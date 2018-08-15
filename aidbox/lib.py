import json
import copy
import requests

from collections import defaultdict

from .utils import encode_params, convert_values
from .exceptions import (
    AidboxResourceFieldDoesNotExist, AidboxResourceNotFound,
    AidboxOperationOutcome)


class Aidbox:
    schema = None
    resources_cache = None
    url = None
    authorization = None
    without_cache = False

    def __init__(self, url, authorization, without_cache=False):
        self.schema = {}
        self.url = url
        self.authorization = authorization
        self.resources_cache = defaultdict(dict)
        self.without_cache = without_cache

    def _add_resource_to_cache(self, resource):
        if self.without_cache:
            return

        self.resources_cache[resource.resource_type][resource.id] = resource

    def _remove_resource_from_cache(self, resource):
        if self.without_cache:
            return

        del self.resources_cache[resource.resource_type][resource.id]

    def _get_resource_from_cache(self, resource_type, id):
        if self.without_cache:
            return None

        return self.resources_cache[resource_type].get(id, None)

    def clear_resources_cache(self, resource_type=None):
        if self.without_cache:
            return

        if resource_type:
            self.resources_cache[resource_type] = {}
        else:
            self.resources_cache = defaultdict(dict)

    def reference(self, resourceType, id, **kwargs):
        if not resourceType or not id:
            raise TypeError(
                'Arguments resourceType and id are required')

        return AidboxReference(
            self, resource_type=resourceType, id=id, **kwargs)

    def resource(self, resourceType=None, **kwargs):
        if not resourceType:
            raise TypeError(
                'Argument resourceType is required')

        self._fetch_schema(resourceType)

        return AidboxResource(
            self,
            resource_type=resourceType,
            **convert_values(
                kwargs,
                lambda x: AidboxReference(
                    self,
                    resource_type=x.get('resourceType'),
                    **x
                ) if AidboxBaseResource.is_reference(x) else x)
        )

    def resources(self, resource_type):
        return AidboxSearchSet(self, resource_type=resource_type)

    def _do_request(self, method, path, data=None, params=None):
        url = '{0}/{1}?{2}'.format(
            self.url, path, encode_params(params))
        r = requests.request(
            method,
            url,
            json=data,
            headers={'Authorization': self.authorization})

        if 200 <= r.status_code < 300:
            return json.loads(r.content) if r.content else None

        if r.status_code == 404:
            raise AidboxResourceNotFound(r.content.decode())

        raise AidboxOperationOutcome(r.content.decode())

    def _fetch_resource(self, path, params=None):
        return self._do_request('get', path, params=params)

    def _fetch_schema(self, resource_type):
        schema = self.schema.get(resource_type, None)
        if not schema:
            bundle = self._fetch_resource(
                'Attribute',
                params={'entity': resource_type}
            )
            attrs = [res['resource'] for res in bundle['entry']]
            schema = {attr['path'][0] for attr in attrs} | \
                     {'id', 'resourceType', 'meta', 'extension'}
            self.schema[resource_type] = schema

        return schema

    def __str__(self):  # pragma: no cover
        return self.url

    def __repr__(self):  # pragma: no cover
        return self.__str__()


class AidboxSearchSet:
    _aidbox = None
    resource_type = None
    params = None

    def __init__(self, _aidbox, resource_type, params=None):
        self._aidbox = _aidbox
        self.resource_type = resource_type
        self.params = defaultdict(list, params or {})

    def get(self, id):
        res = self.search(_id=id).first()
        if res:
            return res

        raise AidboxResourceNotFound()

    def execute(self):
        res_data = self._aidbox._fetch_resource(self.resource_type, self.params)
        resource_data = [res['resource'] for res in res_data['entry']]

        resources = [self._aidbox.resource(**data) for data in resource_data]
        for resource in resources:
            self._aidbox._add_resource_to_cache(resource)

        return [resource for resource in resources
                if resource.resource_type == self.resource_type]

    def count(self):
        new_params = copy.deepcopy(self.params)
        new_params['_count'] = 1
        new_params['_totalMethod'] = 'count'

        return self._aidbox._fetch_resource(
            self.resource_type,
            params=new_params
        )['total']

    def first(self):
        result = self.limit(1).execute()
        return result[0] if result else None

    def clone(self, override=False, **kwargs):
        new_params = copy.deepcopy(self.params)
        for key, value in kwargs.items():
            if override:
                if isinstance(value, list):
                    new_params[key] = value
                else:
                    new_params[key] = [value]
            else:
                if isinstance(value, list):
                    for item in value:
                        new_params[key].append(item)
                else:
                    new_params[key].append(value)
        return AidboxSearchSet(self._aidbox, self.resource_type, new_params)

    def elements(self, *attrs, exclude=False):
        attrs = set(attrs)
        if not exclude:
            attrs |= {'id', 'resourceType'}
        attrs = [attr for attr in attrs]

        return self.clone(
            _elements='{0}{1}'.format('-' if exclude else '',
                                      ','.join(attrs)))

    def include(self, resource_type, attr, recursive=False):
        key = '_include{0}'.format(':recursive' if recursive else '')

        return self.clone(
            **{key: '{0}:{1}'.format(resource_type, attr)})

    def revinclude(self, resource_type, attr, recursive=False):
        # For the moment, this method might only have useless behaviour
        # because you don't have any possibilities to access the related data

        raise NotImplementedError()

    def search(self, **kwargs):
        return self.clone(**kwargs)

    def limit(self, limit):
        return self.clone(_count=limit, override=True)

    def page(self, page):
        return self.clone(_page=page, override=True)

    def sort(self, *keys):
        sort_keys = ','.join(keys)
        return self.clone(_sort=sort_keys)

    def __str__(self):  # pragma: no cover
        return '<AidboxSearchSet {0}?{1}>'.format(
            self.resource_type, encode_params(self.params))

    def __repr__(self):  # pragma: no cover
        return self.__str__()

    def __iter__(self):
        return iter(self.execute())


class AidboxBaseResource:
    _aidbox = None
    _data = None
    resource_type = None

    def __init__(self, _aidbox, resource_type, **kwargs):
        self._aidbox = _aidbox
        self._data = {}
        self.resource_type = resource_type

        self['resourceType'] = resource_type
        for key, value in kwargs.items():
            self[key] = value

    def __contains__(self, item):
        return item in self.get_root_attrs()

    def __setitem__(self, key, value):
        if key in self.get_root_attrs():
            self._data[key] = value
        else:
            raise AidboxResourceFieldDoesNotExist(
                'Invalid attribute `{0}` for resource `{1}`'.format(
                    key, self.resource_type))

    def __getitem__(self, key):
        if key in self.get_root_attrs():
            return self._data.get(key, None)
        else:
            raise AidboxResourceFieldDoesNotExist(
                'Invalid attribute `{0}` for resource `{1}`'.format(
                    key, self.resource_type))

    def __eq__(self, other):
        return isinstance(other, (AidboxResource, AidboxReference)) \
               and self.id == other.id \
               and self.resource_type == other.resource_type

    def to_dict(self):
        def convert_fn(item):
            if isinstance(item, AidboxResource):
                return item.to_reference().to_dict()
            elif isinstance(item, AidboxReference):
                return item.to_dict()
            else:
                return item

        return convert_values(self._data, convert_fn)

    def get_root_attrs(self):
        return ['resourceType', 'id']

    @property
    def id(self):
        return self['id']

    @staticmethod
    def is_reference(value):
        if not isinstance(value, dict):
            return False
        return 'id' in value and 'resourceType' in value and \
               not (set(value.keys()) - {'id', 'resourceType', 'display'})

    def _ipython_key_completions_(self):
        return self.get_root_attrs()


class AidboxResource(AidboxBaseResource):
    def get_root_attrs(self):
        return self._aidbox.schema[self.resource_type]

    def get_path(self):
        if self.id:
            return '{0}/{1}'.format(self.resource_type, self.id)

        return self.resource_type

    def save(self):
        data = self._aidbox._do_request(
            'put' if self.id else 'post', self.get_path(), data=self.to_dict())

        self['meta'] = data.get('meta', {})
        self['id'] = data.get('id')

        self._aidbox._add_resource_to_cache(self)

    def delete(self):
        self._aidbox._remove_resource_from_cache(self)

        return self._aidbox._do_request('delete', self.get_path())

    def to_reference(self, **kwargs):
        return AidboxReference(
            self._aidbox, resource_type=self.resource_type, id=self.id,
            **kwargs)

    def __str__(self):  # pragma: no cover
        return '<AidboxResource {0}>'.format(self.get_path())

    def __repr__(self):  # pragma: no cover
        return self.__str__()


class AidboxReference(AidboxBaseResource):
    def get_root_attrs(self):
        return ['resourceType', 'id', 'display']

    def __str__(self):  # pragma: no cover
        return '<AidboxReference {0}/{1}>'.format(
            self.resource_type, self.id)

    def __repr__(self):  # pragma: no cover
        return self.__str__()

    def to_resource(self, nocache=False):
        cached_resource = self._aidbox._get_resource_from_cache(
            self.resource_type, self.id)

        if cached_resource and not nocache:
            return cached_resource

        return self._aidbox.resources(self.resource_type).get(self.id)

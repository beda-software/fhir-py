import json
import copy
import requests

from collections import defaultdict
from urllib.parse import parse_qsl

from .utils import encode_params, select_keys, convert_values
from .exceptions import (
    AidboxResourceFieldDoesNotExist, AidboxResourceNotFound,
    AidboxAuthorizationError, AidboxOperationOutcome)


class ReferableMixin:
    def __eq__(self, other):
        return isinstance(other, (AidboxResource, AidboxReference)) \
               and self.id == other.id \
               and self.resourceType == other.resourceType


class Aidbox:
    schema = None
    resources_cache = None
    url = None
    authorization = None
    without_cache = False

    @staticmethod
    def obtain_token(url, email, password):
        r = requests.post(
            '{0}/oauth2/authorize'.format(url),
            params={
                'client_id': 'sansara',
                'scope': 'openid profile email',
                'response_type': 'id_token',
            },
            data={'email': email, 'password': password},
            allow_redirects=False
        )
        if 'location' not in r.headers:
            raise AidboxAuthorizationError()

        # We don't fill production database with test tokens
        token_data = dict(parse_qsl(r.headers['location']))  # pragma: no cover
        return token_data['id_token']  # pragma: no cover

    def __init__(self, url, authorization, without_cache=False):
        self.schema = {}
        self.url = url
        self.authorization = authorization
        self.resources_cache = defaultdict(dict)
        self.without_cache = without_cache

    def add_resource_to_cache(self, resource):
        if self.without_cache:
            return

        self.resources_cache[resource.resourceType][resource.id] = resource

    def remove_resource_from_cache(self, resource):
        if self.without_cache:
            return

        del self.resources_cache[resource.resourceType][resource.id]

    def get_resource_from_cache(self, resourceType, id):
        if self.without_cache:
            return None

        return self.resources_cache[resourceType].get(id, None)

    def clear_resources_cache(self, resourceType=None):
        if self.without_cache:
            return

        if resourceType:
            self.resources_cache[resourceType] = {}
        else:
            self.resources_cache = defaultdict(dict)

    def reference(self, resourceType=None, id=None, **kwargs):
        if resourceType is None or id is None:
            raise AttributeError('`resourceType` and `id` are required')
        return AidboxReference(self, resourceType, id, **kwargs)

    def resource(self, resourceType, **kwargs):
        kwargs['resourceType'] = resourceType
        return AidboxResource(self, **kwargs)

    def resources(self, resourceType):
        return AidboxSearchSet(self, resourceType=resourceType)

    def _do_request(self, method, path, data=None, params=None):
        url = '{0}/{1}?{2}'.format(
            self.url, path, encode_params(params))
        r = requests.request(
            method,
            url,
            json=data,
            headers={'Authorization': self.authorization})

        if 200 <= r.status_code < 300:
            result = json.loads(r.content) if r.content else None
            return convert_values(
                result,
                lambda x: self.reference(**x)
                if AidboxReference.is_reference(x) else x)

        if r.status_code == 404:
            raise AidboxResourceNotFound(r.content)

        raise AidboxOperationOutcome(r.content)

    def _fetch_resource(self, path, params=None):
        return self._do_request('get', path, params=params)

    def _fetch_schema(self, resourceType):
        schema = self.schema.get(resourceType, None)
        if not schema:
            bundle = self._fetch_resource(
                'Attribute',
                params={'entity': resourceType}
            )
            attrs = [res['resource'] for res in bundle['entry']]
            schema = {attr['path'][0] for attr in attrs} | \
                     {'id', 'resourceType', 'meta', 'extension'}
            self.schema[resourceType] = schema

        return schema

    def __str__(self):  # pragma: no cover
        return self.url

    def __repr__(self):  # pragma: no cover
        return self.__str__()


class AidboxSearchSet:
    _aidbox = None
    resourceType = None
    params = None

    def __init__(self, aidbox, resourceType, params=None):
        self._aidbox = aidbox
        self.resourceType = resourceType
        self.params = defaultdict(list, params or {})

    def get(self, id):
        res = self.search(_id=id).first()
        if res:
            return res

        raise AidboxResourceNotFound()

    def execute(self):
        attrs = self._aidbox._fetch_schema(self.resourceType)

        res_data = self._aidbox._fetch_resource(self.resourceType, self.params)
        resource_data = [res['resource'] for res in res_data['entry']]
        resources = [
            AidboxResource(
                self._aidbox,
                **select_keys(data, attrs)
            )
            for data in resource_data
        ]
        for resource in resources:
            self._aidbox.add_resource_to_cache(resource)

        return [resource for resource in resources
                if resource.resourceType == self.resourceType]

    def count(self):
        new_params = copy.deepcopy(self.params)
        new_params['_count'] = 1
        new_params['_totalMethod'] = 'count'

        return self._aidbox._fetch_resource(
            self.resourceType,
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
        return AidboxSearchSet(self._aidbox, self.resourceType, new_params)

    def elements(self, *attrs, exclude=False):
        attrs = set(attrs)
        if not exclude:
            attrs |= {'id', 'resourceType'}
        attrs = [attr for attr in attrs]

        return self.clone(
            _elements='{0}{1}'.format('-' if exclude else '',
                                      ','.join(attrs)))

    def include(self, resourceType, attr, recursive=False):
        key = '_include{0}'.format(':recursive' if recursive else '')

        return self.clone(
            **{key: '{0}:{1}'.format(resourceType, attr)})

    def revinclude(self, resourceType, attr, recursive=False):
        # TODO: For the moment, this method can have useless behaviour
        # TODO: Think about architecture

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
            self.resourceType, encode_params(self.params))

    def __repr__(self):  # pragma: no cover
        return self.__str__()

    def __iter__(self):
        return iter(self.execute())


class AidboxResource(ReferableMixin):
    _aidbox = None
    _data = None

    resourceType = None

    def get_root_attrs(self):
        return self._aidbox.schema[self.resourceType]

    def __init__(self, aidbox, **kwargs):
        resourceType = kwargs.get('resourceType')
        aidbox._fetch_schema(resourceType)

        self.resourceType = resourceType
        self._aidbox = aidbox
        self._data = {}

        for key, value in kwargs.items():
            setattr(self, key, value)

    def __dir__(self):
        return list(self.get_root_attrs()) + \
               super(AidboxResource, self).__dir__()

    def __setattr__(self, key, value):
        if key in ['_aidbox', '_data', 'resourceType']:
            super(AidboxResource, self).__setattr__(key, value)
        elif key in self.get_root_attrs():
            self._data[key] = value
        else:
            raise AidboxResourceFieldDoesNotExist(
                'Invalid attribute `{0}` for resource `{1}`'.format(
                    key, self.resourceType))

    def __getattr__(self, key):
        if key in self.get_root_attrs():
            return self._data.get(key, None)
        else:
            raise AidboxResourceFieldDoesNotExist(
                'Invalid attribute `{0}` for resource `{1}`'.format(
                    key, self.resourceType))

    def get_path(self):
        if self.id:
            return '{0}/{1}'.format(self.resourceType, self.id)

        return self.resourceType

    def save(self):
        data = self._aidbox._do_request(
            'put' if self.id else 'post', self.get_path(), data=self.to_dict())

        self.meta = data.get('meta', {})
        self.id = data.get('id')

        self._aidbox.add_resource_to_cache(self)

    def delete(self):
        self._aidbox.remove_resource_from_cache(self)

        return self._aidbox._do_request('delete', self.get_path())

    def to_reference(self, **kwargs):
        return AidboxReference(
            self._aidbox, self.resourceType, self.id, **kwargs)

    def to_dict(self):
        def convert_fn(item):
            if isinstance(item, AidboxResource):
                return item.to_reference().to_dict()
            elif isinstance(item, AidboxReference):
                return item.to_dict()
            else:
                return item

        data = {'resourceType': self.resourceType}
        data.update(self._data)

        return convert_values(data, convert_fn)

    def __str__(self):  # pragma: no cover
        return '<AidboxResource {0}>'.format(self.get_path())

    def __repr__(self):  # pragma: no cover
        return self.__str__()


class AidboxReference(ReferableMixin):
    _aidbox = None
    resourceType = None
    id = None
    display = None

    def __init__(self, aidbox, resourceType, id, **kwargs):
        self._aidbox = aidbox
        self.resourceType = resourceType
        self.id = id
        self.display = kwargs.get('display', None)

    def __str__(self):  # pragma: no cover
        return '<AidboxReference {0}/{1}>'.format(self.resourceType, self.id)

    def __repr__(self):  # pragma: no cover
        return self.__str__()

    def to_resource(self, nocache=False):
        cached_resource = self._aidbox.get_resource_from_cache(
            self.resourceType, self.id)

        if cached_resource and not nocache:
            return cached_resource

        return self._aidbox.resources(self.resourceType).get(self.id)

    def to_dict(self):
        return {attr: getattr(self, attr) for attr in [
            'id', 'resourceType', 'display'
        ] if getattr(self, attr, None)}

    @staticmethod
    def is_reference(value):
        if not isinstance(value, dict):
            return False
        return 'id' in value and 'resourceType' in value and \
               not (set(value.keys()) - {'id', 'resourceType', 'display'})

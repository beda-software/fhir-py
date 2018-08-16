import json
import copy
import pickle
from collections import defaultdict

import requests


from .utils import encode_params, convert_values
from .exceptions import (
    FHIRResourceNotFound, FHIROperationOutcome, FHIRNotSupportedVersionError)


def load_schema(version):
    try:
        with open('schemas/fhir-{0}.pkl'.format(version), 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        raise FHIRNotSupportedVersionError()


class FHIRClient:
    schema = None
    resources_cache = None
    url = None
    authorization = None
    without_cache = False

    def __init__(self, url, authorization=None, without_cache=False,
                 fhir_version='3.0.1'):
        self.url = url
        self.authorization = authorization
        self.resources_cache = defaultdict(dict)
        self.without_cache = without_cache
        self.schema = load_schema(fhir_version)

    def __str__(self):  # pragma: no cover
        return '<FHIRClient {0}>'.format(self.url)

    def __repr__(self):  # pragma: no cover
        return self.__str__()

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

    def reference(self, resource_type=None, id=None, reference=None, **kwargs):
        if resource_type and id:
            reference = '{0}/{1}'.format(resource_type, id)

        if not reference:
            raise TypeError(
                'Arguments `resource_type` and `id` or `reference` '
                'are required')

        return FHIRReference(self, reference=reference, **kwargs)

    def resource(self, resource_type=None, **kwargs):
        if resource_type is None:
            raise TypeError('Argument `resource_type` is required')

        return FHIRResource(
            self,
            resource_type=resource_type,
            **convert_values(
                kwargs,
                lambda x: self.reference(
                    **x
                ) if FHIRBaseResource.is_reference(x) else x)
        )

    def resources(self, resource_type):
        return FHIRSearchSet(self, resource_type=resource_type)

    def _do_request(self, method, path, data=None, params=None):
        params = params or {}
        params.update({'_format': 'json'})
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
            raise FHIRResourceNotFound(r.content.decode())

        raise FHIROperationOutcome(r.content.decode())

    def _fetch_resource(self, path, params=None):
        return self._do_request('get', path, params=params)

    def _get_schema(self, resource_type):
        return self.schema.get(resource_type, None)


class FHIRSearchSet:
    _client = None
    resource_type = None
    params = None

    def __init__(self, _client, resource_type, params=None):
        self._client = _client
        self.resource_type = resource_type
        self.params = defaultdict(list, params or {})

    def execute(self, skip_cache=False):
        res_data = self._client._fetch_resource(self.resource_type, self.params)
        resources_data = [res['resource'] for res in res_data['entry']]

        resources = []
        for data in resources_data:
            resource_type = data.get('resourceType', None)
            resource = self._client.resource(resource_type, **data)

            if not skip_cache:
                self._client._add_resource_to_cache(resource)

            if resource.resource_type == self.resource_type:
                resources.append(resource)

        return resources

    def count(self):
        new_params = copy.deepcopy(self.params)
        new_params['_count'] = 1
        new_params['_totalMethod'] = 'count'

        return self._client._fetch_resource(
            self.resource_type,
            params=new_params
        )['total']

    def first(self):
        result = self.limit(1).execute()
        return result[0] if result else None

    def get(self, id):
        res = self.search(_id=id).first()
        if res:
            return res

        raise FHIRResourceNotFound()

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
        return FHIRSearchSet(self._client, self.resource_type, new_params)

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
        return '<FHIRSearchSet {0}?{1}>'.format(
            self.resource_type, encode_params(self.params))

    def __repr__(self):  # pragma: no cover
        return self.__str__()

    def __iter__(self):
        return iter(self.execute())


class FHIRBaseResource:
    _client = None
    _data = None

    def __init__(self, _client, **kwargs):
        self._client = _client
        self._data = {}

        for key, value in kwargs.items():
            self[key] = value

    def __contains__(self, item):
        return self._data.get(item, None) is not None

    def __setitem__(self, key, value):
        if key in self.get_root_attrs():
            self._data[key] = value
        else:
            raise KeyError('Invalid key `{0}`'.format(key))

    def __getitem__(self, key):
        if key in self.get_root_attrs():
            return self._data.get(key, None)
        else:
            raise KeyError('Invalid key `{0}`'.format(key))

    def __eq__(self, other):
        return isinstance(other, FHIRBaseResource) \
               and self.reference == other.reference

    def to_dict(self):
        def convert_fn(item):
            if isinstance(item, FHIRResource):
                return item.to_reference().to_dict()
            elif isinstance(item, FHIRReference):
                return item.to_dict()
            else:
                return item

        return convert_values(self._data, convert_fn)

    def get_root_attrs(self):
        raise NotImplementedError

    @property
    def id(self):
        raise NotImplementedError()

    @property
    def resource_type(self):
        raise NotImplementedError()

    @property
    def reference(self):
        raise NotImplementedError()

    @staticmethod
    def is_reference(value):
        if not isinstance(value, dict):
            return False

        return 'reference' in value and \
               not (set(value.keys()) - {'reference', 'display'})

    def _ipython_key_completions_(self):
        return self.get_root_attrs()


class FHIRResource(FHIRBaseResource):
    resource_type = None

    def __init__(self, _client, resource_type, **kwargs):
        self.resource_type = resource_type
        kwargs['resourceType'] = resource_type

        super(FHIRResource, self).__init__(_client, **kwargs)

    def __setitem__(self, key, value):
        if key == 'resourceType' and self['resourceType'] is not None:
            raise KeyError(
                'Can not change `resourceType` after instantiating resource. '
                'You must re-instantiate resource using '
                '`FHIRClient.resource` method')

        super(FHIRResource, self).__setitem__(key, value)

    def __str__(self):  # pragma: no cover
        return '<FHIRResource {0}>'.format(self.get_path())

    def __repr__(self):  # pragma: no cover
        return self.__str__()

    def get_root_attrs(self):
        return set(self._client._get_schema(self.resource_type)) | \
               {'resourceType', 'id', 'meta', 'extension'}

    def get_path(self):
        if self.id:
            return '{0}/{1}'.format(self.resource_type, self.id)

        return self.resource_type

    def save(self):
        data = self._client._do_request(
            'put' if self.id else 'post', self.get_path(), data=self.to_dict())

        self['meta'] = data.get('meta', {})
        self['id'] = data.get('id')

        self._client._add_resource_to_cache(self)

    def delete(self):
        self._client._remove_resource_from_cache(self)

        return self._client._do_request('delete', self.get_path())

    def to_resource(self, nocache=False):
        """
        Returns FHIRResource instance for this resource
        """
        return self

    def to_reference(self, **kwargs):
        """
        Returns FHIRReference instance for this resource
        """
        return self._client.reference(reference=self.reference, **kwargs)

    @property
    def id(self):
        return self['id']

    @property
    def reference(self):
        """
        Returns reference if local resource is saved
        """
        if self.id:
            return '{0}/{1}'.format(self.resource_type, self.id)


class FHIRReference(FHIRBaseResource):
    def __str__(self):  # pragma: no cover
        return '<FHIRReference {0}>'.format(self.reference)

    def __repr__(self):  # pragma: no cover
        return self.__str__()

    def get_root_attrs(self):
        return ['reference', 'display']

    def to_resource(self, nocache=False):
        """
        Returns FHIRResource instance for this reference from cache
        if nocache is not specified and from fhir server otherwise.
        """
        if not self.is_local:
            raise FHIRResourceNotFound(
                'Can not resolve not local resource')

        cached_resource = self._client._get_resource_from_cache(
            self.resource_type, self.id)

        if cached_resource and not nocache:
            return cached_resource

        return self._client.resources(self.resource_type).get(self.id)

    def to_reference(self, **kwargs):
        """
        Returns FHIRReference instance for this reference
        """
        return self._client.reference(reference=self.reference, **kwargs)

    @property
    def reference(self):
        return self['reference']

    @property
    def id(self):
        """
        Returns id if reference specifies to the local resource
        """
        if self.is_local:
            return self.reference.split('/', 1)[1]

    @property
    def resource_type(self):
        """
        Returns resource type if reference specifies to the local resource
        """
        if self.is_local:
            return self.reference.split('/', 1)[0]

    @property
    def is_local(self):
        return '/' in self.reference

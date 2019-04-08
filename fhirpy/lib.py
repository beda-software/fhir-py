import json
import copy
import pickle
from os.path import dirname
from collections import defaultdict

import requests


from .utils import (
    encode_params, convert_values, get_by_path, parse_path, chunks)
from .exceptions import (
    FHIRResourceNotFound, FHIROperationOutcome, FHIRNotSupportedVersionError,
    FHIRInvalidResponse)


def load_schema(version):
    filename = '{0}/schemas/fhir-{1}.pkl'.format(dirname(__file__), version)

    try:
        with open(filename, 'rb') as f:
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
            **kwargs
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
            return json.loads(r.content.decode()) if r.content else None

        if r.status_code == 404:
            raise FHIRResourceNotFound(r.content.decode())

        raise FHIROperationOutcome(r.content.decode())

    def _fetch_resource(self, path, params=None):
        return self._do_request('get', path, params=params)

    def _get_schema(self, resource_type):
        return self.schema.get(resource_type, None)


class FHIRSearchSet:
    client = None
    resource_type = None
    params = None

    def __init__(self, client, resource_type, params=None):
        self.client = client
        self.resource_type = resource_type
        self.params = defaultdict(list, params or {})

    def _perform_resource(self, data, skip_caching):
        resource_type = data.get('resourceType', None)
        resource = self.client.resource(resource_type, **data)

        if not skip_caching:
            self.client._add_resource_to_cache(resource)

        return resource

    def fetch(self, *, skip_caching=False):
        bundle_data = self.client._fetch_resource(
            self.resource_type, self.params)
        bundle_resource_type = bundle_data.get('resourceType', None)

        if bundle_resource_type != 'Bundle':
            raise FHIRInvalidResponse(
                'Expected to receive Bundle '
                'but {0} received'.format(bundle_resource_type))

        resources_data = [
            res['resource'] for res in bundle_data.get('entry', [])]

        resources = []
        for data in resources_data:
            resource = self._perform_resource(data, skip_caching)
            if resource.resource_type == self.resource_type:
                resources.append(resource)

        return resources

    def fetch_all(self, *, skip_caching=False):
        page = 1
        resources = []

        while True:
            new_resources = self.page(page).fetch(skip_caching=skip_caching)
            if not new_resources:
                break

            resources.extend(new_resources)
            page += 1

        return resources

    def get(self, id, *, skip_caching=False):
        res_data = self.client._fetch_resource(
            '{0}/{1}'.format(self.resource_type, id))

        if res_data['resourceType'] != self.resource_type:
            raise FHIRInvalidResponse(
                'Expected to receive {0} '
                'but {1} received'.format(self.resource_type,
                                          res_data['resourceType']))

        return self._perform_resource(res_data, skip_caching)

    def count(self):
        new_params = copy.deepcopy(self.params)
        new_params['_count'] = 1
        new_params['_totalMethod'] = 'count'

        return self.client._fetch_resource(
            self.resource_type,
            params=new_params
        )['total']

    def first(self):
        result = self.limit(1).fetch()

        return result[0] if result else None

    def clone(self, override=False, **kwargs):
        new_params = copy.deepcopy(self.params)
        for key, value in kwargs.items():
            if not isinstance(value, list):
                value = [value]

            if override:
                new_params[key] = value
            else:
                new_params[key].extend(value)

        return FHIRSearchSet(self.client, self.resource_type, new_params)

    def elements(self, *attrs, exclude=False):
        attrs = set(attrs)
        if not exclude:
            attrs |= {'id', 'resourceType'}
        attrs = [attr for attr in attrs]

        return self.clone(
            _elements='{0}{1}'.format('-' if exclude else '',
                                      ','.join(attrs)),
            override=True
        )

    def include(self, resource_type, attr, target_resource_type=None,
                *, recursive=False):
        key_params = ['_include']
        if recursive:
            key_params.append('recursive')
        key = ':'.join(key_params)

        value_params = [resource_type, attr]
        if target_resource_type:
            value_params.append(target_resource_type)
        value = ':'.join(value_params)

        return self.clone(**{key: value})

    def has(self, *args, **kwargs):
        if len(args) % 2 != 0:
            raise TypeError(
                'You should pass even size of arguments, for example: '
                '`.has(\'Observation\', \'patient\', '
                '\'AuditEvent\', \'entity\', user=\'id\')`')

        key_part = ':'.join(
            ['_has:{0}'.format(':'.join(pair))
             for pair in chunks(args, 2)])

        return self.clone(
            **{':'.join([key_part, key]): value
               for key, value in kwargs.items()})

    def revinclude(self, resource_type, attr, recursive=False):
        # For the moment, this method might only have useless behaviour
        # because you don't have any possibilities to access the related data

        raise NotImplementedError()

    def search(self, **kwargs):
        return self.clone(**kwargs)

    def limit(self, limit):
        return self.clone(_count=limit, override=True)

    def page(self, page):
        return self.clone(page=page, override=True)

    def sort(self, *keys):
        sort_keys = ','.join(keys)
        return self.clone(_sort=sort_keys, override=True)

    def __str__(self):  # pragma: no cover
        return '<FHIRSearchSet {0}?{1}>'.format(
            self.resource_type, encode_params(self.params))

    def __repr__(self):  # pragma: no cover
        return self.__str__()

    def __iter__(self):
        return iter(self.fetch())


class FHIRBaseResource(dict):
    client = None

    def __init__(self, client, **kwargs):
        self.client = client

        self._raise_error_if_invalid_keys(kwargs.keys())
        super(FHIRBaseResource, self).__init__(**kwargs)

    def __eq__(self, other):
        return isinstance(other, FHIRBaseResource) \
               and self.reference == other.reference

    def __setitem__(self, key, value):
        self._raise_error_if_invalid_key(key)

        super(FHIRBaseResource, self).__setitem__(key, value)

    def __getitem__(self, key):
        self._raise_error_if_invalid_key(key)

        return super(FHIRBaseResource, self).__getitem__(key)

    def get_by_path(self, path, default=None):
        keys = parse_path(path)

        self._raise_error_if_invalid_key(keys[0])

        return get_by_path(self, keys, default)

    def get(self, key, default=None):
        self._raise_error_if_invalid_key(key)

        return super(FHIRBaseResource, self).get(key, default)

    def setdefault(self, key, default=None):
        self._raise_error_if_invalid_key(key)

        return super(FHIRBaseResource, self).setdefault(key, default)

    def serialize(self):
        def convert_fn(item):
            if isinstance(item, FHIRResource):
                return item.to_reference().serialize(), True
            elif isinstance(item, FHIRReference):
                return item.serialize(), True
            else:
                return item, False

        return convert_values(
            {key: value for key, value in self.items()}, convert_fn)

    def get_root_keys(self):  # pragma: no cover
        raise NotImplementedError

    @property
    def id(self):  # pragma: no cover
        raise NotImplementedError()

    @property
    def resource_type(self):  # pragma: no cover
        raise NotImplementedError()

    @property
    def reference(self):  # pragma: no cover
        raise NotImplementedError()

    @staticmethod
    def is_reference(value):
        if not isinstance(value, dict):
            return False

        return 'reference' in value and \
               not (set(value.keys()) - {'reference', 'display'})

    def _ipython_key_completions_(self):  # pragma: no cover
        return self.get_root_keys()

    def _raise_error_if_invalid_keys(self, keys):
        root_attrs = self.get_root_keys()

        for key in keys:
            if key not in root_attrs:
                raise KeyError(
                    'Invalid key `{0}`. Possible keys are `{1}`'.format(
                        key, ', '.join(root_attrs)))

    def _raise_error_if_invalid_key(self, key):
        self._raise_error_if_invalid_keys([key])


class FHIRResource(FHIRBaseResource):
    resource_type = None

    def __init__(self, client, resource_type, **kwargs):
        def convert_fn(item):
            if isinstance(item, FHIRBaseResource):
                return item, True

            if FHIRBaseResource.is_reference(item):
                return FHIRReference(client, **item), True

            return item, False

        self.resource_type = resource_type
        kwargs['resourceType'] = resource_type
        converted_kwargs = convert_values(kwargs, convert_fn)

        super(FHIRResource, self).__init__(client, **converted_kwargs)

    def __setitem__(self, key, value):
        if key == 'resourceType' and 'resourceType' not in self:
            raise KeyError(
                'Can not change `resourceType` after instantiating resource. '
                'You must re-instantiate resource using '
                '`FHIRClient.resource` method')

        super(FHIRResource, self).__setitem__(key, value)

    def __str__(self):  # pragma: no cover
        return '<FHIRResource {0}>'.format(self._get_path())

    def __repr__(self):  # pragma: no cover
        return self.__str__()

    def get_root_keys(self):
        return set(self.client._get_schema(self.resource_type)) | \
               {'resourceType', 'id', 'meta', 'extension'}

    def save(self):
        data = self.client._do_request(
            'put' if self.id else 'post', 
            self._get_path(), 
            data=self.serialize())

        self['meta'] = data.get('meta', {})
        self['id'] = data.get('id')

        self.client._add_resource_to_cache(self)

    def delete(self):
        self.client._remove_resource_from_cache(self)

        return self.client._do_request('delete', self._get_path())

    def to_resource(self, nocache=False):
        """
        Returns FHIRResource instance for this resource
        """
        return self

    def to_reference(self, **kwargs):
        """
        Returns FHIRReference instance for this resource
        """
        if not self.reference:
            raise FHIRResourceNotFound(
                'Can not get reference to unsaved resource without id')

        return FHIRReference(self.client, reference=self.reference, **kwargs)

    @property
    def id(self):
        return self.get('id', None)

    @property
    def reference(self):
        """
        Returns reference if local resource is saved
        """
        if self.id:
            return '{0}/{1}'.format(self.resource_type, self.id)

    def _get_path(self):
        if self.id:
            return '{0}/{1}'.format(self.resource_type, self.id)

        return self.resource_type


class FHIRReference(FHIRBaseResource):
    def __str__(self):  # pragma: no cover
        return '<FHIRReference {0}>'.format(self.reference)

    def __repr__(self):  # pragma: no cover
        return self.__str__()

    def get_root_keys(self):
        return ['reference', 'display']

    def to_resource(self, nocache=False):
        """
        Returns FHIRResource instance for this reference from cache
        if nocache is not specified and from fhir server otherwise.
        """
        if not self.is_local:
            raise FHIRResourceNotFound(
                'Can not resolve not local resource')

        cached_resource = self.client._get_resource_from_cache(
            self.resource_type, self.id)

        if cached_resource and not nocache:
            return cached_resource

        return self.client.resources(self.resource_type).get(self.id)

    def to_reference(self, **kwargs):
        """
        Returns FHIRReference instance for this reference
        """
        return FHIRReference(self.client, reference=self.reference, **kwargs)

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
        if self.reference.count('/') != 1:
            return False

        resource_type, _ = self.reference.split('/')
        if self.client._get_schema(resource_type):
            return True

        return False

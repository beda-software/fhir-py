import json
import copy
import aiohttp
import requests
import datetime
import pytz
from abc import ABC, abstractmethod
from collections import defaultdict
from .utils import (
    AttrDict, encode_params, convert_values, get_by_path, parse_path, chunks
)
from .exceptions import (ResourceNotFound, OperationOutcome, InvalidResponse)


class AbstractClient(ABC):
    schema = None
    resources_cache = None
    url = None
    authorization = None
    without_cache = False
    extra_headers = None

    def __init__(
        self,
        url,
        authorization=None,
        with_cache=False,
        schema=None,
        extra_headers=None
    ):
        self.url = url
        self.authorization = authorization
        self.resources_cache = defaultdict(dict)
        self.without_cache = not with_cache
        self.extra_headers = extra_headers
        if schema:
            self.schema = schema

    def __str__(self):  # pragma: no cover
        return '<{0} {1}>'.format(self.__class__.__name__, self.url)

    def __repr__(self):  # pragma: no cover
        return self.__str__()

    @property
    @abstractmethod
    def searchset_class(self):
        pass

    @property
    @abstractmethod
    def resource_class(self):
        pass

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

    @abstractmethod
    def reference(self, resource_type=None, id=None, reference=None, **kwargs):
        pass

    def resource(self, resource_type=None, **kwargs):
        if resource_type is None:
            raise TypeError('Argument `resource_type` is required')

        return self.resource_class(self, resource_type=resource_type, **kwargs)

    def resources(self, resource_type):
        return self.searchset_class(self, resource_type=resource_type)

    @abstractmethod
    def _do_request(self, method, path, data=None, params=None):
        pass

    @abstractmethod
    def _fetch_resource(self, path, params=None):
        pass

    def _get_schema(self):
        return self.schema


class AsyncAbstractClient(AbstractClient):
    async def _do_request(self, method, path, data=None, params=None):
        params = params or {}
        params.update({'_format': 'json'})
        url = '{0}/{1}?{2}'.format(self.url, path, encode_params(params))

        headers = {'Authorization': self.authorization}

        if self.extra_headers is not None:
            headers = {**headers, **self.extra_headers}

        async with aiohttp.request(
            method, url, json=data, headers=headers
        ) as r:
            if 200 <= r.status < 300:
                data = await r.text()
                return json.loads(data, object_hook=AttrDict)

            if r.status == 404 or r.status == 410:
                raise ResourceNotFound(await r.text())

            raise OperationOutcome(await r.text())

    async def _fetch_resource(self, path, params=None):
        return await self._do_request('get', path, params=params)


class SyncAbstractClient(AbstractClient):
    def _do_request(self, method, path, data=None, params=None):
        params = params or {}
        params.update({'_format': 'json'})
        url = '{0}/{1}?{2}'.format(self.url, path, encode_params(params))

        headers = {'Authorization': self.authorization}

        if self.extra_headers is not None:
            headers = {**headers, **self.extra_headers}

        r = requests.request(method, url, json=data, headers=headers)

        if 200 <= r.status_code < 300:
            return json.loads(
                r.content.decode(),
                object_hook=AttrDict) if r.content else None

        if r.status_code == 404 or r.status_code == 410:
            raise ResourceNotFound(r.content.decode())

        raise OperationOutcome(r.content.decode())

    def _fetch_resource(self, path, params=None):
        return self._do_request('get', path, params=params)


FHIR_DATE_TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
FHIR_DATE_FORMAT = '%Y-%m-%d'


def format_date_time(date: datetime.datetime):
    return pytz.utc.normalize(date).strftime(FHIR_DATE_TIME_FORMAT)


def format_date(date: datetime.date):
    return date.strftime(FHIR_DATE_FORMAT)


def transform_param(param: str):
    """
    >>> transform_param('general_practitioner')
    'general-practitioner'
    """
    if param[0] == '_':
        # Don't correct _id, _has, _include, etc.
        return param

    return param.replace('_', '-')


def transform_value(value):
    """
    >>> transform_value(datetime.datetime(2019, 1, 1))
    '2019-01-01T00:00:00Z'

    >>> transform_value(datetime.date(2019, 1, 1))
    '2019-01-01'

    >>> transform_value(True)
    'true'
    """
    if isinstance(value, datetime.datetime):
        return format_date_time(value)
    if isinstance(value, datetime.date):
        return format_date(value)
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (BaseReference, BaseResource)):
        return value.reference
    return value


class Raw:
    kwargs = {}

    def __init__(self, **kwargs):
        self.kwargs = kwargs


def SQ(*args, **kwargs):
    """
    Builds search query

    >>> dict(SQ(general_practitioner='prid'))
    {'general-practitioner': ['prid']}

    >>> dict(SQ(period__ge='2018', period__lt='2019'))
    {'period': ['ge2018', 'lt2019']}

    >>> dict(SQ(text__contains='test'))
    {'text:contains': ['test']}

    >>> dict(SQ(status__not_in='success'))
    {'status:not-in': ['success']}

    >>> dict(SQ(name='family1,family2'))
    {'name': ['family1,family2']}

    >>> dict(SQ(status__not=['failed', 'completed']))
    {'status:not': ['failed', 'completed']}

    >>> dict(SQ(active=True))
    {'active': ['true']}

    >>> dict(SQ(Raw(**{'_has:Person:link:id': 'id'})))
    {'_has:Person:link:id': ['id']}

    """
    res = defaultdict(list)
    for key, value in kwargs.items():
        value = value if isinstance(value, list) else [value]
        value = [transform_value(sub_value) for sub_value in value]

        if '__' in key:
            param, op = key.split('__')
            if op in ['contains', 'exact', 'missing', 'not',
                      'below', 'above', 'in', 'not_in', 'text', 'of_type']:
                param = '{0}:{1}'.format(param, transform_param(op))
            elif op in ['eq', 'ne', 'gt', 'ge', 'lt', 'le', 'sa', 'eb', 'ap']:
                value = ['{0}{1}'.format(op, sub_value) for sub_value in value]
            res[transform_param(param)].extend(value)
        else:
            res[transform_param(key)].extend(value)

    for arg in args:
        if isinstance(arg, Raw):
            for key, value in arg.kwargs.items():
                value = value if isinstance(value, list) else [value]
                res[key].extend(value)
        else:
            raise ValueError('Can\'t handle args without Raw() wrapper')

    return res


class AbstractSearchSet(ABC):
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

    @abstractmethod
    def fetch(self, *, skip_caching=False):
        pass

    @abstractmethod
    def fetch_raw(self, *, skip_caching=False):
        pass

    @abstractmethod
    def fetch_all(self, *, skip_caching=False):
        pass

    @abstractmethod
    def get(self, id, *, skip_caching=False):
        pass

    @abstractmethod
    def count(self):
        pass

    @abstractmethod
    def first(self):
        pass

    def clone(self, override=False, **kwargs):
        new_params = copy.deepcopy(self.params)
        for key, value in kwargs.items():
            if not isinstance(value, list):
                value = [value]

            if override:
                new_params[key] = value
            else:
                new_params[key].extend(value)

        return self.__class__(self.client, self.resource_type, new_params)

    def elements(self, *attrs, exclude=False):
        attrs = set(attrs)
        if not exclude:
            attrs |= {'id', 'resourceType'}
        attrs = [attr for attr in attrs]

        return self.clone(
            _elements='{0}{1}'.format('-' if exclude else '', ','.join(attrs)),
            override=True
        )

    def include(
        self,
        resource_type,
        attr,
        target_resource_type=None,
        *,
        recursive=False
    ):
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
                '\'AuditEvent\', \'entity\', user=\'id\')`'
            )

        key_part = ':'.join(
            ['_has:{0}'.format(':'.join(pair)) for pair in chunks(args, 2)]
        )

        return self.clone(
            **
            {':'.join([key_part, key]): value
             for key, value in SQ(**kwargs).items()}
        )

    def revinclude(self, resource_type, attr, recursive=False):
        key_params = ['_revinclude']

        if recursive:
            key_params.append('recursive')
        key = ':'.join(key_params)

        value_params = [resource_type, attr]
        value = ':'.join(value_params)

        return self.clone(**{key: value})

    def search(self, *args, **kwargs):
        return self.clone(**SQ(*args, **kwargs))

    def limit(self, limit):
        return self.clone(_count=limit, override=True)

    def page(self, page):
        return self.clone(page=page, override=True)

    def sort(self, *keys):
        sort_keys = ','.join(keys)
        return self.clone(_sort=sort_keys, override=True)

    def __str__(self):  # pragma: no cover
        return '<{0} {1}?{2}>'.format(
            self.__class__.__name__, self.resource_type,
            encode_params(self.params)
        )

    def __repr__(self):  # pragma: no cover
        return self.__str__()


class SyncSearchSet(AbstractSearchSet):
    def fetch(self, *, skip_caching=False):
        bundle_data = self.client._fetch_resource(
            self.resource_type, self.params
        )
        bundle_resource_type = bundle_data.get('resourceType', None)

        if bundle_resource_type != 'Bundle':
            raise InvalidResponse(
                'Expected to receive Bundle '
                'but {0} received'.format(bundle_resource_type)
            )

        resources_data = [
            res['resource'] for res in bundle_data.get('entry', [])
        ]

        resources = []
        for data in resources_data:
            resource = self._perform_resource(data, skip_caching)
            if resource.resource_type == self.resource_type:
                resources.append(resource)

        return resources

    def fetch_raw(self, *, skip_caching=False):
        data = self.client._fetch_resource(
            self.resource_type, self.params
        )
        data_resource_type = data.get('resourceType', None)

        if data_resource_type == 'Bundle':
            for item in data['entry']:
                item.resource = self._perform_resource(
                    item.resource, skip_caching)

        return data

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
            '{0}/{1}'.format(self.resource_type, id)
        )

        if res_data['resourceType'] != self.resource_type:
            raise InvalidResponse(
                'Expected to receive {0} '
                'but {1} received'.format(
                    self.resource_type, res_data['resourceType']
                )
            )

        return self._perform_resource(res_data, skip_caching)

    def count(self):
        new_params = copy.deepcopy(self.params)
        new_params['_count'] = 0
        new_params['_totalMethod'] = 'count'

        return self.client._fetch_resource(
            self.resource_type, params=new_params
        )['total']

    def first(self):
        result = self.limit(1).fetch()

        return result[0] if result else None

    def __iter__(self):
        return iter(self.fetch())


async def aiter(iterable_coroutine):
    items = await iterable_coroutine
    for item in items:
        yield item


class AsyncSearchSet(AbstractSearchSet):
    # TODO: AsyncSearchSet may implements async iterator methods

    async def fetch(self, *, skip_caching=False):
        bundle_data = await self.client._fetch_resource(
            self.resource_type, self.params
        )
        bundle_resource_type = bundle_data.get('resourceType', None)

        if bundle_resource_type != 'Bundle':
            raise InvalidResponse(
                'Expected to receive Bundle '
                'but {0} received'.format(bundle_resource_type)
            )

        resources_data = [
            res['resource'] for res in bundle_data.get('entry', [])
        ]

        resources = []
        for data in resources_data:
            resource = self._perform_resource(data, skip_caching)
            if resource.resource_type == self.resource_type:
                resources.append(resource)

        return resources

    async def fetch_raw(self, *, skip_caching=False):
        data = await self.client._fetch_resource(
            self.resource_type, self.params
        )
        data_resource_type = data.get('resourceType', None)

        if data_resource_type == 'Bundle':
            for item in data['entry']:
                item.resource = self._perform_resource(
                    item.resource, skip_caching)

        return data

    async def fetch_all(self, *, skip_caching=False):
        page = 1
        resources = []

        while True:
            new_resources = await self.page(page).fetch(
                skip_caching=skip_caching
            )
            if not new_resources:
                break

            resources.extend(new_resources)
            page += 1

        return resources

    async def get(self, id, *, skip_caching=False):
        res_data = await self.client._fetch_resource(
            '{0}/{1}'.format(self.resource_type, id)
        )

        if res_data['resourceType'] != self.resource_type:
            raise InvalidResponse(
                'Expected to receive {0} '
                'but {1} received'.format(
                    self.resource_type, res_data['resourceType']
                )
            )

        return self._perform_resource(res_data, skip_caching)

    async def count(self):
        new_params = copy.deepcopy(self.params)
        new_params['_count'] = 0
        new_params['_totalMethod'] = 'count'

        return (
            await
            self.client._fetch_resource(self.resource_type, params=new_params)
        )['total']

    async def first(self):
        result = await self.limit(1).fetch()

        return result[0] if result else None

    def __aiter__(self):
        return aiter(self.fetch())


class AbstractResource(dict):
    client = None

    def __init__(self, client, **kwargs):
        self.client = client

        self._raise_error_if_invalid_keys(kwargs.keys())
        super(AbstractResource, self).__init__(**kwargs)

    def __eq__(self, other):
        return isinstance(other, AbstractResource) \
               and self.reference == other.reference

    def __setitem__(self, key, value):
        self._raise_error_if_invalid_key(key)

        super(AbstractResource, self).__setitem__(key, value)

    def __getitem__(self, key):
        self._raise_error_if_invalid_key(key)

        return super(AbstractResource, self).__getitem__(key)

    def __getattribute__(self, key):
        try:
            return super().__getattribute__(key)
        except AttributeError:
            return self[key]

    def __setattribute__(self, key, value):
        try:
            super().__setattribute__(key, value)
        except AttributeError:
            self[key] = value

    def get_by_path(self, path, default=None):
        keys = parse_path(path)

        self._raise_error_if_invalid_key(keys[0])

        return get_by_path(self, keys, default)

    def get(self, key, default=None):
        self._raise_error_if_invalid_key(key)

        return super(AbstractResource, self).get(key, default)

    def setdefault(self, key, default=None):
        self._raise_error_if_invalid_key(key)

        return super(AbstractResource, self).setdefault(key, default)

    def serialize(self):
        def convert_fn(item):
            if isinstance(item, BaseResource):
                return item.to_reference().serialize(), True
            elif isinstance(item, BaseReference):
                return item.serialize(), True
            else:
                return item, False

        return convert_values(
            {key: value
             for key, value in self.items()}, convert_fn
        )

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

    def _ipython_key_completions_(self):  # pragma: no cover
        return self.get_root_keys()

    def _raise_error_if_invalid_keys(self, keys):
        schema = self.client._get_schema()
        if not schema:
            return
        root_attrs = self.get_root_keys()
        for key in keys:
            if key not in root_attrs:
                raise KeyError(
                    'Invalid key `{0}`. Possible keys are `{1}`'.format(
                        key, ', '.join(root_attrs)
                    )
                )

    def _raise_error_if_invalid_key(self, key):
        self._raise_error_if_invalid_keys([key])


class BaseResource(AbstractResource, ABC):
    resource_type = None

    def __init__(self, client, resource_type, **kwargs):
        def convert_fn(item):
            if isinstance(item, AbstractResource):
                return item, True

            if self.is_reference(item):
                return client.reference(**item), True

            return item, False

        self.resource_type = resource_type
        kwargs['resourceType'] = resource_type
        converted_kwargs = convert_values(kwargs, convert_fn)

        super(BaseResource, self).__init__(client, **converted_kwargs)

    def __setitem__(self, key, value):
        if key == 'resourceType' and 'resourceType' not in self:
            raise KeyError(
                'Can not change `resourceType` after instantiating resource. '
                'You must re-instantiate resource using '
                '`Client.resource` method'
            )

        super(BaseResource, self).__setitem__(key, value)

    def __str__(self):  # pragma: no cover
        return '<{0} {1}>'.format(self.__class__.__name__, self._get_path())

    def __repr__(self):  # pragma: no cover
        return self.__str__()

    def get_root_keys(self):
        schema = self.client._get_schema()
        if not schema:
            return set()
        return set(schema.get(self.resource_type, [])) | \
               {'resourceType', 'id', 'meta', 'extension'}

    @abstractmethod
    def save(self):
        pass

    @abstractmethod
    def delete(self):
        pass

    def to_resource(self, nocache=False):
        """
        Returns Resource instance for this resource
        """
        return self

    def to_reference(self, **kwargs):
        """
        Returns Reference instance for this resource
        """
        if not self.reference:
            raise ResourceNotFound(
                'Can not get reference to unsaved resource without id'
            )

        return self.client.reference(reference=self.reference, **kwargs)

    @abstractmethod
    def is_reference(self, value):
        pass

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
        elif self.resource_type == 'Bundle':
            return ''

        return self.resource_type


class SyncResource(BaseResource):
    def save(self):
        data = self.client._do_request(
            'put' if self.id else 'post',
            self._get_path(),
            data=self.serialize()
        )

        self['meta'] = data.get('meta', {})
        self['id'] = data.get('id')

        self.client._add_resource_to_cache(self)

    def delete(self):
        self.client._remove_resource_from_cache(self)

        return self.client._do_request('delete', self._get_path())


class AsyncResource(BaseResource):
    async def save(self):
        data = await self.client._do_request(
            'put' if self.id else 'post',
            self._get_path(),
            data=self.serialize()
        )

        self['meta'] = data.get('meta', {})
        self['id'] = data.get('id')

        self.client._add_resource_to_cache(self)

    async def delete(self):
        self.client._remove_resource_from_cache(self)

        return await self.client._do_request('delete', self._get_path())

    async def to_resource(self, *args, **kwargs):
        return super(AsyncResource, self).to_resource(*args, **kwargs)


class BaseReference(AbstractResource):
    def __str__(self):  # pragma: no cover
        return '<{0} {1}>'.format(self.__class__.__name__, self.reference)

    def __repr__(self):  # pragma: no cover
        return self.__str__()

    @abstractmethod
    def to_resource(self, nocache=False):
        pass

    def to_reference(self, **kwargs):
        """
        Returns Reference instance for this reference
        """
        return self.client.reference(reference=self.reference, **kwargs)

    @abstractmethod
    def get_root_keys(self):
        pass

    @property
    @abstractmethod
    def reference(self):
        pass

    @property
    @abstractmethod
    def id(self):
        """
        Returns id if reference specifies to the local resource
        """
        pass

    @property
    @abstractmethod
    def resource_type(self):
        """
        Returns resource type if reference specifies to the local resource
        """
        pass

    @property
    @abstractmethod
    def is_local(self):
        pass


class SyncReference(BaseReference):
    def to_resource(self, nocache=False):
        """
        Returns Resource instance for this reference from cache
        if nocache is not specified and from fhir server otherwise.
        """
        if not self.is_local:
            raise ResourceNotFound('Can not resolve not local resource')

        cached_resource = self.client._get_resource_from_cache(
            self.resource_type, self.id
        )

        if cached_resource and not nocache:
            return cached_resource

        return self.client.resources(self.resource_type).get(self.id)


class AsyncReference(BaseReference):
    async def to_resource(self, nocache=False):
        """
        Returns Resource instance for this reference from cache
        if nocache is not specified and from fhir server otherwise.
        """
        if not self.is_local:
            raise ResourceNotFound('Can not resolve not local resource')

        cached_resource = self.client._get_resource_from_cache(
            self.resource_type, self.id
        )

        if cached_resource and not nocache:
            return cached_resource

        return await self.client.resources(self.resource_type).get(self.id)

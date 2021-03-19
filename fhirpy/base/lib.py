import json
import copy
import warnings
from abc import ABC, abstractmethod

import aiohttp
import requests

from yarl import URL
from fhirpy.base.searchset import AbstractSearchSet
from fhirpy.base.resource import BaseResource, BaseReference
from fhirpy.base.utils import (
    AttrDict, encode_params, get_by_path, parse_pagination_url
)
from fhirpy.base.exceptions import (
    ResourceNotFound, OperationOutcome, InvalidResponse, MultipleResourcesFound
)


class AbstractClient(ABC):
    url = None
    authorization = None
    extra_headers = None

    def __init__(self, url, authorization=None, extra_headers=None):
        self.url = url
        self.authorization = authorization
        self.extra_headers = extra_headers

    def __str__(self):  # pragma: no cover
        return '<{0} {1}>'.format(self.__class__.__name__, self.url)

    def __repr__(self):  # pragma: no cover
        return self.__str__()

    @property  # pragma: no cover
    @abstractmethod
    def searchset_class(self):
        pass

    @property  # pragma: no cover
    @abstractmethod
    def resource_class(self):
        pass

    @abstractmethod  # pragma: no cover
    def reference(self, resource_type=None, id=None, reference=None, **kwargs):
        pass

    def resource(self, resource_type=None, **kwargs):
        if resource_type is None:
            raise TypeError('Argument `resource_type` is required')

        return self.resource_class(self, resource_type=resource_type, **kwargs)

    def resources(self, resource_type):
        return self.searchset_class(self, resource_type=resource_type)

    @abstractmethod  # pragma: no cover
    def execute(self, path, method=None, **kwargs):
        pass

    @abstractmethod  # pragma: no cover
    def _do_request(self, method, path, data=None, params=None):
        pass

    @abstractmethod  # pragma: no cover
    def _fetch_resource(self, path, params=None):
        pass

    def _build_request_headers(self):
        headers = {'Authorization': self.authorization, 'Accept': 'application/json'}

        if self.extra_headers is not None:
            headers = {**headers, **self.extra_headers}

        return headers

    def _build_request_url(self, path, params):
        if URL(path).is_absolute():
            if self.url in path:
                return path
            else:
                raise ValueError(
                    f'Request url "{path}" does not contain base url "{self.url}"'
                    ' (possible security issue)'
                )

        params = params or {}
        return f'{self.url}/{path.lstrip("/")}?{encode_params(params)}'


class AsyncClient(AbstractClient, ABC):
    async def execute(self, path, method='post', **kwargs):
        return await self._do_request(method, path, **kwargs)

    async def _do_request(self, method, path, data=None, params=None):
        headers = self._build_request_headers()
        url = self._build_request_url(path, params)
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


class SyncClient(AbstractClient, ABC):
    def execute(self, path, method='post', **kwargs):
        return self._do_request(method, path, **kwargs)

    def _do_request(self, method, path, data=None, params=None):
        if method == 'patch':
            self.extra_headers['Content-Type'] = 'application/json-patch+json'

        headers = self._build_request_headers()
        url = self._build_request_url(path, params)
        r = requests.request(method, url, json=data, headers=headers)

        if 200 <= r.status_code < 300:
            return json.loads(
                r.content.decode(), object_hook=AttrDict
            ) if r.content else None

        if r.status_code == 404 or r.status_code == 410:
            raise ResourceNotFound(r.content.decode())

        raise OperationOutcome(r.content.decode())

    def _fetch_resource(self, path, params=None):
        return self._do_request('get', path, params=params)


class SyncSearchSet(AbstractSearchSet, ABC):
    def fetch(self):
        bundle_data = self.client._fetch_resource(
            self.resource_type, self.params
        )
        resources = self._get_bundle_resources(bundle_data)
        return resources

    def fetch_raw(self):
        data = self.client._fetch_resource(self.resource_type, self.params)
        data_resource_type = data.get('resourceType', None)

        if data_resource_type == 'Bundle':
            for item in data['entry']:
                item.resource = self._perform_resource(item.resource)

        return data

    def fetch_all(self):
        return list([x for x in self])

    def get(self, id=None):
        searchset = self.limit(2)
        if id:
            warnings.warn(
                "parameter 'id' of method get() is deprecated "
                "and will be removed in future versions. "
                "Please use 'search(id='...').get()'",
                DeprecationWarning,
                stacklevel=2
            )
            searchset = searchset.search(_id=id)
        res_data = searchset.fetch()
        if len(res_data) == 0:
            raise ResourceNotFound('No resources found')
        elif len(res_data) > 1:
            raise MultipleResourcesFound('More than one resource found')
        resource = res_data[0]
        return self._perform_resource(resource)

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
        next_link = None
        while True:
            if next_link:
                bundle_data = self.client._fetch_resource(*parse_pagination_url(next_link))
            else:
                bundle_data = self.client._fetch_resource(
                    self.resource_type, self.params
                )
            new_resources = self._get_bundle_resources(bundle_data)
            next_link = get_by_path(bundle_data, ['link', {'relation': 'next'}, 'url'])

            for item in new_resources:
                yield item

            if not next_link:
                break


class AsyncSearchSet(AbstractSearchSet, ABC):
    async def fetch(self):
        bundle_data = await self.client._fetch_resource(
            self.resource_type, self.params
        )
        resources = self._get_bundle_resources(bundle_data)
        return resources

    async def fetch_raw(self):
        data = await self.client._fetch_resource(
            self.resource_type, self.params
        )
        data_resource_type = data.get('resourceType', None)

        if data_resource_type == 'Bundle':
            for item in data['entry']:
                item.resource = self._perform_resource(item.resource)

        return data

    async def fetch_all(self):
        return list([x async for x in self])

    async def get(self, id=None):
        searchset = self.limit(2)
        if id:
            warnings.warn(
                "parameter 'id' of method get() is deprecated "
                "and will be removed in future versions. "
                "Please use 'search(id='...').get()'",
                DeprecationWarning,
                stacklevel=2
            )
            searchset = searchset.search(_id=id)
        res_data = await searchset.fetch()
        if len(res_data) == 0:
            raise ResourceNotFound('No resources found')
        elif len(res_data) > 1:
            raise MultipleResourcesFound('More than one resource found')
        resource = res_data[0]
        return self._perform_resource(resource)

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

    async def __aiter__(self):
        next_link = None
        while True:
            if next_link:
                bundle_data = await self.client._fetch_resource(*parse_pagination_url(next_link))
            else:
                bundle_data = await self.client._fetch_resource(
                    self.resource_type, self.params
                )
            new_resources = self._get_bundle_resources(bundle_data)
            next_link = get_by_path(bundle_data, ['link', {'relation': 'next'}, 'url'])

            for item in new_resources:
                yield item

            if not next_link:
                break


class SyncResource(BaseResource, ABC):
    def save(self, fields=None):
        data = self.serialize()
        if fields:  # Use FHIRPatch if fields for partial update are defined http://hl7.org/fhir/http.html#patch
            if not self.id:
                raise TypeError('Resource `id` is required for update operation')
            request_data = []
            for key in fields:
                operator = 'add'  #TODO add logic to support other operators
                request_data.append(
                    {
                        'op': operator,
                        'path': f'/{key}',
                        'value': data[key]
                    }
                )
            data = request_data
            method = 'patch'
        else:
            method = 'put' if self.id else 'post'
        response_data = self.client._do_request(
            method,
            self._get_path(),
            data=data
        )
        if response_data:
            super(BaseResource, self).clear()
            super(BaseResource, self).update(**self.client.resource(self.resource_type, **response_data))

    def update(self, **kwargs):
        super(BaseResource, self).update(**kwargs)
        self.save(fields=kwargs.keys())

    def delete(self):
        return self.client._do_request('delete', self._get_path())

    def refresh(self):
        data = self.client._do_request('get', self._get_path())
        super(BaseResource, self).clear()
        super(BaseResource, self).update(**data)

    def is_valid(self, raise_exception=False):
        data = self.client._do_request(
            'post',
            '{0}/$validate'.format(self.resource_type),
            data=self.serialize()
        )
        if any(
            issue['severity'] in ['fatal', 'error'] for issue in data['issue']
        ):
            if raise_exception:
                raise OperationOutcome(data)
            return False
        return True

    def execute(self, operation, method='post', data=None, params=None):
        return self.client._do_request(
            method,
            '{0}/{1}'.format(self._get_path(), operation),
            data=data,
            params=params
        )


class AsyncResource(BaseResource, ABC):
    async def save(self, fields=None):
        data = self.serialize()
        if fields:
            if not self.id:
                raise TypeError('Resource `id` is required for update operation')
            data = {key: data[key] for key in fields}
            method = 'patch'
        else:
            method = 'put' if self.id else 'post'

        response_data = await self.client._do_request(
            method,
            self._get_path(),
            data=data
        )
        if response_data:
            super(BaseResource, self).clear()
            super(BaseResource, self).update(**self.client.resource(self.resource_type, **response_data))

    async def update(self, **kwargs):
        super(BaseResource, self).update(**kwargs)
        await self.save(fields=kwargs.keys())

    async def delete(self):
        return await self.client._do_request('delete', self._get_path())

    async def refresh(self):
        data = await self.client._do_request('get', self._get_path())
        super(BaseResource, self).clear()
        super(BaseResource, self).update(**data)

    async def to_resource(self):
        return super(AsyncResource, self).to_resource()

    async def is_valid(self, raise_exception=False):
        data = await self.client._do_request(
            'post',
            '{0}/$validate'.format(self.resource_type),
            data=self.serialize()
        )
        if any(
            issue['severity'] in ['fatal', 'error'] for issue in data['issue']
        ):
            if raise_exception:
                raise OperationOutcome(data)
            return False
        return True

    async def execute(self, operation, method='post', **kwargs):
        return await self.client._do_request(
            method, '{0}/{1}'.format(self._get_path(), operation), **kwargs
        )


class SyncReference(BaseReference, ABC):
    def to_resource(self):
        """
        Returns Resource instance for this reference
        from fhir server otherwise.
        """
        if not self.is_local:
            raise ResourceNotFound('Can not resolve not local resource')
        return self.client.resources(self.resource_type).search(_id=self.id
                                                               ).get()

    def execute(self, operation, method='post', **kwargs):
        if not self.is_local:
            raise ResourceNotFound('Can not execute on not local resource')
        return self.client._do_request(
            method,
            '{0}/{1}/{2}'.format(self.resource_type, self.id,
                                 operation), **kwargs
        )


class AsyncReference(BaseReference, ABC):
    async def to_resource(self):
        """
        Returns Resource instance for this reference
        from fhir server otherwise.
        """
        if not self.is_local:
            raise ResourceNotFound('Can not resolve not local resource')
        return await self.client.resources(self.resource_type
                                          ).search(_id=self.id).get()

    async def execute(self, operation, method='post', **kwargs):
        if not self.is_local:
            raise ResourceNotFound('Can not execute on not local resource')
        return await self.client._do_request(
            method,
            '{0}/{1}/{2}'.format(self.resource_type, self.id,
                                 operation), **kwargs
        )

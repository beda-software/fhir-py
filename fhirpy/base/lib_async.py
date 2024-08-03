import copy
import json
import warnings
from abc import ABC
from collections.abc import AsyncGenerator
from typing import Any, Generic, Literal, TypeVar, Union, overload

import aiohttp

from fhirpy.base.client import AbstractClient
from fhirpy.base.exceptions import MultipleResourcesFound, OperationOutcome, ResourceNotFound
from fhirpy.base.resource import BaseReference, BaseResource, serialize_resource
from fhirpy.base.resource_protocol import TResource, get_resource_path, get_resource_type_from_class
from fhirpy.base.searchset import AbstractSearchSet
from fhirpy.base.utils import AttrDict, get_by_path, parse_pagination_url


class AsyncClient(AbstractClient, ABC):
    aiohttp_config: dict

    def __init__(
        self,
        url: str,
        authorization: Union[str, None] = None,
        extra_headers: Union[dict, None] = None,
        aiohttp_config: Union[dict, None] = None,
    ):
        self.aiohttp_config = aiohttp_config or {}

        super().__init__(url, authorization, extra_headers)

    async def execute(
        self,
        path,
        method="post",
        data: Union[dict, None] = None,
        params: Union[dict, None] = None,
    ):
        return await self._do_request(method, path, data=data, params=params)

    @overload
    async def save(
        self,
        resource: TResource,
        fields: Union[list, None] = None,
        *,
        _search_params: Union[dict, None] = None,
        _as_dict: Literal[True] = True,
    ) -> Any:
        ...

    @overload
    async def save(
        self,
        resource: TResource,
        fields: Union[list, None] = None,
        *,
        _search_params: Union[dict, None] = None,
        _as_dict: Literal[False] = False,
    ) -> TResource:
        ...

    async def save(
        self,
        resource: TResource,
        fields: Union[list, None] = None,
        *,
        # TODO: I would like to deprecate search_params
        # TODO: we have search set for conditional create
        _search_params: Union[dict, None] = None,
        # _as_dict is a private api used internally
        _as_dict: bool = False,
    ) -> Union[TResource, Any]:
        data = serialize_resource(resource)
        if fields:
            if not resource.id:
                raise TypeError("Resource `id` is required for update operation")
            data = {key: data[key] for key in fields}
            method = "patch"
        else:
            method = "put" if resource.id else "post"

        response_data = await self._do_request(
            method, get_resource_path(resource), data=data, params=_search_params
        )

        if _as_dict:
            return response_data

        return resource.__class__(**response_data)

    async def create(self, resource: TResource) -> TResource:
        return await self.save(resource)

    async def update(self, resource: TResource) -> TResource:
        if not resource.id:
            raise TypeError("Resource `id` is required for update operation")
        return await self.save(resource)

    @overload
    async def patch(self, resource_type: type[TResource], id: str, **kwargs) -> TResource:
        ...

    @overload
    async def patch(self, resource_type: str, id: str, **kwargs) -> Any:
        ...

    async def patch(
        self,
        resource_type: Union[str, type[TResource]],
        id: str,  # noqa: A002
        **kwargs,
    ) -> Union[TResource, Any]:
        resource_type_str = (
            resource_type
            if isinstance(resource_type, str)
            else get_resource_type_from_class(resource_type)
        )
        custom_resource_class = None if isinstance(resource_type, str) else resource_type

        response_data = await self._do_request("patch", f"{resource_type_str}/{id}", data=kwargs)

        if custom_resource_class:
            return custom_resource_class(**response_data)

        return response_data

    async def delete(self, resource_type: Union[str, type[TResource]], id: str):  # noqa: A002
        resource_type_str = (
            resource_type
            if isinstance(resource_type, str)
            else get_resource_type_from_class(resource_type)
        )
        return await self._do_request("delete", f"{resource_type_str}/{id}")

    @overload
    async def _do_request(
        self,
        method: str,
        path: str,
        data: Union[dict, None] = None,
        params: Union[dict, None] = None,
        returning_status: Literal[False] = False,
    ) -> Any:
        ...

    @overload
    async def _do_request(
        self,
        method: str,
        path: str,
        data: Union[dict, None] = None,
        params: Union[dict, None] = None,
        returning_status: Literal[True] = True,
    ) -> tuple[Any, int]:
        ...

    async def _do_request(
        self,
        method: str,
        path: str,
        data: Union[dict, None] = None,
        params: Union[dict, None] = None,
        returning_status=False,
    ) -> Union[Any, tuple[Any, int]]:
        headers = self._build_request_headers()
        url = self._build_request_url(path, params)
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.request(method, url, json=data, **self.aiohttp_config) as r:
                if 200 <= r.status < 300:  # noqa: PLR2004
                    raw_data = await r.text()
                    r_data = json.loads(raw_data, object_hook=AttrDict) if raw_data else None
                    return (r_data, r.status) if returning_status else r_data

                if r.status in (404, 410):
                    raise ResourceNotFound(await r.text())

                if r.status == 412:  # noqa: PLR2004
                    raise MultipleResourcesFound(await r.text())

                raw_data = await r.text()
                try:
                    parsed_data = json.loads(raw_data)
                    if parsed_data["resourceType"] == "OperationOutcome":
                        raise OperationOutcome(resource=parsed_data)
                    raise OperationOutcome(reason=raw_data)
                except (KeyError, json.JSONDecodeError) as exc:
                    raise OperationOutcome(reason=raw_data) from exc

    async def _fetch_resource(self, path, params=None):
        return await self._do_request("get", path, params=params)


TAsyncClient = TypeVar("TAsyncClient", bound=AsyncClient)


class AsyncResource(Generic[TAsyncClient], BaseResource[TAsyncClient], ABC):
    async def save(
        self, fields: Union[list[str], None] = None, search_params: Union[dict, None] = None
    ):
        response_data = await self.client.save(
            self, fields=fields, _search_params=search_params, _as_dict=True
        )

        if response_data:
            resource_type = self.resource_type
            super(BaseResource, self).clear()
            super(BaseResource, self).update(**self.client.resource(resource_type, **response_data))

    async def create(self, **kwargs):
        await self.save(search_params=kwargs)
        return self

    async def update(self):
        if not self.id:
            raise TypeError("Resource `id` is required for update operation")
        await self.save()

    async def patch(self, **kwargs):
        super(BaseResource, self).update(**kwargs)
        await self.save(fields=kwargs.keys())

    async def delete(self):
        if not self.id:
            raise TypeError("Resource `id` is required for delete operation")
        return await self.client.delete(self.resource_type, self.id)

    async def refresh(self):
        data = await self.client._do_request("get", self._get_path())
        super(BaseResource, self).clear()
        super(BaseResource, self).update(**data)

    async def to_resource(self):
        return super().to_resource()

    async def is_valid(self, raise_exception=False):
        data = await self.client._do_request(
            "post", f"{self.resource_type}/$validate", data=self.serialize()
        )
        if any(issue["severity"] in ["fatal", "error"] for issue in data["issue"]):
            if raise_exception:
                raise OperationOutcome(resource=data)
            return False
        return True

    async def execute(
        self,
        operation: str,
        method: str = "post",
        data: Union[dict, None] = None,
        params: Union[dict, None] = None,
    ) -> Any:
        return await self.client._do_request(
            method,
            f"{self._get_path()}/{operation}",
            data=data,
            params=params,
        )


class AsyncReference(Generic[TAsyncClient], BaseReference[TAsyncClient], ABC):
    async def to_resource(self):
        """
        Returns Resource instance for this reference
        from fhir server otherwise.
        """
        if not self.is_local:
            raise ResourceNotFound("Can not resolve not local resource")
        resource_data = await self.client._do_request("get", f"{self.resource_type}/{self.id}")
        return self._dict_to_resource(resource_data)

    async def execute(self, operation, method="post", **kwargs):
        if not self.is_local:
            raise ResourceNotFound("Can not execute on not local resource")
        return await self.client._do_request(
            method,
            f"{self.resource_type}/{self.id}/{operation}",
            **kwargs,
        )


class AsyncSearchSet(
    Generic[TAsyncClient, TResource], AbstractSearchSet[TAsyncClient, TResource], ABC
):
    async def fetch(self) -> list[TResource]:
        bundle_data = await self.client._fetch_resource(self.resource_type, self.params)

        return self._get_bundle_resources(bundle_data)

    # It's difficult to specify type for it, because there's implicit transformation for resources
    async def fetch_raw(self) -> Any:
        data = await self.client._fetch_resource(self.resource_type, self.params)
        data_resource_type = data.get("resourceType", None)

        if data_resource_type == "Bundle":
            for item in data["entry"]:
                item.resource = self._dict_to_resource(item.resource)

        return data

    async def fetch_all(self) -> list[TResource]:
        return [x async for x in self]

    async def get(self, id=None) -> TResource:  # noqa: A002
        searchset = self.limit(2)
        if id:
            warnings.warn(
                "parameter `id` of method get() is deprecated "
                "and will be removed in future versions. "
                "Please use `search(id='...').get()`",
                DeprecationWarning,
                stacklevel=2,
            )
            searchset = searchset.search(_id=id)
        res_data = await searchset.fetch()
        if len(res_data) == 0:
            raise ResourceNotFound("No resources found")
        if len(res_data) > 1:
            raise MultipleResourcesFound("More than one resource found")
        return res_data[0]

    async def count(self) -> int:
        new_params = copy.deepcopy(self.params)
        new_params["_count"] = 0
        new_params["_totalMethod"] = "count"

        return (await self.client._fetch_resource(self.resource_type, params=new_params))["total"]

    async def first(self) -> Union[TResource, None]:
        result = await self.limit(1).fetch()

        return result[0] if result else None

    async def get_or_create(self, resource: TResource) -> tuple[TResource, bool]:
        assert resource.resourceType == self.resource_type
        response_data, status_code = await self.client._do_request(
            "POST",
            self.resource_type,
            serialize_resource(resource),
            self.params,
            returning_status=True,
        )
        return self._dict_to_resource(response_data), (status_code == 201)  # noqa: PLR2004

    async def update(self, resource: TResource) -> tuple[TResource, bool]:
        # TODO: Support cases where resource with id is provided
        # accordingly to the https://build.fhir.org/http.html#cond-update
        assert resource.resourceType == self.resource_type
        response_data, status_code = await self.client._do_request(
            "PUT",
            self.resource_type,
            serialize_resource(resource),
            self.params,
            returning_status=True,
        )
        return self._dict_to_resource(response_data), (status_code == 201)  # noqa: PLR2004

    # TODO: think about partial TResource support
    async def patch(self, _resource: Any = None, **kwargs) -> TResource:
        warnings.warn(
            "The first arg of method patch() is deprecated "
            "and will be removed in future versions. "
            "Please use `patch(key=value)`",
            DeprecationWarning,
            stacklevel=2,
        )
        data = serialize_resource(_resource if _resource is not None else kwargs)
        response_data = await self.client._do_request(
            "PATCH", self.resource_type, data, self.params
        )
        return self._dict_to_resource(response_data)

    async def delete(self) -> Any:
        return await self.client._do_request(
            "DELETE", self.resource_type, params=self.params, returning_status=True
        )

    async def __aiter__(self) -> AsyncGenerator[TResource, None]:
        next_link = None
        while True:
            if next_link:
                bundle_data = await self.client._fetch_resource(*parse_pagination_url(next_link))
            else:
                bundle_data = await self.client._fetch_resource(self.resource_type, self.params)
            new_resources = self._get_bundle_resources(bundle_data)
            next_link = get_by_path(bundle_data, ["link", {"relation": "next"}, "url"])

            for item in new_resources:
                yield item

            if not next_link:
                break
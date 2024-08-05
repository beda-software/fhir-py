import copy
import json
import warnings
from abc import ABC
from collections.abc import Generator
from typing import Any, Generic, Literal, TypeVar, Union, cast, overload

import requests

from fhirpy.base.client import AbstractClient
from fhirpy.base.exceptions import MultipleResourcesFound, OperationOutcome, ResourceNotFound
from fhirpy.base.resource import BaseReference, BaseResource, serialize
from fhirpy.base.resource_protocol import (
    TReference,
    TResource,
    get_resource_path,
    get_resource_type_id_and_class,
)
from fhirpy.base.searchset import AbstractSearchSet
from fhirpy.base.utils import AttrDict, get_by_path, parse_pagination_url


class SyncClient(AbstractClient, ABC):
    requests_config: dict

    def __init__(
        self,
        url: str,
        authorization: Union[str, None] = None,
        extra_headers: Union[dict, None] = None,
        requests_config: Union[dict, None] = None,
    ):
        self.requests_config = requests_config or {}

        super().__init__(url, authorization, extra_headers)

    def execute(
        self,
        path: str,
        method: str = "post",
        data: Union[dict, None] = None,
        params: Union[dict, None] = None,
    ) -> Any:
        return self._do_request(method, path, data=data, params=params)

    @overload
    def get(self, resource_type_or_resource: TResource, id: None = None) -> TResource:
        ...

    @overload
    def get(
        self, resource_type_or_resource: type[TResource], id: Union[str, None] = None
    ) -> TResource:
        ...

    @overload
    def get(self, resource_type_or_resource: str, id: Union[str, None] = None) -> Any:
        ...

    def get(
        self,
        resource_type_or_resource: Union[str, type[TResource], TResource],
        id: Union[str, None] = None,  # noqa: A002
    ) -> Union[TResource, Any]:
        resource_type, resource_id, custom_resource_class = get_resource_type_id_and_class(
            resource_type_or_resource, id
        )

        if resource_id is None:
            raise TypeError("Resource `id` is required for get operation")

        response_data = self._do_request("get", f"{resource_type}/{resource_id}")

        if custom_resource_class:
            return custom_resource_class(**response_data)

        return response_data

    @overload
    def save(
        self,
        resource: TResource,
        fields: Union[list, None] = None,
        *,
        _search_params: Union[dict, None] = None,
        _as_dict: Literal[False] = False,
    ) -> TResource:
        ...

    @overload
    def save(
        self,
        resource: TResource,
        fields: Union[list, None] = None,
        *,
        _search_params: Union[dict, None] = None,
        _as_dict: Literal[True] = True,
    ) -> Any:
        ...

    def save(
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
        data = serialize(resource)
        if fields:
            if not resource.id:
                raise TypeError("Resource `id` is required for update operation")
            data = {key: data[key] for key in fields}
            method = "patch"
        else:
            method = "put" if resource.id else "post"

        response_data = self._do_request(
            method, get_resource_path(resource), data=data, params=_search_params
        )

        if _as_dict:
            return response_data

        return resource.__class__(**response_data)

    def create(self, resource: TResource) -> TResource:
        return self.save(resource)

    def update(self, resource: TResource) -> TResource:
        if not resource.id:
            raise TypeError("Resource `id` is required for update operation")
        return self.save(resource)

    @overload
    def patch(self, resource_type_or_resource: TResource, id: None = None, **kwargs) -> TResource:
        ...

    @overload
    def patch(
        self, resource_type_or_resource: type[TResource], id: Union[str, None] = None, **kwargs
    ) -> TResource:
        ...

    @overload
    def patch(self, resource_type_or_resource: str, id: Union[str, None] = None, **kwargs) -> Any:
        ...

    def patch(
        self,
        resource_type_or_resource: Union[str, type[TResource], TResource],
        id: Union[str, None] = None,  # noqa: A002
        **kwargs,
    ) -> Union[TResource, Any]:
        resource_type, resource_id, custom_resource_class = get_resource_type_id_and_class(
            resource_type_or_resource, id
        )

        if resource_id is None:
            raise TypeError("Resource `id` is required for patch operation")

        response_data = self._do_request(
            "patch", f"{resource_type}/{resource_id}", data=serialize(kwargs)
        )

        if custom_resource_class:
            return custom_resource_class(**response_data)

        return response_data

    def delete(
        self,
        resource_type_or_resource: Union[str, type[TResource], TResource],
        id: Union[str, None] = None,  # noqa: A002
    ):
        resource_type, resource_id, _ = get_resource_type_id_and_class(
            resource_type_or_resource, id
        )

        if resource_id is None:
            raise TypeError("Resource `id` is required for delete operation")

        return self._do_request("delete", f"{resource_type}/{resource_id}")

    @overload
    def _do_request(
        self,
        method: str,
        path: str,
        data: Union[dict, None] = None,
        params: Union[dict, None] = None,
        returning_status: Literal[False] = False,
    ) -> Any:
        ...

    @overload
    def _do_request(
        self,
        method: str,
        path: str,
        data: Union[dict, None] = None,
        params: Union[dict, None] = None,
        returning_status: Literal[True] = True,
    ) -> tuple[Any, int]:
        ...

    def _do_request(
        self,
        method: str,
        path: str,
        data: Union[dict, None] = None,
        params: Union[dict, None] = None,
        returning_status=False,
    ):
        headers = self._build_request_headers()
        url = self._build_request_url(path, params)
        r = requests.request(method, url, json=data, headers=headers, **self.requests_config)

        if 200 <= r.status_code < 300:  # noqa: PLR2004
            r_data = json.loads(r.content.decode(), object_hook=AttrDict) if r.content else None
            return (r_data, r.status_code) if returning_status else r_data

        if r.status_code in (404, 410):
            raise ResourceNotFound(r.content.decode())

        if r.status_code == 412:  # noqa: PLR2004
            raise MultipleResourcesFound(r.content.decode())

        raw_data = r.content.decode()
        try:
            parsed_data = json.loads(raw_data)
            if parsed_data["resourceType"] == "OperationOutcome":
                raise OperationOutcome(resource=parsed_data)
            raise OperationOutcome(reason=raw_data)
        except (KeyError, json.JSONDecodeError) as exc:
            raise OperationOutcome(reason=raw_data) from exc

    def _fetch_resource(self, path, params=None):
        return self._do_request("get", path, params=params)


TSyncClient = TypeVar("TSyncClient", bound=SyncClient)


class SyncResource(
    Generic[TSyncClient, TResource, TReference],
    BaseResource[TSyncClient, TResource, TReference],
    ABC,
):
    def save(
        self, fields: Union[list[str], None] = None, search_params: Union[dict, None] = None
    ) -> TResource:
        response_data = self.__client__.save(
            self, fields, _search_params=search_params, _as_dict=True
        )
        if response_data:
            resource_type = self.resource_type
            super(BaseResource, self).clear()
            super(BaseResource, self).update(
                **self.__client__.resource(resource_type, **response_data)
            )

        return cast(TResource, self)

    def create(self, **kwargs):
        self.save(search_params=kwargs)

        return cast(TResource, self)

    def update(self) -> TResource:  # type: ignore
        if not self.id:
            raise TypeError("Resource `id` is required for update operation")
        self.save()

        return cast(TResource, self)

    def patch(self, **kwargs) -> TResource:
        super(BaseResource, self).update(**kwargs)
        self.save(fields=list(kwargs.keys()))

        return cast(TResource, self)

    def delete(self):
        if not self.id:
            raise TypeError("Resource `id` is required for delete operation")
        return self.__client__.delete(self)

    def refresh(self) -> TResource:
        data = self.__client__._do_request("get", self._get_path())
        super(BaseResource, self).clear()
        super(BaseResource, self).update(**data)

        return cast(TResource, self)

    def to_resource(self) -> TResource:
        return cast(TResource, self)

    def is_valid(self, raise_exception=False) -> bool:
        data = self.__client__.execute(
            f"{self.resource_type}/$validate", method="post", data=self.serialize()
        )
        if any(issue["severity"] in ["fatal", "error"] for issue in data["issue"]):
            if raise_exception:
                raise OperationOutcome(resource=data)
            return False
        return True

    def execute(
        self,
        operation: str,
        method: str = "post",
        data: Union[dict, None] = None,
        params: Union[dict, None] = None,
    ) -> Any:
        return self.__client__.execute(
            f"{self._get_path()}/{operation}",
            method=method,
            data=data,
            params=params,
        )


class SyncReference(
    Generic[TSyncClient, TResource, TReference],
    BaseReference[TSyncClient, TResource, TReference],
    ABC,
):
    def to_resource(self) -> TResource:
        """
        Returns Resource instance for this reference
        from fhir server otherwise.
        """
        if not self.is_local:
            raise ResourceNotFound("Can not resolve not local resource")
        resource_data = self.__client__.execute(
            f"{self.resource_type}/{self.id}",
            method="get",
        )
        return self._dict_to_resource(resource_data)

    def execute(
        self,
        operation,
        method="post",
        data: Union[dict, None] = None,
        params: Union[dict, None] = None,
    ):
        if not self.is_local:
            raise ResourceNotFound("Can not execute on not local resource")
        return self.__client__.execute(
            f"{self.resource_type}/{self.id}/{operation}",
            method=method,
            data=data,
            params=params,
        )

    def patch(self, **kwargs) -> TResource:
        resource_data = self.__client__.patch(self.reference, **kwargs)
        return self._dict_to_resource(resource_data)

    def delete(self):
        return self.__client__.delete(self.reference)


class SyncSearchSet(
    Generic[TSyncClient, TResource], AbstractSearchSet[TSyncClient, TResource], ABC
):
    def execute(
        self,
        operation: str,
        method: str = "post",
        data: Union[dict, None] = None,
        params: Union[dict, None] = None,
    ) -> Any:
        return self.client.execute(
            f"{self.resource_type}/{operation}",
            method=method,
            data=data,
            params=params,
        )

    def fetch(self) -> list[TResource]:
        bundle_data = self.client._fetch_resource(self.resource_type, self.params)

        return self._get_bundle_resources(bundle_data)

    # It's difficult to specify type for it, because there's implicit transformation for resources
    def fetch_raw(self) -> Any:
        data = self.client._fetch_resource(self.resource_type, self.params)
        data_resource_type = data.get("resourceType", None)

        if data_resource_type == "Bundle":
            for item in data["entry"]:
                item.resource = self._dict_to_resource(item.resource)

        return data

    def fetch_all(self) -> list[TResource]:
        return list(self)

    def get(self, id=None) -> TResource:  # noqa: A002
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
        res_data = searchset.fetch()
        if len(res_data) == 0:
            raise ResourceNotFound("No resources found")
        if len(res_data) > 1:
            raise MultipleResourcesFound("More than one resource found")
        return res_data[0]

    def count(self) -> int:
        new_params = copy.deepcopy(self.params)
        new_params["_count"] = 0
        new_params["_totalMethod"] = "count"

        return self.client._fetch_resource(self.resource_type, params=new_params)["total"]

    def first(self) -> Union[TResource, None]:
        result = self.limit(1).fetch()

        return result[0] if result else None

    def get_or_create(self, resource: TResource) -> tuple[TResource, int]:
        assert resource.resourceType == self.resource_type
        response_data, status_code = self.client._do_request(
            "post",
            self.resource_type,
            serialize(resource),
            self.params,
            returning_status=True,
        )
        return self._dict_to_resource(response_data), (status_code == 201)  # noqa: PLR2004

    def update(self, resource: TResource) -> tuple[TResource, int]:
        # TODO: Support cases where resource with id is provided
        # accordingly to the https://build.fhir.org/http.html#cond-update
        assert resource.resourceType == self.resource_type
        response_data, status_code = self.client._do_request(
            "put",
            self.resource_type,
            serialize(resource),
            self.params,
            returning_status=True,
        )
        return self._dict_to_resource(response_data), (status_code == 201)  # noqa: PLR2004

    def patch(self, _resource: Any = None, **kwargs) -> TResource:
        if _resource is not None:
            warnings.warn(
                "The first arg of method patch() is deprecated "
                "and will be removed in future versions. "
                "Please use `patch(key=value)`",
                DeprecationWarning,
                stacklevel=2,
            )

        data = serialize(_resource if _resource is not None else kwargs)
        response_data = self.client._do_request("patch", self.resource_type, data, self.params)
        return self._dict_to_resource(response_data)

    def delete(self) -> Any:
        return self.client._do_request(
            "delete", self.resource_type, params=self.params, returning_status=True
        )

    def __iter__(self) -> Generator[TResource, None, None]:
        next_link = None
        while True:
            if next_link:
                bundle_data = self.client._fetch_resource(*parse_pagination_url(next_link))
            else:
                bundle_data = self.client._fetch_resource(self.resource_type, self.params)
            new_resources = self._get_bundle_resources(bundle_data)
            next_link = get_by_path(bundle_data, ["link", {"relation": "next"}, "url"])

            yield from new_resources

            if not next_link:
                break

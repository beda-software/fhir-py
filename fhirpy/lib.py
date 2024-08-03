from abc import ABC
from typing import Generic, Union, overload

from fhirpy.base.client import TClient
from fhirpy.base.resource import BaseReference, BaseResource
from fhirpy.base.resource_protocol import TReference, TResource

from .base import (
    AsyncClient,
    AsyncReference,
    AsyncResource,
    AsyncSearchSet,
    SyncClient,
    SyncReference,
    SyncResource,
    SyncSearchSet,
)


class SyncFHIRSearchSet(Generic[TResource], SyncSearchSet["SyncFHIRClient", TResource]):
    pass


class AsyncFHIRSearchSet(Generic[TResource], AsyncSearchSet["AsyncFHIRClient", TResource]):
    pass


class BaseFHIRResource(
    Generic[TClient, TResource, TReference], BaseResource[TClient, TResource, TReference], ABC
):
    def is_reference(self, value):
        if not isinstance(value, dict):
            return False

        return "reference" in value and not (
            set(value.keys()) - {"reference", "display", "type", "identifier", "extension"}
        )


class SyncFHIRResource(
    BaseFHIRResource["SyncFHIRClient", "SyncFHIRResource", "SyncFHIRReference"],
    SyncResource["SyncFHIRClient", "SyncFHIRResource", "SyncFHIRReference"],
):
    pass


class AsyncFHIRResource(
    BaseFHIRResource["AsyncFHIRClient", "AsyncFHIRResource", "AsyncFHIRReference"],
    AsyncResource["AsyncFHIRClient", "AsyncFHIRResource", "AsyncFHIRReference"],
):
    pass


class BaseFHIRReference(
    Generic[TClient, TResource, TReference], BaseReference[TClient, TResource, TReference], ABC
):
    @property
    def reference(self):
        return self["reference"]

    @property
    def id(self):
        """
        Returns id if reference specifies to the local resource
        """
        if self.is_local:
            return self.reference.split("/", 1)[1]

        return None

    @property
    def resource_type(self):
        """
        Returns resource type if reference specifies to the local resource
        """
        if self.is_local:
            return self.reference.split("/", 1)[0]

        return None

    @property
    def is_local(self):
        return self.reference.count("/") == 1


class SyncFHIRReference(
    BaseFHIRReference["SyncFHIRClient", "SyncFHIRResource", "SyncFHIRReference"],
    SyncReference["SyncFHIRClient", "SyncFHIRResource", "SyncFHIRReference"],
):
    pass


class AsyncFHIRReference(
    BaseFHIRReference["AsyncFHIRClient", "AsyncFHIRResource", "AsyncFHIRReference"],
    AsyncReference["AsyncFHIRClient", "AsyncFHIRResource", "AsyncFHIRReference"],
):
    pass


class SyncFHIRClient(SyncClient):
    def reference(self, resource_type=None, id=None, reference=None, **kwargs):  # noqa: A002
        if resource_type and id:
            reference = f"{resource_type}/{id}"

        if not reference:
            raise TypeError("Arguments `resource_type` and `id` or `reference` are required")
        return SyncFHIRReference(self, reference=reference, **kwargs)

    @overload
    def resource(self, resource_type: str, **kwargs) -> SyncFHIRResource:
        ...

    @overload
    def resource(self, resource_type: type[TResource], **kwargs) -> TResource:
        ...

    def resource(
        self, resource_type: Union[str, type[TResource]], **kwargs
    ) -> Union[SyncFHIRResource, TResource]:
        if isinstance(resource_type, str):
            return SyncFHIRResource(self, resource_type=resource_type, **kwargs)

        return resource_type(**kwargs)

    @overload
    def resources(self, resource_type: str) -> SyncFHIRSearchSet[SyncFHIRResource]:
        ...

    @overload
    def resources(self, resource_type: type[TResource]) -> SyncFHIRSearchSet[TResource]:
        ...

    def resources(
        self, resource_type: Union[str, type[TResource]]
    ) -> Union[SyncFHIRSearchSet[TResource], SyncFHIRSearchSet[SyncFHIRResource]]:
        return SyncFHIRSearchSet(self, resource_type=resource_type)


class AsyncFHIRClient(AsyncClient):
    def reference(
        self,
        resource_type: Union[str, None] = None,
        id: Union[str, None] = None,  # noqa: A002
        reference: Union[str, None] = None,
        **kwargs,
    ):
        if resource_type and id:
            reference = f"{resource_type}/{id}"

        if not reference:
            raise TypeError("Arguments `resource_type` and `id` or `reference` are required")
        return AsyncFHIRReference(self, reference=reference, **kwargs)

    @overload
    def resource(self, resource_type: str, **kwargs) -> AsyncFHIRResource:
        ...

    @overload
    def resource(self, resource_type: type[TResource], **kwargs) -> TResource:
        ...

    def resource(
        self, resource_type: Union[str, type[TResource]], **kwargs
    ) -> Union[AsyncFHIRResource, TResource]:
        if isinstance(resource_type, str):
            return AsyncFHIRResource(self, resource_type, **kwargs)

        return resource_type(**kwargs)

    @overload
    def resources(self, resource_type: str) -> AsyncFHIRSearchSet[AsyncFHIRResource]:
        ...

    @overload
    def resources(self, resource_type: type[TResource]) -> AsyncFHIRSearchSet[TResource]:
        ...

    def resources(
        self, resource_type: Union[str, type[TResource]]
    ) -> Union[AsyncFHIRSearchSet[TResource], AsyncFHIRSearchSet[AsyncFHIRResource]]:
        return AsyncFHIRSearchSet(self, resource_type)

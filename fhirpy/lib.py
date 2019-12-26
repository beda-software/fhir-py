from abc import ABC

from fhirpy.base.resource import BaseResource, BaseReference
from .base import (
    SyncClient, AsyncClient, SyncSearchSet, AsyncSearchSet,
    SyncResource, AsyncResource, SyncReference, AsyncReference
)


class SyncFHIRSearchSet(SyncSearchSet):
    pass


class AsyncFHIRSearchSet(AsyncSearchSet):
    pass


class BaseFHIRResource(BaseResource, ABC):
    def is_reference(self, value):
        if not isinstance(value, dict):
            return False

        return 'reference' in value and \
               not (set(value.keys()) - {'reference', 'display'})

    @property
    def reference(self):
        """
        Returns reference if local resource is saved
        """
        if self.id:
            return '{0}/{1}'.format(self.resource_type, self.id)


class SyncFHIRResource(BaseFHIRResource, SyncResource):
    pass


class AsyncFHIRResource(BaseFHIRResource, AsyncResource):
    pass


class BaseFHIRReference(BaseReference, ABC):
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
        return self.reference.count('/') == 1


class SyncFHIRReference(BaseFHIRReference, SyncReference):
    pass


class AsyncFHIRReference(BaseFHIRReference, AsyncReference):
    pass


class SyncFHIRClient(SyncClient):
    searchset_class = SyncFHIRSearchSet
    resource_class = SyncFHIRResource

    def __init__(self, url, authorization=None, extra_headers=None):
        super(SyncFHIRClient, self).__init__(url, authorization, extra_headers)

    def reference(self, resource_type=None, id=None, reference=None, **kwargs):
        if resource_type and id:
            reference = '{0}/{1}'.format(resource_type, id)

        if not reference:
            raise TypeError(
                'Arguments `resource_type` and `id` or `reference` '
                'are required'
            )
        return SyncFHIRReference(self, reference=reference, **kwargs)


class AsyncFHIRClient(AsyncClient):
    searchset_class = AsyncFHIRSearchSet
    resource_class = AsyncFHIRResource

    def __init__(self, url, authorization=None, extra_headers=None):
        super(AsyncFHIRClient, self).__init__(url, authorization, extra_headers)

    def reference(self, resource_type=None, id=None, reference=None, **kwargs):
        if resource_type and id:
            reference = '{0}/{1}'.format(resource_type, id)

        if not reference:
            raise TypeError(
                'Arguments `resource_type` and `id` or `reference` '
                'are required'
            )
        return AsyncFHIRReference(self, reference=reference, **kwargs)

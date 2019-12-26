from .lib import (
    SyncClient,
    AsyncClient,
    SyncSearchSet,
    AsyncSearchSet,
    SyncResource,
    AsyncResource,
    SyncReference,
    AsyncReference,
)

# TODO: Remove in 1.2.0
SyncAbstractClient = SyncClient
AsyncAbstractClient = AsyncClient

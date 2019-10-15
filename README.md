[![Build Status](https://travis-ci.org/beda-software/fhir-py.svg?branch=master)](https://travis-ci.org/beda-software/fhir-py)
[![codecov](https://codecov.io/gh/beda-software/fhir-py/branch/master/graph/badge.svg)](https://codecov.io/gh/beda-software/fhir-py)
[![pypi](https://img.shields.io/pypi/v/fhirpy.svg)](https://pypi.python.org/pypi/fhirpy)

# fhir-py
async/sync FHIR client for python.
This package provides an API for CRUD operations over FHIR resources

# Getting started
## Async example
```Python
import asyncio
from fhirpy import AsyncFHIRClient

async def main():
    # Create an instance
    client = AsyncFHIRClient(
        'http://fhir-server/',
        fhir_version='4.0.0',
        authorization='Bearer TOKEN',
    )

    # Search for patients
    resources = client.resources('Patient')  # Return lazy search set
    resources = resources.search(name='John').limit(10).page(2).sort('name')
    print(await resources.fetch())  # Returns list of AsyncFHIRResource

    # Create Organization resource
    organization = client.resource(
        'Organization',
        name='beda.software'
    )
    await organization.save()

    # Get patient resource by reference and delete
    patient_ref = client.reference('Patient', 'new_patient')
    patient_res = await patient_ref.to_resource()
    await patient_res.delete()

    # Iterate over search set
    org_resources = client.resources('Organization')
    async for org_resource in org_resources:
        print(org_resource.serialize())

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
```


# Main class structure
Both async and sync clients have identical sets of classes and methods.

|               | Sync                | Async                |
| ------------- | ------------------- | -------------------- |
| Client        | SyncFHIRClient      | AsyncFHIRClient      |
| SearchSet     | SyncFHIRSearchSet   | AsyncFHIRSearchSet   |
| Resource      | SyncFHIRResource    | AsyncFHIRResource    |
| Reference     | SyncFHIRReference   | AsyncFHIRReference   |


# AsyncFHIRClient
Import library:

`from fhirpy import AsyncFHIRClient`

To create AsyncFHIRClient instance use:

`AsyncFHIRClient(url, authorization='', fhir_version='3.0.1', with_cache=False, extra_headers={})`

Returns an instance of the connection to the server which provides:
* .reference(resource_type, id, reference, **kwargs) - returns `AsyncFHIRReference` to the resource
* .resource(resource_type, **kwargs) - returns `AsyncFHIRResource` which described below
* .resources(resource_type) - returns `AsyncFHIRSearchSet`

## AsyncFHIRResource

provides:
* `async` .save() - creates or updates resource instance
* `async` .delete() - deletes resource instance
* `async` .to_reference(**kwargs) - returns `AsyncFHIRReference` for this resource

## AsyncFHIRReference

provides:
* `async` .to_resource(nocache=False) - returns `AsyncFHIRResource` for this reference

## AsyncFHIRReference

provides:
* .search(param=value)
* .limit(count)
* .page(page)
* .sort(*args)
* .elements(*args, exclude=False)
* .include(resource_type, attr)
* `async` .fetch() - makes query to the server and returns a list of `Resource`
* `async` .fetch_all() - makes query to the server and returns a full list of `Resource`
* `async` .first() - returns `Resource` or None
* `async` .get(id=id) - returns `Resource` or raises `ResourceNotFound`
* `async` .count() - makes query to the server and returns the total number of resources that match the SearchSet


# SyncFHIRClient
Import library:

`from fhirpy import SyncFHIRClient`

To create SyncFHIRClient instance use:

`SyncFHIRClient(url, authorization='', fhir_version='3.0.1', with_cache=False, extra_headers={})`


Returns an instance of the connection to the server which provides:
* .reference(resource_type, id, reference, **kwargs) - returns `SyncFHIRReference` to the resource
* .resource(resource_type, **kwargs) - returns `SyncFHIRResource` which described below
* .resources(resource_type) - returns `SyncFHIRSearchSet`

## SyncFHIRResource

provides:
* .save() - creates or updates resource instance
* .delete() - deletes resource instance
* .to_reference(**kwargs) - returns `SyncFHIRReference` for this resource

## SyncFHIRReference

provides:
* .to_resource(nocache=False) - returns `SyncFHIRResource` for this reference

## SyncFHIRSearchSet

provides:
* .search(param=value)
* .limit(count)
* .page(page)
* .sort(*args)
* .elements(*args, exclude=False)
* .include(resource_type, attr)
* .fetch() - makes query to the server and returns a list of `SyncFHIRResource`
* .fetch_all() - makes query to the server and returns a full list of `SyncFHIRResource`
* .first() - returns `SyncFHIRResource` or None
* .get(id=id) - returns `SyncFHIRResource` or raises `ResourceNotFound`
* .count() - makes query to the server and returns the total number of resources that match the SearchSet
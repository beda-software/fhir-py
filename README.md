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
|               | Sync                | Async                |
| ------------- | ------------------- | -------------------- |
| Client        | SyncFHIRClient      | AsyncFHIRClient      |
| SearchSet     | SyncFHIRSearchSet   | AsyncFHIRSearchSet   |
| Resource      | SyncFHIRResource    | AsyncFHIRResource    |
| Reference     | SyncFHIRReference   | AsyncFHIRReference   |


# API
Import library:

`from fhirpy import SyncFHIRClient`

or

`from fhirpy import AsyncFHIRClient`

To create FHIR instance use:

`SyncFHIRClient(url, authorization='', fhir_version='3.0.1', with_cache=False, extra_headers={})`

or

`AsyncFHIRClient(url, authorization='', fhir_version='3.0.1', with_cache=False, extra_headers={})`


Returns an instance of the connection to the server which provides:
* .reference(resource_type, id, reference, **kwargs) - returns `Reference` to the resource
* .resource(resource_type, **kwargs) - returns `Resource` which described below
* .resources(resource_type) - returns `SearchSet`

`SyncFHIRResource` / `AsyncFHIRResource`

provides:
* .save() - creates or updates resource instance
* .delete() - deletes resource instance
* .to_reference(**kwargs) - returns `Reference` for this resource

`SyncFHIRReference` / `AsyncFHIRReference`

provides:
* .to_resource(nocache=False) - returns `Resource` for this reference

`SyncFHIRSearchSet` / `AsyncFHIRReference`

provides:
* .search(param=value)
* .limit(count)
* .page(page)
* .sort(*args)
* .elements(*args, exclude=False)
* .include(resource_type, attr)
* .fetch() - makes query to the server and returns a list of `Resource`
* .fetch_all() - makes query to the server and returns a full list of `Resource`
* .first() - returns `Resource` or None
* .get(id=id) - returns `Resource` or raises `ResourceNotFound`

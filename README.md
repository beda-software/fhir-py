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
    patients = await resources.fetch()  # Returns list of AsyncFHIRResource

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

## Searchset examples
```Python
patients = client.resources('Patient')

patients.search(birthdate__gt='1944', birthdate__lt='1964')
# /Patient?birthdate=gt1944&birthdate=lt1964

patients.search(name__contains='John')
# /Patient?name:contains=John

patients.search(name=['John', 'Rivera'])
# /Patient?name=John&name=Rivera

patients.search(name='John,Eva')
# /Patient?name=John,Eva

patients.search(family__exact='Moore')
# /Patient?family:exact=Moore

patients.search(address_state='TX')
# /Patient?address-state=TX

patients.search(active=True, _id='id')
# /Patient?active=true&_id=id

patients.search(gender__not=['male', 'female'])
# /Patient?gender:not=male&gender:not=female
```

```Python
practitioner = client.resources('Practitioner').search(id='john-smith').first()
patients.search(general_practitioner=practitioner)
# /Patient?general-practitioner=Practitioner/john-smith
```

```Python
conditions = client.resources('Condition')

conditions.search(code__text='headache')
# /Condition?code:text=headache

conditions.search(code__in='http://acme.org/fhir/ValueSet/cardiac-conditions')
# /Condition?code:in=http://acme.org/fhir/ValueSet/cardiac-conditions

conditions.search(code__not_in='http://acme.org/fhir/ValueSet/cardiac-conditions')
# /Condition?code:not-in=http://acme.org/fhir/ValueSet/cardiac-conditions

conditions.search(code__below='126851005')
# /Condition?code:below=126851005

conditions.search(code__above='126851005')
# /Condition?code:above=126851005
```

```Python
import pytz
import datetime


patients.search(birthdate__lt=datetime.datetime.now(pytz.utc))
# /Patient?birthdate=lt2019-11-19T20:16:08Z

patients.search(birthdate__gt=datetime.datetime(2013, 10, 27, tzinfo=pytz.utc))
# /Patient?birthdate=gt2013-10-27T00:00:00Z
```

## Get exactly one resource
```Python
practitioners = client.resources('Practitioner')
patients = client.resources('Patient')

try:
    await practitioners.get(id='id')
except ResourceNotFound:
    pass
```

## Get first result
```Python
await practitioners.search(name='Jack').first()
# /Practitioner?name=Jack&_count=1

await patients.sort('active', '-birthdate').first()
# /Patient?_sort=active,-birthdate&_count=1
```

## Get total count
```Python
await practitioners.search(active=True).count()

await patients.count()
```

## Fetch one page
```Python
await practitioners.fetch()
# /Practitioner

await patients.elements('name', 'telecom').fetch()
# /Patient?_elements=resourceType,name,id,telecom
```

## Fetch all resources on all pages
```Python
await practitioners.search(address_city='Krasnoyarsk').fetch_all()

await patients.fetch_all()
```

## Page number (page)
```Python
# Get third page
await practitioners.limit(10).page(3).fetch()
# /Practitioner?_count=10&page=3
```

## Page count (_count)
```Python
# Get 100 resources
await practitioners.limit(100).fetch()
```

## Sort (_sort)
```Python
observations = client.resources('Observation')

observations.sort('status', '-date', 'category')
# /Observation?_sort=status,-date,category
```

## Elements (_elements)
```Python
# Get only specified set of elements for each resource
patients.elements('identifier', 'active', 'link')
# /Patient?_elements=identifier,active,link

# Get all elements except specified set
practitioners.elements('address', 'telecom', exclude=True)
```

## Include
```Python
await client.resources('EpisodeOfCare') \
    .include('EpisodeOfCare', 'patient').fetch_raw()
# /EpisodeOfCare?_include=EpisodeOfCare:patient

await client.resources('MedicationRequest') \
    .include('MedicationRequest', 'patient', target_resource_type='Patient') \
    .fetch_raw()
# /MedicationRequest?_include=MedicationRequest:patient:Patient
```

## Revinclude
```Python
await practitioners.revinclude('Group', 'member').fetch_raw()
# /Practitioner?_revinclude=Group:member
```

# Resource and helper methods

## Accessing resource attributes
```Python
patient = await client.resources('Patient').first()

# Work with the resource as a dictionary
patient_family = patient['name'][0]['family']

# Or access value by an attribute
patient_given_name = patient.name[0].given[0]
```

## get_by_path(path, default=None)
```Python
patient_postal = patient.get_by_path(['resource', 'address', 0, 'postalCode'])

# get_by_path can be also used on any nested attribute
patient_name = patient.name[0]
patient_fullname = '{} {}'.format(
    patient_name.get_by_path(['given', 0]),
    patient_name.get_by_path(['given', 0])
)

# Get identifier value by specified system or empty string
uid = patient.get_by_path([
        'resource', 'identifier',
        {'system':'http://example.com/identifier/uid'},
        'value'
    ], '')

# Get base value amount or 0
invoice = await client.resources('Invoice').first()
base_value = invoice.get_by_path([
    'totalPriceComponent',
    {'type': 'base'},
    'amount', 'value'], 0)
```

## serialize()
```Python
# Returns dict
patient.serialize()
```

# Reference

## Main class structure
Both async and sync clients have identical sets of classes and methods.

|               | Sync                | Async                |
| ------------- | ------------------- | -------------------- |
| Client        | SyncFHIRClient      | AsyncFHIRClient      |
| SearchSet     | SyncFHIRSearchSet   | AsyncFHIRSearchSet   |
| Resource      | SyncFHIRResource    | AsyncFHIRResource    |
| Reference     | SyncFHIRReference   | AsyncFHIRReference   |


## Acync client (based on _aiohttp_) – AsyncFHIRClient
Import library:

`from fhirpy import AsyncFHIRClient`

To create AsyncFHIRClient instance use:

`AsyncFHIRClient(url, authorization='', fhir_version='3.0.1', with_cache=False, extra_headers={})`

Returns an instance of the connection to the server which provides:
* .reference(resource_type, id, reference, **kwargs) - returns `AsyncFHIRReference` to the resource
* .resource(resource_type, **kwargs) - returns `AsyncFHIRResource` which described below
* .resources(resource_type) - returns `AsyncFHIRSearchSet`

### AsyncFHIRResource

provides:
* .serialize() - serializes resource
* .get_by_path(path, default=None) – gets the value at path of resource
* `async` .save() - creates or updates resource instance
* `async` .delete() - deletes resource instance
* `async` .to_reference(**kwargs) - returns `AsyncFHIRReference` for this resource

### AsyncFHIRReference

provides:
* `async` .to_resource(nocache=False) - returns `AsyncFHIRResource` for this reference

### AsyncFHIRSearchSet

provides:
* .search(param=value)
* .limit(count)
* .page(page)
* .sort(*args)
* .elements(*args, exclude=False)
* .include(resource_type, attr)
* .revinclude(resource_type, attr, recursive=False)
* .has(*args, **kwargs)
* `async` .fetch() - makes query to the server and returns a list of `Resource`
* `async` .fetch_all() - makes query to the server and returns a full list of `Resource`
* `async` .first() - returns `Resource` or None
* `async` .get(id=id) - returns `Resource` or raises `ResourceNotFound`
* `async` .count() - makes query to the server and returns the total number of resources that match the SearchSet


## Sync client (based on _requests_) – SyncFHIRClient
Import library:

`from fhirpy import SyncFHIRClient`

To create SyncFHIRClient instance use:

`SyncFHIRClient(url, authorization='', fhir_version='3.0.1', with_cache=False, extra_headers={})`


Returns an instance of the connection to the server which provides:
* .reference(resource_type, id, reference, **kwargs) - returns `SyncFHIRReference` to the resource
* .resource(resource_type, **kwargs) - returns `SyncFHIRResource` which described below
* .resources(resource_type) - returns `SyncFHIRSearchSet`

### SyncFHIRResource

The same as AsyncFHIRResource but with sync methods

### SyncFHIRReference

provides:
The same as AsyncFHIRReference but with sync methods

### SyncFHIRSearchSet

The same as AsyncFHIRSearchSet but with sync methods

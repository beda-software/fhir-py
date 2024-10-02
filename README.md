[![build status](https://github.com/beda-software/fhir-py/actions/workflows/build.yaml/badge.svg)](https://github.com/beda-software/fhir-py/actions/workflows/build.yaml)
[![codecov](https://codecov.io/gh/beda-software/fhir-py/branch/master/graph/badge.svg)](https://codecov.io/gh/beda-software/fhir-py)
[![pypi](https://img.shields.io/pypi/v/fhirpy.svg)](https://pypi.org/project/fhirpy)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![Supported Python version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/release/python-390/)

# fhir-py
async/sync FHIR client for python3.
This package provides an API for CRUD operations over FHIR resources

```pip install fhirpy```

or to install the latest dev version:

```pip install git+https://github.com/beda-software/fhir-py.git```

You can test this library by interactive FHIR course in the repository [Aidbox/jupyter-course](https://github.com/Aidbox/jupyter-course).

<!-- To regenerate table of contents: doctoc README.md --maxlevel=3 -->
<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Getting started](#getting-started)
  - [Async example](#async-example)
  - [Searchset examples](#searchset-examples)
    - [Chained parameters](#chained-parameters)
    - [Reference](#reference)
    - [Date](#date)
    - [Modifiers](#modifiers)
    - [Raw parameters](#raw-parameters)
  - [Get resource by id](#get-resource-by-id)
  - [Get exactly one resource](#get-exactly-one-resource)
  - [Get first result](#get-first-result)
  - [Get total count](#get-total-count)
  - [Fetch one page](#fetch-one-page)
  - [Fetch all resources on all pages](#fetch-all-resources-on-all-pages)
  - [Page count (_count)](#page-count-_count)
  - [Sort (_sort)](#sort-_sort)
  - [Elements (_elements)](#elements-_elements)
  - [Include](#include)
    - [Modifier :iterate (or :recurse in some previous versions of FHIR)](#modifier-iterate-or-recurse-in-some-previous-versions-of-fhir)
    - [Wild card (any search parameter of type=reference be included)](#wild-card-any-search-parameter-of-typereference-be-included)
  - [Revinclude](#revinclude)
    - [Wild card (any search parameter of type=reference be included)](#wild-card-any-search-parameter-of-typereference-be-included-1)
  - [Conditional operations](#conditional-operations)
    - [Conditional create](#conditional-create)
    - [Conditional update](#conditional-update)
    - [Conditional patch](#conditional-patch)
    - [Conditional delete](#conditional-delete)
- [Data models](#data-models)
  - [Static typechecking](#static-typechecking)
  - [Resource instantiation](#resource-instantiation)
  - [CRUD client methods](#crud-client-methods)
    - [Create](#create)
    - [Update](#update)
    - [Save](#save)
    - [Patch](#patch)
    - [Delete](#delete)
    - [Read](#read)
- [Resource and helper methods](#resource-and-helper-methods)
  - [Validate resource using operation $validate](#validate-resource-using-operation-validate)
  - [Accessing resource attributes](#accessing-resource-attributes)
  - [get_by_path(path, default=None)](#get_by_pathpath-defaultnone)
  - [set_by_path(obj, path, value)](#set_by_pathobj-path-value)
  - [serialize()](#serialize)
- [Reference](#reference-1)
  - [Main class structure](#main-class-structure)
  - [Async client (based on _aiohttp_) – AsyncFHIRClient](#async-client-based-on-_aiohttp_--asyncfhirclient)
    - [Aiohttp request parameters](#aiohttp-request-parameters)
    - [AsyncFHIRResource](#asyncfhirresource)
    - [AsyncFHIRReference](#asyncfhirreference)
    - [AsyncFHIRSearchSet](#asyncfhirsearchset)
  - [Sync client (based on _requests_) – SyncFHIRClient](#sync-client-based-on-_requests_--syncfhirclient)
    - [Requests request parameters](#requests-request-parameters)
    - [SyncFHIRResource](#syncfhirresource)
    - [SyncFHIRReference](#syncfhirreference)
    - [SyncFHIRSearchSet](#syncfhirsearchset)
- [Run integration tests](#run-integration-tests)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Getting started
## Async example
```Python
import asyncio
from fhirpy import AsyncFHIRClient


async def main():
    # Create an instance
    client = AsyncFHIRClient(
        'http://fhir-server/',
        authorization='Bearer TOKEN',
    )

    # Search for patients
    resources = client.resources('Patient')  # Return lazy search set
    resources = resources.search(name='John').limit(10).sort('name')
    patients = await resources.fetch()  # Returns list of AsyncFHIRResource

    # Create Organization resource
    organization = client.resource(
        'Organization',
        name='beda.software',
        active=False
    )
    await organization.save()

    # Update (PATCH) organization. Resource support accessing its elements
    # both as attribute and as a dictionary keys
    if organization['active'] is False:
        organization.active = True
    await organization.save(fields=['active'])
    # `await organization.patch(active=True)` would do the same PATCH operation

    # Get patient resource by reference and delete
    patient_ref = client.reference('Patient', 'new_patient')
    # Get resource from this reference
    # (throw ResourceNotFound if no resource was found)
    patient_res = await patient_ref.to_resource()
    await patient_res.delete()

    # Iterate over search set
    org_resources = client.resources('Organization')
    # Lazy loading resources page by page with page count = 100
    async for org_resource in org_resources.limit(100):
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

### Chained parameters
```Python
patients.search(general_practitioner__Organization__name='Hospital')
# /Patient?general-practitioner:Organization.name=Hospital
```

```Python
patients.search(general_practitioner__name='Hospital')
# /Patient?general-practitioner.name=Hospital
```

### Reference
```Python
practitioner = client.resources('Practitioner').search(_id='john-smith').first()
patients.search(general_practitioner=practitioner)
# /Patient?general-practitioner=Practitioner/john-smith
```

### Date
```Python
import pytz
import datetime


patients.search(birthdate__lt=datetime.datetime.now(pytz.utc))
# /Patient?birthdate=lt2019-11-19T20:16:08Z

patients.search(birthdate__gt=datetime.datetime(2013, 10, 27, tzinfo=pytz.utc))
# /Patient?birthdate=gt2013-10-27T00:00:00Z
```

### Modifiers
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

### Raw parameters
Sometimes you can find that fhir-py does not implement some search parameters from the FHIR specification. 
In this case, you can use `Raw()` wrapper without any transformations

```Python
from fhirpy.base.searchset import Raw

patients = client.resources('Patient')
patients.search(Raw(**{'general-practitioner.name': 'Hospital'}))
# /Patient?general-practitioner.name=Hospital
```

## Get resource by id
Use reference to get resource by id
```Python
patient = await client.reference('Patient', '1').to_resource()
# /Patient/1
```

Or use FHIR search API with `.first()` or `.get()` as described below.

## Get exactly one resource
```Python
practitioners = client.resources('Practitioner')

try:
    await practitioners.search(active=True, _id='id').get()
    # /Practitioner?active=true&_id=id
except ResourceNotFound:
    pass
except MultipleResourcesFound:
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
Keep in mind that this method as well as .fetch() doesn't return any included resources. Use fetch_raw() if you want to get all included resources.
```Python
# Returns a list of `Practitioner` resources
await practitioners.search(address_city='Krasnoyarsk').fetch_all()

await patients.fetch_all()
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
result = await client.resources('EpisodeOfCare') \
    .include('EpisodeOfCare', 'patient').fetch_raw()
# /EpisodeOfCare?_include=EpisodeOfCare:patient
for entry in result.entry:
    print(entry.resource)

await client.resources('MedicationRequest') \
    .include('MedicationRequest', 'patient', target_resource_type='Patient') \
    .fetch_raw()
# /MedicationRequest?_include=MedicationRequest:patient:Patient
```
### Modifier :iterate (or :recurse in some previous versions of FHIR)
```Python
# For FHIR version >= 3.5 we can also use modifier :iterate
await client.resources('MedicationRequest') \
    .include('MedicationDispense', 'prescription') \
    .include('MedicationRequest', 'performer', iterate=True) \
    .fetch_raw()
# /MedicationRequest?_include=MedicationDispense:prescription
#    &_include:iterate=MedicationRequest:performer

# For FHIR version 3.0-3.3 use modifier :recurse
await client.resources('MedicationDispense') \
    .include('MedicationRequest', 'prescriber', recursive=True) \
    .fetch_raw()
# /MedicationDispense?_include:recurse=MedicationRequest:prescriber
```
### Wild card (any search parameter of type=reference be included)
```Python
await client.resources('Encounter').include('*') \
    .fetch_raw()
# /Encounter?_include=*
```

## Revinclude
```Python
await practitioners.revinclude('Group', 'member').fetch_raw()
# /Practitioner?_revinclude=Group:member
```
or
```Python
await practitioners.include('Group', 'member', reverse=True).fetch_raw()
# /Practitioner?_revinclude=Group:member
```

### Wild card (any search parameter of type=reference be included)
```Python
await client.resources('EpisodeOfCare').revinclude('*') \
    .fetch_raw()
# /EpisodeOfCare?_revinclude=*
```

## Conditional operations
### Conditional create
[FHIR spec: Conditional create](https://build.fhir.org/http.html#ccreate)<br>
#### For resource
```Python
# resource.create(search_params)
# executes POST /Patient?identifier=fhirpy

patient = client.resource("Patient",
    identifier=[{"system": "http://example.com/env", "value": "fhirpy"}],
    name=[{"text": "Mr. Smith"}],
)
await patient.create(identifier="other")
```
#### For SearchSet
```Python
# searchset.get_or_create(resource)
# executes POST /Patient?identifier=fhirpy

patient, created = await client.resources("Patient").search(identifier="fhirpy").get_or_create(patient_to_save)

# no match -> created is True
# one match -> created is False, return existing resource
# multiple matches -> 412 'MultipleResourcesFound'
```
### Conditional update
[FHIR spec: Conditional update](https://build.fhir.org/http.html#cond-update)<br>
```Python
# resource, created: bool = searchset.patch(resource)
# executes PUT /Patient?identifier=fhirpy

patient_to_update = client.resource("Patient", 
                                    identifier=[{"system": "http://example.com/env", "value": "fhirpy"}],
                                    active=False)
new_patient, created = await client.resources("Patient").search(identifier="fhirpy").update(patient_to_update)

# no match -> created is True
# one match -> created is False, the matched resource is overwritten
# multiple matches -> 412 'MultipleResourcesFound'
```
### Conditional patch
[FHIR spec: Conditional patch](https://build.fhir.org/http.html#cond-patch)<br>
```Python
# patched_resource = searchset.patch(resource)
# executes PATCH /Patient?identifier=fhirpy

patient_to_patch = client.resource("Patient", 
                                    identifier=[{"system": "http://example.com/env", "value": "fhirpy"}], 
                                    name=[{"text": "Mr. Smith"}])
patched_patient = await client.resources("Patient").search(identifier="fhirpy").patch(patient_to_patch)

# no match -> 404 'ResourceNotFound'
# multiple matches -> 412 'MultipleResourcesFound'
```

### Conditional delete
[FHIR spec: Conditional delete](https://build.fhir.org/http.html#cdelete)<br>
```Python
response_data, status_code = await self.client.resources("Patient").search(identifier="abc").delete()

# no match -> status_code = 204 'No Content'
# one match -> status_code = 200 'OK'
# multiple matches -> status_code = 412 'MultipleResourcesFound' (implementation specific)
```

# Data models

Third party typing data models might be used along with fhir-py.
The typing data models should match [ResourceProtocol](https://github.com/beda-software/fhir-py/blob/master/fhirpy/base/resource_protocol.py#L5), e.g. have `resourceType` attribute, optional `id` and be iterable for serialization. 
There's a third party repository [fhir-py-types](https://github.com/beda-software/fhir-py-types) that is written on top of pydantic models is fully compatible with fhir-py.

## Static typechecking

fhir-py uses typehints in the codebase and it statically checked by [mypy](https://github.com/python/mypy). Some interfaces that are described below designed in the way to properly infer the return type based on the model class or instance.

## Resource instantiation

To instantiate a resource, simply use type model constructor, e.g.
```python
patient = Patient(name=[HumanName(text='Patient')])
```

## CRUD client methods

Client class provides CRUD methods that designed to work with typed models.

### Create

```python
await client.create(patient) # returns Patient
```

### Update

```python
await client.create(patient) # returns Patient
```

### Save

Smart helper that creates or updated the resource based on having `id`

```python
await client.save(patient) # returns Patient
```

Also it supports overriding specific fields using patch:

```python
await client.save(patient, fields=['identifier']) # returns Patient
```

### Patch

Patch accepts different syntaxes for patching, there're two syntaxes for general usage, without inferred types:

* Patch using reference defined by separate resource type and id:

```python
await client.patch('Patient', 'id', name=[HumanName(text='Patient')]) # returns Any
```

* Patch using reference string:

```python
await client.patch('Patient/id', name=[HumanName(text='Patient')]) # returns Any
```

And two types that infers type:


* Patch using model class and id


```python
await client.patch(Patient, 'id', name=[HumanName(text='Patient')]) # returns Patient
```

* Patch using model instance

```python
await client.patch(patient, name=[HumanName(text='Patient')]) # returns Patient
```

### Delete

Delete accepts different syntaxes for resource deletion, there're also syntaxes similar to patch, but without output type because delete usually returns nothing.

* Delete using reference defined by separate resource type and id:

```python
await client.delete('Patient', 'id') 
```

* Delete using reference string:

```python
await client.delete('Patient/id')
```


* Delete using model class and id


```python
await client.delete(Patient, 'id')
```

* Delete using model instance

```python
await client.delete(patient)
```

### Read

For fetching single resource by resourceType and id:

```python
ss = await client.get(Patient, 'id') # returns Patient
```

For fetching multiple resources, SearchSet needs to be instantiated using the model class as the first argument

```python
ss = client.resources(Patient) # returns AsyncFHIRSearchSet[Patient]
await ss.fetch_all() # returns list[Patient]
```

In that case search set infers model type for all methods that described above in the sections about search sets, including data fetching and conditional CRUD.


# Resource and helper methods

## Validate resource using operation $validate
```Python
try:
    await client.resource('Patient', birthDate='date', custom_prop='123', telecom=True) \
        .is_valid(raise_exception=True)
except OperationOutcome as e:
    print('Error: {}'.format(e))

patient = client.resource('Patient', birthDate='1998-01-01')
if (await patient.is_valid()):
    pass
```

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
    patient_name.get_by_path(['family'])
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

## set_by_path(obj, path, value)
```python
resource = {
    "name": [{"given": ["Firstname"], "family": "Lastname"}],
}

set_by_path(resource, ["name", 0, "given", 0], "FirstnameUpdated")

# resource
# {"name": [{"given": ["FirstnameUpdated"], "family": "Lastname"}]}
```

## serialize()
```Python
# Returns resources as dict
patient = await client.reference('Patient', '1').to_resource()
patient.serialize()
# Or 
await client.reference('Patient', '1').to_resource().serialize()
# {'resourceType': 'Patient', 'id': '1', 'meta': {'versionId': '1', 'lastUpdated': '2021-11-13T11:50:24.685719Z'}, ...}
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


## Async client (based on _aiohttp_) – AsyncFHIRClient
Import library:

`from fhirpy import AsyncFHIRClient`

To create AsyncFHIRClient instance use:

`AsyncFHIRClient(url, authorization='', extra_headers={})`

Returns an instance of the connection to the server which provides:
* .reference(resource_type, id, reference, **kwargs) - returns `AsyncFHIRReference` to the resource
* .resource(resource_type, **kwargs) - returns `AsyncFHIRResource` which described below
* .resources(resource_type) - returns `AsyncFHIRSearchSet`
* .resources(resource_class: T) - returns `AsyncFHIRSearchSet[T]`
* `async` .execute(path, method='post', data=None, params=None) - returns a result of FHIR operation

data model methods:
* `async` .get(resource_type: type[T], id) - returns T instance by resourceType/id
* `async` .get(resource_type: type[T], reference) - returns T instance by reference
* `async` .get(resource_type: str, id) - gets instance by resourceType/id
* `async` .get(reference: str) - gets instance by reference
* `async` .save(resource: T, fields=[]) - creates or updates or patches (with fields=[...]) T instance
* `async` .create(resource: T) - creates T instance
* `async` .update(resource: T) - updates T instance
* `async` .patch(resource: T, **kwargs) - patches T instance
* `async` .patch(resource_type: type[T], id, **kwargs) - patches instance by resourceType/id and returns T instance
* `async` .patch(resource_type: type[T], reference, **kwargs) - patches instance by reference and returns T instance
* `async` .patch(resource_type: str, id, **kwargs) - patches instance by resourceType/id 
* `async` .patch(reference: str, **kwargs) - patches instance by reference
* `async` .delete(resource: T) - deletes T instance
* `async` .delete(resource_type: type[T], id) - deletes resource by resourceType/id 
* `async` .delete(resource_type: type[T], reference) - deletes resource by reference
* `async` .delete(resource_type: str, id) - deletes instance by resourceType/id 
* `async` .delete(reference: str) - deletes instance by reference

### Aiohttp request parameters
Sometimes you need more control over the way http request is made and provide additional aiohttp [session's request](https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession.request) parameters like `ssl`, `proxy`, `cookies`, `timeout` etc. It's possible by providing `aiohttp_config` dict for `AsyncFHIRClient`:
```Python
client = AsyncFHIRClient(
    FHIR_SERVER_URL,
    aiohttp_config={
        "ssl": ssl.create_default_context(),
        "timeout": aiohttp.ClientTimeout(total=100),
    }
)
```

Be careful and don't override other request values like `params`, `json`, `data`, `auth`, because it'll interfere with the way `fhir-py` works and lead to an incorrect behavior. 

### AsyncFHIRResource

provides:
* .serialize() - serializes resource
* .get_by_path(path, default=None) – gets the value at path of resource
* `async` .save(fields=[]) - creates or updates or patches (with fields=[...]) resource instance
* `async` .create() - creates resource instance
* `async` .update() - updates resource instance
* `async` .patch(**kwargs) - patches resource instance
* `async` .delete() - deletes resource instance
* `async` .refresh() - reloads resource from a server
* `async` .to_reference(**kwargs) - returns `AsyncFHIRReference` for this resource
* `async` .execute(operation, method='post', data=None, params=None) - returns a result of FHIR operation on the resource

### AsyncFHIRReference

provides:
* `async` .to_resource() - returns `AsyncFHIRResource` for this reference
* `async` .execute(operation, method='post', data=None, params=None) - returns a result of FHIR operation on the resource
* `async` .patch(**kwargs) - patches resource instance
* `async` .delete() - deletes resource instance

### AsyncFHIRSearchSet

provides:
* .search(param=value)
* .limit(count)
* .sort(*args)
* .elements(*args, exclude=False)
* .include(resource_type, attr=None, recursive=False, iterate=False)
* .revinclude(resource_type, attr=None, recursive=False, iterate=False)
* .has(*args, **kwargs)
* `async` .fetch() - makes query to the server and returns a list of `Resource` filtered by resource type
* `async` .fetch_all() - makes query to the server and returns a full list of `Resource` filtered by resource type
* `async` .fetch_raw() - makes query to the server and returns a raw Bundle `Resource`
* `async` .first() - returns `Resource` or None
* `async` .get() - returns `Resource` or raises `ResourceNotFound` when no resource found or MultipleResourcesFound when more than one resource found (parameter 'id' is deprecated)
* `async` .count() - makes query to the server and returns the total number of resources that match the SearchSet
* `async` .get_or_create(resource) - conditional create
* `async` .update(resource) - conditional update
* `async` .patch(**kwargs) - conditional patch


## Sync client (based on _requests_) – SyncFHIRClient
Import library:

`from fhirpy import SyncFHIRClient`

To create SyncFHIRClient instance use:

`SyncFHIRClient(url, authorization='', extra_headers={})`


Returns an instance of the connection to the server which provides:
* .reference(resource_type, id, reference, **kwargs) - returns `SyncFHIRReference` to the resource
* .resource(resource_type, **kwargs) - returns `SyncFHIRResource` which described below
* .resources(resource_type) - returns `SyncFHIRSearchSet`

### Requests request parameters
Pass `requests_config` parameter to `SyncFHIRClient` if you want to provide additional parameters for a [request](https://docs.python-requests.org/en/latest/api/#requests.request) like `verify`, `cert`, `timeout` etc.
```Python
client = SyncFHIRClient(
    FHIR_SERVER_URL,
    requests_config={
        "verify": False,
        "allow_redirects": True,
        "timeout": 60,
    }
)
```

Be careful and don't override other request values like `params`, `json`, `data`, `headers`, which may interfere with the way `fhir-py` works and lead to an incorrect behavior. 

### SyncFHIRResource

The same as AsyncFHIRResource but with sync methods

### SyncFHIRReference

provides:
The same as AsyncFHIRReference but with sync methods

### SyncFHIRSearchSet

The same as AsyncFHIRSearchSet but with sync methods


# Run integration tests
(need some test FHIR server to run with, e.g. https://docs.aidbox.app/installation/setup-aidbox.dev)
1. Clone this repository:
`https://github.com/beda-software/fhir-py.git`

2. Go to fhir-py folder and install dev dependencies:
```
cd fhir-py
pip install -r requirements.txt
```

If you've already installed fhir-py library and want to test the last changes, reinstall it by running `python setup.py install` (or uninstall `pip uninstall fhirpy`)

3. Provide ENV variables `FHIR_SERVER_URL` and `FHIR_SERVER_AUTHORIZATION`, or edit tests/config.py

4. Run `pytest`

If you've found any bugs or think that some part of fhir-py is not compatible with FHIR spec, feel free to create an issue/pull request.

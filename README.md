[![Build Status](https://travis-ci.org/beda-software/fhir-py.svg?branch=master)](https://travis-ci.org/beda-software/fhir-py)
[![codecov](https://codecov.io/gh/beda-software/fhir-py/branch/master/graph/badge.svg)](https://codecov.io/gh/beda-software/fhir-py)
[![pypi](https://img.shields.io/pypi/v/fhirpy.svg)](https://pypi.python.org/pypi/fhirpy)

# fhir-py
FHIR client for python.
This package provides an API for CRUD operations over FHIR resources

# API
Import library:

`from fhirpy import FHIRClient`

To create FHIR instance use:

`FHIRClient(url, authorization='', version='3.0.1', without_cache=False)`

Returns an instance of the connection to the server which provides:
* .reference(resource_type, id, reference, **kwargs) - returns `FHIRReference` to the resource
* .resource(resource_type, **kwargs) - returns `FHIRResource` which described below
* .resources(resource_type) - returns `FHIRSearchSet`

`FHIRResource`

provides:
* .save() - creates or updates resource instance
* .delete() - deletes resource instance
* .to_reference(**kwargs) - returns  `FHIRReference` for this resource
* setattr/getattr using dot operator

`FHIRReference`

provides:
* .to_resource(nocache=False) - returns `FHIRResource` for this reference

`FHIRSearchSet`

provides:
* .search(param=value)
* .limit(count)
* .page(page)
* .sort(*args)
* .elements(*args, exclude=False)
* .include(resourceType, attr)
* .execute() - makes query to the server and returns a list of `FHIRResource`
* .first() - returns `FHIRResource` or None
* .get(id=id) - returns `FHIRResource` or raises `FHIRResourceNotFound`

# Usage

Create an instance
```python
ab = FHIRClient(url='http://path-to-fhir-server', authorization='Bearer TOKEN')
```

Fetch list of resource's instances
```python
resources = ab.resources('Patient')  # Return lazy search set
resources = resources.search(name='John').limit(10).page(2).sort('name')

resources.execute()  # Returns list of FHIRResource
```

Get the particular instance of resource
```python
res = ab.resources('Entity').get(id='ID')
```

Create new resource's instance
```python
res = ab.resource('Entity')
res.name = 'Chat'
res.save()  # Creates new instance

res.name = 'Chat2'
res.save()  # Updates the instance

res.delete()  # Deletes the instance
```

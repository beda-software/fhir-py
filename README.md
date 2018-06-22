[![Build Status](https://travis-ci.org/beda-software/aidbox-py.svg?branch=master)](https://travis-ci.org/beda-software/aidbox-py)
[![codecov](https://codecov.io/gh/beda-software/aidbox-py/branch/master/graph/badge.svg)](https://codecov.io/gh/beda-software/aidbox-py)
[![pypi](https://img.shields.io/pypi/v/aidbox.svg)](https://pypi.python.org/pypi/aidbox)

# aidbox-py
Aidbox client for python.
This package provides an API for CRUD operations over aidbox resources

# API

To obtain token by email and password use static method:
`Aidbox.obtain_token(host, email, password)`

To create Aidbox instance use:

`Aidbox(host, token)`

Returns an instance of the connection to the aidbox server which provides:
* .reference(resource_type, id, **kwargs) - returns `AidboxReference` to the resource
* .resource(resource_type, **kwargs) - returns `AidboxResource` which described below
* .resources(resource_type) - returns `AidboxSearchSet`

`AidboxResource`

provides:
* .save() - creates or updates resource instance
* .delete() - deletes resource instance
* .to_reference(**kwargs) - returns  `AidboxReference` for this resource
* setattr/getattr using dot operator

`AidboxReference`

provides:
* .to_resource() - returns `AidboxResource` for this reference

`AidboxSearchSet`

provides:
* .search(param=value)
* .limit(count)
* .page(page)
* .sort(*args)
* .execute() - makes query to the server and returns a list of `AidboxResource`
* .first() - returns `AidboxResource` or None
* .get(id=id) - returns `AidboxResource` or raises `AidboxResourceNotFound`

# Usage

Create an instance
```python
ab = Aidbox(host='host', token='token')
```

Fetch list of resource's instances
```python
resources = ab.resources('Patient')  # Return lazy search set
resources = resources.search(name='John').limit(10).page(2).sort('-id', 'name')

resources.execute()  # Returns list of AidboxResource
```

Get the particular instance of resource
```python
res = ab.resources('Entity').get(id=1)
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

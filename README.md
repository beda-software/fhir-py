[![Build Status](https://travis-ci.org/beda-software/aidbox-py.svg?branch=master)](https://travis-ci.org/beda-software/aidbox-py)
[![codecov](https://codecov.io/gh/beda-software/aidbox-py/branch/master/graph/badge.svg)](https://codecov.io/gh/beda-software/aidbox-py)
[![pypi](https://img.shields.io/pypi/v/aidbox.svg)](https://pypi.python.org/pypi/aidbox)

# aidbox-py
Aidbox client for python.
This package provides a low-level API for authorization and CRUD operations over aidbox resources

# API

To obtain token by email and password use static method:
`Aidbox.obtain_token(host, email, password)`

Create Aidbox instance:

`Aidbox(host, token)`

Returns an instance of the connection to aidbox server which allows:
* .reference(resource_type, id, **kwargs) - returns a reference to resource
* .resource(resource_type, **kwargs) - returns AidboxResource which described below
* .resources(resource_type) - returns SearchSet

`AidboxResource`
allows:
* .save() - creates or updates resource instance
* .delete() - deletes resource instance
* .reference(**kwargs) - returns reference to this resource
* setattr/getattr using dot operator


# Usage

Create an instance
```python
ab = Aidbox(host='host', token='token')
```

Fetch list of resource instances
```python
resources = ab.resources('Patient') # lazy search set (iterable)
resources.search(name='John').limit(10).page(2).sort('-id', 'name')

resources.first() # returns AidboxResource or None
resources.get() # returns AidboxResource or raises `AidboxResourceNotFound`
resources.execute() # returns list of AidboxResource
```

Get the particular instance of resource
```python
res = ab.resources('Entity').get(id=1)
res.save() # updates
```

Create new resource's instance
```python
res = ab.resource('Entity')
res.name = 'Chat'
res.save() # creates new resource


res = ab.resources('Entity').get(id=1)
res.delete() # deletes resource Entity with id=1
```

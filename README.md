# aidbox-py
Aidbox client for python.
This package provides a low-level API for authorization and CRUD operations over aidbox resources

# API

`Aidbox(host, login, password)`

Returns an instance of the connection to aidbox server which allows:
* .reference(resource_type, id, **kwargs) - returns a reference to resource
* .resource(resource_type, **kwargs) - returns AidboxResource which described below
* .resources(resource_type) - returns SearchSet

`AidboxResource(connection, resource_type, **kwargs)`

Returns an instance of an aidbox resource, which allows:
* .save() - creates or updates resource instance
* .delete() - deletes resource instance
* .reference(**kwargs) - returns reference to resource
* setattr/getattr using dot operator

# Usage

Create an instance
```python
ab = Aidbox(host=‘https://sansara.health-samurai.io', login=‘login’, password=‘password’)
```

Fetch list of resource instances
```python
resources = ab.resources(resource_type=‘Patient’) # lazy as query set (iterable)
resources.filter().limit(10).offset(10).order_by() # lazy (iterable)

resources.first() # not lazy
resources.get() # not lazy
```

Get the particular instance of resource
```python
res = ab.resource(resource_type=‘Entity’, id=1) # not lazy
res.save() # updates
```

Create new resource's instance
```python
res = ab.resource(resource_type=‘Entity’) # not lazy, fetches structure
res.save() # creates

res.delete()
```

Create new resource
```python
chat_res = ab.resource('Entity', id='chat')
title_attr = ab.resource(
    'Attribute',
    id='chat.title',
    name='title',
    path=['title'],
    resource=chat_res,
    type=ab.reference('Entity', id='string'))
last_subject = ab.resource(
    'Attribute',
    id='chat.subject',
    name='subject',
    path=['subject'],
    resource=chat_res,
    type=ab.reference('Entity', id='Reference'))
```

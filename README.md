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
ab = Aidbox(host='host', login='login', password='password', token='token')
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

Create new chat resource
```python
chat_res = ab.resource('Entity', id='Chat')
chat_res.save()
title_attr = ab.resource(
    'Attribute',
    id='chat.title',
    name='title',
    path=['title'],
    resource=chat_res,
    type=ab.reference('Entity', id='string'))
title_attr.save()
subject_attr = ab.resource(
    'Attribute',
    id='chat.subject',
    name='subject',
    path=['subject'],
    resource=chat_res,
    type=ab.reference('Entity', id='Reference'))
subject_attr.save()
```

Create instance of Chat
```python
chat = ab.resource('Chat')
chat.title = 'Chat title'
chat.subject = ab.reference('Patient', id='new-patient')
chat.save()
```

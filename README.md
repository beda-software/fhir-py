# aidbox-py
Aidbox client for python

# Usage

Create an instance
```
ab = AidBox(host=‘https://sansara.health-samurai.io', login=‘login’, password=‘password’)
```

Fetch list of resource instances
```
resources = ab.resources(resource_type=‘Patient’) # lazy as query set (iterable)
resources.filter().limit(10).offset(10).order_by() # lazy (iterable)

resources.first() # not lazy
resources.get() # not lazy
```

Get the particular instance of resource
```
res = ab.resource(resource_type=‘Entity’, id=1) # not lazy
res.save() # updates
```

Create new resource's instance
```
res = ab.resource(resource_type=‘Entity’) # not lazy, fetches structure
res.save() # creates

res.delete()
```

Create new resource
```
chat_res = ab.resource('Entity', id='chat')
title_attr = ab.resource('Attribute', id='chat.title', name='title', path=['title'], resource=chat_res, type=ab.resource('Entity', id='string'))
last_subject = ab.resource('Attribute', id='chat.subject', name='subject', path=['subject'], resource=type=ab.resource('Entity', id='Reference'))
```

# Example
```
res = ab.resource(resource_type=‘Patient’)
res.name = [{‘text’: ‘Name’}]
res.save()
```
=>
```
{‘name’: [{‘text’: ‘Name’}], ‘resourceType’: ‘Patient’}
```

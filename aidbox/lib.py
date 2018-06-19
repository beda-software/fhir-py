import requests


class Aidbox:
    def __init__(self, host, login, password):
        pass

    def resource(self, resource_type, **kwargs):
        result = AidboxResource(resource_type, **kwargs)
        return result


class AidboxResource:
    data = {}  # holds
    validation_schema = {}

    def __init__(self, aidbox, resource_type, **kwargs):
        # fetch schema and fill
        pass

    def __setattr__(self, key, value):
        pass  # set in data

    def __getattr__(self, item):
        pass  # get from data

    def save(self):
        # pass over data and when we see type(field) == AidboxResource, then
        # convert to dict with {'resource_type': '', 'id': ''}
        # then CamelCase it and post JSON to server
        pass

    def delete(self):
        pass


class AidboxReference:
    def __init__(self, resource_type, id, **kwargs):
        pass

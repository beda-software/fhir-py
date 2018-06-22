import json
import copy
import requests

from collections import defaultdict
from urllib.parse import parse_qsl

from .utils import (
    underscore, convert_keys_to_underscore, convert_keys_to_camelcase,
    convert_values, encode_params, select_keys)
from .exceptions import (
    AidboxResourceFieldDoesNotExist, AidboxResourceNotFound,
    AidboxAuthorizationError, AidboxOperationOutcome)


class ReferableMixin:
    def __eq__(self, other):
        return isinstance(other, (AidboxResource, AidboxReference)) \
               and self.id == other.id \
               and self.resource_type == other.resource_type


class Aidbox:
    schema = None

    @staticmethod
    def obtain_token(host, email, password):
        r = requests.post(
            '{0}/oauth2/authorize'.format(host),
            params={
                'client_id': 'sansara',
                'scope': 'openid profile email',
                'response_type': 'id_token',
            },
            data={'email': email, 'password': password},
            allow_redirects=False
        )
        if 'location' not in r.headers:
            raise AidboxAuthorizationError()

        # We don't fill production database with test tokens
        token_data = dict(parse_qsl(r.headers['location'])) # pragma: no cover
        return token_data['id_token'] # pragma: no cover

    def __init__(self, host, token):
        self.schema = {}
        self.host = host
        self.token = token

    def reference(self, resource_type=None, id=None, **kwargs):
        if resource_type is None or id is None:
            raise AttributeError('`resource_type` and `id` are required')
        return AidboxReference(self, resource_type, id, **kwargs)

    def resource(self, resource_type, **kwargs):
        kwargs['resource_type'] = resource_type
        return AidboxResource(self, **kwargs)

    def resources(self, resource_type):
        return AidboxSearchSet(self, resource_type=resource_type)

    def _do_request(self, method, path, data=None, params=None):
        url = '{0}/{1}?{2}'.format(
            self.host, path, encode_params(params))
        r = requests.request(
            method,
            url,
            json=convert_keys_to_camelcase(data),
            headers={'Authorization': 'Bearer {0}'.format(self.token)})

        if 200 <= r.status_code < 300:
            result = json.loads(r.text) if r.text else None
            return convert_values(
                convert_keys_to_underscore(result),
                lambda x: self.reference(**x)
                if AidboxReference.is_reference(x) else x)

        if r.status_code == 404:
            raise AidboxResourceNotFound(r.text)

        raise AidboxOperationOutcome(r.text)

    def _fetch_resource(self, path, params=None):
        return self._do_request('get', path, params=params)

    def _fetch_schema(self, resource_type):
        schema = self.schema.get(resource_type, None)
        if not schema:
            bundle = self._fetch_resource(
                'Attribute',
                params={'entity': resource_type}
            )
            attrs = [res['resource'] for res in bundle['entry']]
            schema = {underscore(attr['path'][0])
                      for attr in attrs} | {'id', 'resource_type'}
            self.schema[resource_type] = schema

        return schema

    def __str__(self):  # pragma: no cover
        return self.host

    def __repr__(self):  # pragma: no cover
        return self.__str__()


class AidboxSearchSet:
    aidbox = None
    resource_type = None
    params = None

    def __init__(self, aidbox, resource_type, params=None):
        self.aidbox = aidbox
        self.resource_type = resource_type
        self.params = defaultdict(list, params or {})

    def get(self, id):
        res = self.search(_id=id).first()
        if res:
            return res

        raise AidboxResourceNotFound()

    def execute(self):
        attrs = self.aidbox._fetch_schema(self.resource_type)

        res_data = self.aidbox._fetch_resource(self.resource_type, self.params)
        resource_data = [res['resource'] for res in res_data['entry']]
        return [
            AidboxResource(
                self.aidbox,
                **select_keys(data, attrs)
            )
            for data in resource_data
            if data.get('resource_type') == self.resource_type
        ]

    def count(self):
        new_params = copy.deepcopy(self.params)
        new_params['_count'] = 1
        new_params['_totalMethod'] = 'count'

        return self.aidbox._fetch_resource(
            self.resource_type,
            params=new_params
        )['total']

    def first(self):
        result = self.limit(1).execute()
        return result[0] if result else None

    def clone(self, **kwargs):
        new_params = copy.deepcopy(self.params)
        for key, value in kwargs.items():
            if isinstance(value, list):
                for item in value:
                    new_params[key].append(item)
            else:
                new_params[key].append(value)
        return AidboxSearchSet(self.aidbox, self.resource_type, new_params)

    def search(self, **kwargs):
        return self.clone(**kwargs)

    def limit(self, limit):
        return self.clone(_count=limit)

    def page(self, page):
        return self.clone(_page=page)

    def sort(self, *keys):
        sort_keys = ','.join(keys)
        return self.clone(_sort=sort_keys)

    def __str__(self):  # pragma: no cover
        return '<AidboxSearchSet {0}?{1}>'.format(
            self.resource_type, encode_params(self.params))

    def __repr__(self):  # pragma: no cover
        return self.__str__()

    def __iter__(self):
        return iter(self.execute())


class AidboxResource(ReferableMixin):
    aidbox = None
    resource_type = None
    _data = None
    _meta = None

    @property
    def root_attrs(self):
        return self.aidbox.schema[self.resource_type]

    def __init__(self, aidbox, **kwargs):
        self.aidbox = aidbox
        self.resource_type = kwargs.get('resource_type')
        self.aidbox._fetch_schema(self.resource_type)

        meta = kwargs.pop('meta', {})
        self._meta = meta
        self._data = {}

        for key, value in kwargs.items():
            setattr(self, key, value)

    def __setattr__(self, key, value):
        if key in dir(self):
            super(AidboxResource, self).__setattr__(key, value)
        elif key in self.root_attrs:
            self._data[key] = value
        else:
            raise AidboxResourceFieldDoesNotExist(
                'Invalid attribute `{0}` for resource `{1}`'.format(
                    key, self.resource_type))

    def __getattr__(self, key):
        if key in self.root_attrs:
            return self._data.get(key, None)
        else:
            raise AidboxResourceFieldDoesNotExist(
                'Invalid attribute `{0}` for resource `{1}`'.format(
                    key, self.resource_type))

    def get_path(self):
        if self.id:
            return '{0}/{1}'.format(self.resource_type, self.id)

        return self.resource_type

    def save(self):
        data = self.aidbox._do_request(
            'put' if self.id else 'post', self.get_path(), data=self.to_dict())

        self._meta = data.get('meta', {})
        self.id = data.get('id')

    def delete(self):
        return self.aidbox._do_request('delete', self.get_path())

    def to_reference(self, **kwargs):
        return AidboxReference(
            self.aidbox, self.resource_type, self.id, **kwargs)

    def to_dict(self):
        def convert_fn(item):
            if isinstance(item, AidboxResource):
                return item.to_reference().to_dict()
            elif isinstance(item, AidboxReference):
                return item.to_dict()
            else:
                return item

        data = {'resource_type': self.resource_type}
        data.update(self._data)

        return convert_values(data, convert_fn)

    def __str__(self):  # pragma: no cover
        return '<AidboxResource {0}>'.format(self.get_path())

    def __repr__(self):  # pragma: no cover
        return self.__str__()


class AidboxReference(ReferableMixin):
    aidbox = None
    resource_type = None
    id = None
    display = None

    def __init__(self, aidbox, resource_type, id, **kwargs):
        self.aidbox = aidbox
        self.resource_type = resource_type
        self.id = id
        self.display = kwargs.get('display', None)

    def __str__(self):  # pragma: no cover
        return '<AidboxReference {0}/{1}>'.format(self.resource_type, self.id)

    def __repr__(self):  # pragma: no cover
        return self.__str__()

    def to_resource(self):
        return self.aidbox.resources(self.resource_type).get(self.id)

    def to_dict(self):
        return {attr: getattr(self, attr) for attr in [
            'id', 'resource_type', 'display'
        ] if getattr(self, attr, None)}

    @staticmethod
    def is_reference(value):
        if not isinstance(value, dict):
            return False
        return 'id' in value and 'resource_type' in value and \
               not (set(value.keys()) - {'id', 'resource_type', 'display'})

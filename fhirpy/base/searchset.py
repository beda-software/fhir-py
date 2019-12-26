import copy
import datetime
from abc import ABC, abstractmethod
from collections import defaultdict

import pytz

from fhirpy.base.resource import BaseResource, BaseReference
from fhirpy.base.utils import chunks, encode_params

FHIR_DATE_TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
FHIR_DATE_FORMAT = '%Y-%m-%d'


def format_date_time(date: datetime.datetime):
    return pytz.utc.normalize(date).strftime(FHIR_DATE_TIME_FORMAT)


def format_date(date: datetime.date):
    return date.strftime(FHIR_DATE_FORMAT)


def transform_param(param: str):
    """
    >>> transform_param('general_practitioner')
    'general-practitioner'
    """
    if param[0] == '_' or param[0] == '.':
        # Don't correct _id, _has, _include, .effectiveDate and etc.
        return param

    return param.replace('_', '-')


def transform_value(value):
    """
    >>> transform_value(datetime.datetime(2019, 1, 1, tzinfo=pytz.utc))
    '2019-01-01T00:00:00Z'

    >>> transform_value(datetime.date(2019, 1, 1))
    '2019-01-01'

    >>> transform_value(True)
    'true'
    """
    if isinstance(value, datetime.datetime):
        return format_date_time(value)
    if isinstance(value, datetime.date):
        return format_date(value)
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (BaseReference, BaseResource)):
        return value.reference
    return value


class Raw:
    kwargs = {}

    def __init__(self, **kwargs):
        self.kwargs = kwargs


def SQ(*args, **kwargs):
    """
    Builds search query

    >>> dict(SQ(general_practitioner='prid'))
    {'general-practitioner': ['prid']}

    >>> dict(SQ(patient__Patient__name='John'))
    {'patient:Patient.name': ['John']}

    >>> dict(SQ(patient__Patient__birth_date__ge='2000'))
    {'patient:Patient.birth-date': ['ge2000']}

    >>> dict(SQ(patient__Patient__general_practitioner__Organization__name='Name'))
    {'patient:Patient.general-practitioner:Organization.name': ['Name']}

    >>> dict(SQ(period__ge='2018', period__lt='2019'))
    {'period': ['ge2018', 'lt2019']}

    >>> dict(SQ(text__contains='test'))
    {'text:contains': ['test']}

    >>> dict(SQ(url__not_in='http://loinc.org'))
    {'url:not-in': ['http://loinc.org']}

    >>> dict(SQ(name='family1,family2'))
    {'name': ['family1,family2']}

    >>> dict(SQ(status__not=['failed', 'completed']))
    {'status:not': ['failed', 'completed']}

    >>> dict(SQ(active=True))
    {'active': ['true']}

    >>> dict(SQ(**{'_has:Person:link:id': 'id'}))
    {'_has:Person:link:id': ['id']}

    >>> dict(SQ(**{'.effectiveDate.start$gt': '2019'}))
    {'.effectiveDate.start$gt': ['2019']}

    >>> dict(SQ(Raw(**{'_has:Person:link:id': 'id'})))
    {'_has:Person:link:id': ['id']}

    """
    res = defaultdict(list)
    for key, value in kwargs.items():
        value = value if isinstance(value, list) else [value]
        value = [transform_value(sub_value) for sub_value in value]

        key_parts = key.split('__')

        op = None
        if len(key_parts) % 2 == 0:
            # The operator is always the last part,
            # e.g., birth_date__ge or patient__Patient__birth_date__ge
            op = key_parts[-1]
            key_parts = key_parts[:-1]

        base_param, *chained_params = key_parts
        param_parts = [base_param]
        if chained_params:
            param_parts.extend([
                '.'.join(pair) for pair in chunks(chained_params, 2)])
        param = ':'.join(param_parts)

        if op:
            if op in ['contains', 'exact', 'missing', 'not',
                      'below', 'above', 'in', 'not_in', 'text', 'of_type']:
                param = '{0}:{1}'.format(param, transform_param(op))
            elif op in ['eq', 'ne', 'gt', 'ge', 'lt', 'le', 'sa', 'eb', 'ap']:
                value = ['{0}{1}'.format(op, sub_value) for sub_value in value]
        res[transform_param(param)].extend(value)

    for arg in args:
        if isinstance(arg, Raw):
            for key, value in arg.kwargs.items():
                value = value if isinstance(value, list) else [value]
                res[key].extend(value)
        else:
            raise ValueError('Can\'t handle args without Raw() wrapper')

    return res


class AbstractSearchSet(ABC):
    client = None
    resource_type = None
    params = None

    def __init__(self, client, resource_type, params=None):
        self.client = client
        self.resource_type = resource_type
        self.params = defaultdict(list, params or {})

    def _perform_resource(self, data):
        resource_type = data.get('resourceType', None)
        resource = self.client.resource(resource_type, **data)
        return resource

    @abstractmethod  # pragma: no cover
    def fetch(self):
        pass

    @abstractmethod  # pragma: no cover
    def fetch_raw(self):
        pass

    @abstractmethod  # pragma: no cover
    def fetch_all(self):
        pass

    @abstractmethod  # pragma: no cover
    def get(self, id):
        pass

    @abstractmethod  # pragma: no cover
    def count(self):
        pass

    @abstractmethod  # pragma: no cover
    def first(self):
        pass

    def clone(self, override=False, **kwargs):
        new_params = copy.deepcopy(self.params)
        for key, value in kwargs.items():
            if not isinstance(value, list):
                value = [value]

            if override:
                new_params[key] = value
            else:
                new_params[key].extend(value)

        return self.__class__(self.client, self.resource_type, new_params)

    def elements(self, *attrs, exclude=False):
        attrs = set(attrs)
        if not exclude:
            attrs |= {'id', 'resourceType'}
        attrs = [attr for attr in attrs]

        return self.clone(
            _elements='{0}{1}'.format('-' if exclude else '', ','.join(attrs)),
            override=True
        )

    def has(self, *args, **kwargs):
        if len(args) % 2 != 0:
            raise TypeError(
                'You should pass even size of arguments, for example: '
                '`.has(\'Observation\', \'patient\', '
                '\'AuditEvent\', \'entity\', user=\'id\')`'
            )

        key_part = ':'.join(
            ['_has:{0}'.format(':'.join(pair)) for pair in chunks(args, 2)]
        )

        return self.clone(
            **{
                ':'.join([key_part, key]): value
                for key, value in SQ(**kwargs).items()
            }
        )

    def include(
        self,
        resource_type,
        attr=None,
        target_resource_type=None,
        *,
        recursive=False,
        iterate=False,
        reverse=False
    ):
        key_params = ['_revinclude' if reverse else '_include']

        if iterate:
            # Added in FHIR v3.5
            key_params.append('iterate')
        if recursive:
            # Works for FHIR v3.0-3.3
            key_params.append('recursive')
        key = ':'.join(key_params)

        if resource_type == '*':
            value = '*'
        else:
            if not attr:
                raise TypeError(
                    'You should provide attr '
                    '(search parameter) argument'
                )
            value_params = [resource_type, attr]
            if target_resource_type:
                value_params.append(target_resource_type)
            value = ':'.join(value_params)

        return self.clone(**{key: value})

    def revinclude(
        self,
        resource_type,
        attr=None,
        target_resource_type=None,
        *,
        recursive=False,
        iterate=False
    ):
        return self.include(
            resource_type,
            attr=attr,
            target_resource_type=target_resource_type,
            recursive=recursive,
            iterate=iterate,
            reverse=True
        )

    def search(self, *args, **kwargs):
        return self.clone(**SQ(*args, **kwargs))

    def limit(self, limit):
        return self.clone(_count=limit, override=True)

    def page(self, page):
        return self.clone(page=page, override=True)

    def sort(self, *keys):
        sort_keys = ','.join(keys)
        return self.clone(_sort=sort_keys, override=True)

    def __str__(self):  # pragma: no cover
        return '<{0} {1}?{2}>'.format(
            self.__class__.__name__, self.resource_type,
            encode_params(self.params)
        )

    def __repr__(self):  # pragma: no cover
        return self.__str__()

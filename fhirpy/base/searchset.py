import copy
import datetime
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Generic, Self, Union

import pytz

from fhirpy.base.client import TClient
from fhirpy.base.exceptions import InvalidResponse
from fhirpy.base.resource import BaseReference, BaseResource
from fhirpy.base.resource_protocol import TResource, get_resource_type_from_class
from fhirpy.base.utils import chunks, encode_params

FHIR_DATE_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
FHIR_DATE_FORMAT = "%Y-%m-%d"


def format_date_time(date: datetime.datetime):
    return pytz.utc.normalize(date).strftime(FHIR_DATE_TIME_FORMAT)


def format_date(date: datetime.date):
    return date.strftime(FHIR_DATE_FORMAT)


def transform_param(param: str):
    """
    >>> transform_param('general_practitioner')
    'general-practitioner'
    """
    if param[0] == "_" or param[0] == ".":
        # Don't correct _id, _has, _include, .effectiveDate and etc.
        return param

    return param.replace("_", "-")


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
        return "true" if value else "false"
    if isinstance(value, (BaseReference, BaseResource)):
        return value.reference
    return value


class Raw:
    kwargs: dict

    def __init__(self, **kwargs):
        self.kwargs = kwargs


def SQ(*args, **kwargs):  # noqa: N802
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

    >>> dict(SQ(patient__Patient__general_practitioner__name='Name'))
    {'patient:Patient.general-practitioner.name': ['Name']}

    >>> dict(SQ(based_on__instantiates_canonical='PlanDefinition/id'))
    {'based-on.instantiates-canonical': ['PlanDefinition/id']}

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

    >>> dict(SQ(_lastUpdated__gt=2019))
    {'_lastUpdated': ['gt2019']}

    >>> dict(SQ(Raw(**{'_has:Person:link:id': 'id'})))
    {'_has:Person:link:id': ['id']}

    """
    param_ops = [
        "contains",
        "exact",
        "missing",
        "not",
        "below",
        "above",
        "in",
        "not_in",
        "text",
        "of_type",
    ]
    value_ops = ["eq", "ne", "gt", "ge", "lt", "le", "sa", "eb", "ap"]

    res = defaultdict(list)
    for key, value in kwargs.items():
        value = value if isinstance(value, list) else [value]  # noqa: PLW2901
        value = [transform_value(sub_value) for sub_value in value]  # noqa: PLW2901

        key_parts = key.split("__")

        op = None
        if key_parts[-1] in value_ops or key_parts[-1] in param_ops:
            # The operator is always the last part,
            # e.g., birth_date__ge or patient__Patient__birth_date__ge
            op = key_parts[-1]
            key_parts = key_parts[:-1]

        param = key_parts[0]
        for part in key_parts[1:]:
            # Resource type always starts with upper first letter
            is_resource_type = part[0].isupper()

            param += ":" if is_resource_type else "."
            param += part

        if op:
            if op in param_ops:
                param = f"{param}:{transform_param(op)}"
            elif op in value_ops:
                value = [f"{op}{sub_value}" for sub_value in value]  # noqa: PLW2901
        res[transform_param(param)].extend(value)

    for arg in args:
        if isinstance(arg, Raw):
            for key, value in arg.kwargs.items():
                value = value if isinstance(value, list) else [value]  # noqa: PLW2901
                res[key].extend(value)
        else:
            raise ValueError("Can't handle args without Raw() wrapper")

    return res


class AbstractSearchSet(Generic[TClient, TResource], ABC):
    client: TClient
    resource_type: str
    custom_resource_class: Union[type[TResource], None]
    params: dict

    def __init__(
        self,
        client: TClient,
        resource_type: Union[type[TResource], str],
        params: Union[dict, None] = None,
    ):
        self.client = client
        self.resource_type = (
            resource_type
            if isinstance(resource_type, str)
            else get_resource_type_from_class(resource_type)
        )
        self.custom_resource_class = None if isinstance(resource_type, str) else resource_type
        self.params = defaultdict(list, params or {})

    def _dict_to_resource(self, data) -> TResource:
        if self.custom_resource_class and self.resource_type == data["resourceType"]:
            return self.custom_resource_class(**data)
        return self.client.resource(data["resourceType"], **data)

    @abstractmethod
    def execute(
        self,
        path: str,
        method: str = "post",
        data: Union[dict, None] = None,
        params: Union[dict, None] = None,
    ):
        pass

    @abstractmethod
    def fetch(self):
        pass

    @abstractmethod
    def fetch_raw(self):
        pass

    @abstractmethod
    def fetch_all(self):
        pass

    @abstractmethod
    def get(self, id):  # noqa: A002
        pass

    @abstractmethod
    def count(self):
        pass

    @abstractmethod
    def first(self):
        pass

    @abstractmethod
    async def get_or_create(self, resource):
        pass

    @abstractmethod
    def update(self, resource):
        pass

    @abstractmethod
    def patch(self, _resource, **kwargs):
        pass

    def clone(self, override=False, **kwargs) -> Self:
        new_params = copy.deepcopy(self.params)
        for key, value in kwargs.items():
            if not isinstance(value, list):
                value = [value]  # noqa: PLW2901

            if override:
                new_params[key] = value
            else:
                new_params[key].extend(value)

        return self.__class__(
            self.client,
            self.custom_resource_class if self.custom_resource_class else self.resource_type,
            new_params,
        )

    def elements(self, *attrs, exclude=False) -> Self:
        attrs_set = set(attrs)
        if not exclude:
            attrs_set |= {"id", "resourceType"}
        attrs_list = list(attrs_set)

        return self.clone(
            _elements="{}{}".format("-" if exclude else "", ",".join(attrs_list)),
            override=True,
        )

    def has(self, *args, **kwargs) -> Self:
        if len(args) % 2 != 0:
            raise TypeError(
                "You should pass even size of arguments, for example: "
                "`.has('Observation', 'patient', "
                "'AuditEvent', 'entity', user='id')`"
            )

        key_part = ":".join(["_has:{}".format(":".join(pair)) for pair in chunks(args, 2)])

        return self.clone(
            **{":".join([key_part, key]): value for key, value in SQ(**kwargs).items()}
        )

    def include(  # noqa: PLR0913
        self,
        resource_type: str,
        attr: Union[str, None] = None,
        target_resource_type: Union[str, None] = None,
        *,
        recursive=False,
        iterate=False,
        reverse=False,
    ) -> Self:
        key_params = ["_revinclude" if reverse else "_include"]

        if iterate:
            # Added in FHIR v3.5
            key_params.append("iterate")
        if recursive:
            # Works for FHIR v3.0-3.3
            key_params.append("recursive")
        key = ":".join(key_params)

        if resource_type == "*":
            value = "*"
        else:
            if not attr:
                raise TypeError("You should provide attr (search parameter) argument")
            value_params = [resource_type, attr]
            if target_resource_type:
                value_params.append(target_resource_type)
            value = ":".join(value_params)

        return self.clone(**{key: value})

    def revinclude(
        self,
        resource_type: str,
        attr: Union[str, None] = None,
        target_resource_type: Union[str, None] = None,
        *,
        recursive=False,
        iterate=False,
    ) -> Self:
        return self.include(
            resource_type,
            attr=attr,
            target_resource_type=target_resource_type,
            recursive=recursive,
            iterate=iterate,
            reverse=True,
        )

    def search(self, *args, **kwargs) -> Self:
        return self.clone(**SQ(*args, **kwargs))

    def limit(self, limit) -> Self:
        return self.clone(_count=limit, override=True)

    def sort(self, *keys) -> Self:
        sort_keys = ",".join(keys)
        return self.clone(_sort=sort_keys, override=True)

    def __str__(self) -> str:
        return f"<{self.__class__.__name__} {self.resource_type}?{encode_params(self.params)}>"

    def __repr__(self) -> str:
        return self.__str__()

    def _get_bundle_resources(self, bundle_data) -> list[TResource]:
        bundle_resource_type = bundle_data.get("resourceType", None)

        if bundle_resource_type != "Bundle":
            raise InvalidResponse(f"Expected to receive Bundle but {bundle_resource_type} received")

        resources_data = [res["resource"] for res in bundle_data.get("entry", [])]

        resources = []
        for data in resources_data:
            resource = self._dict_to_resource(data)
            if resource.resourceType == self.resource_type:
                resources.append(resource)
        return resources

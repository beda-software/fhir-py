from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from typing import Any, Generic, Union

from fhirpy.base.client import TClient
from fhirpy.base.exceptions import ResourceNotFound
from fhirpy.base.resource_protocol import TReference, TResource, get_resource_path
from fhirpy.base.utils import convert_values, get_by_path, parse_path


class AbstractResource(Generic[TClient], dict, ABC):
    __client__: TClient

    def __init__(self, client: TClient, **kwargs):
        self.__client__ = client

        super().__init__(**kwargs)

    def __eq__(self, other):
        return isinstance(other, AbstractResource) and self.reference == other.reference

    def __setitem__(self, key, value):
        super().__setitem__(key, value)

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError as e:
            raise AttributeError from e

    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        reserved_keys = ["__client__"]
        if key in reserved_keys:
            super().__setattr__(key, value)
        else:
            self[key] = value

    def get_by_path(self, path, default=None):
        keys = parse_path(path)

        return get_by_path(self, keys, default)

    def get(self, key, default=None):
        return super().get(key, default)

    def setdefault(self, key, default=None):
        return super().setdefault(key, default)

    def serialize(self):
        return serialize(self)

    @property
    @abstractmethod
    def resource_type(self):
        pass

    @property
    @abstractmethod
    def id(self):
        pass

    @property
    @abstractmethod
    def reference(self):
        pass


class BaseResource(Generic[TClient, TResource, TReference], AbstractResource[TClient], ABC):
    def __init__(self, client: TClient, resource_type: str, **kwargs):
        def convert_fn(item):
            if isinstance(item, AbstractResource):
                return item, True

            if self.is_reference(item):
                return client.reference(**item), True

            return item, False

        converted_kwargs = convert_values(kwargs, convert_fn)
        super().__init__(
            client,
            **{
                **converted_kwargs,
                "resourceType": resource_type,
            },
        )

    def __str__(self) -> str:
        return f"<{self.__class__.__name__} {self._get_path()}>"

    def __repr__(self) -> str:
        return self.__str__()

    def __setitem__(self, key, value):
        if key == "resourceType" and key in self and value != self[key]:
            raise KeyError(
                "Can not change `resourceType` after instantiating resource. "
                "You must re-instantiate resource using "
                "`Client.resource` method"
            )

        super().__setitem__(key, value)

    @abstractmethod
    def save(self, fields=None, search_params=None):
        pass

    @abstractmethod
    def create(self, **kwargs):
        pass

    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def patch(self, **kwargs):
        pass

    @abstractmethod
    def delete(self):
        pass

    @abstractmethod
    def refresh(self):
        pass

    @abstractmethod
    def to_resource(self):
        pass

    def to_reference(self, **kwargs) -> TReference:
        """
        Returns Reference instance for this resource
        """
        if not self.reference:
            raise ResourceNotFound("Can not get reference to unsaved resource without id")

        return self.__client__.reference(reference=self.reference, **kwargs)

    @abstractmethod
    def is_reference(self, value):
        pass

    @abstractmethod
    def is_valid(self, raise_exception=False):
        pass

    @abstractmethod
    def execute(
        self,
        operation: str,
        method: str = "post",
        data: Union[dict, None] = None,
        params: Union[dict, None] = None,
    ) -> Any:
        pass

    @property
    def resource_type(self):
        return self["resourceType"]

    # mutable resourceType is needed to match ResourceProtocol
    @property
    def resourceType(self) -> str:  # noqa: N802
        return self["resourceType"]

    @resourceType.setter
    def resourceType(self, value: str):  # pragma: no cover # noqa: N802
        self["resourceType"] = value

    # mutable id is needed to match ResourceProtocol
    @property
    def id(self):
        return self.get("id", None)

    @id.setter
    def id(self, value):  # pragma: no cover
        self["id"] = value

    @property
    def reference(self):
        """
        Returns reference if local resource is saved
        """
        if self.id:
            return f"{self.resource_type}/{self.id}"

        return None

    def _get_path(self):
        return get_resource_path(self)


class BaseReference(Generic[TClient, TResource, TReference], AbstractResource[TClient], ABC):
    def __str__(self):
        return f"<{self.__class__.__name__} {self.reference}>"

    def __repr__(self):
        return self.__str__()

    @abstractmethod
    def to_resource(self):
        pass

    @abstractmethod
    def execute(
        self,
        operation,
        method=None,
        data: Union[dict, None] = None,
        params: Union[dict, None] = None,
    ):
        pass

    @abstractmethod
    def patch(self, **kwargs):
        pass

    @abstractmethod
    def delete(self):
        pass

    def to_reference(self, **kwargs) -> TReference:
        """
        Returns Reference instance for this reference
        """
        return self.__client__.reference(reference=self.reference, **kwargs)

    def _dict_to_resource(self, data):
        return self.__client__.resource(data["resourceType"], **data)

    @property
    @abstractmethod
    def reference(self):
        pass

    @property
    @abstractmethod
    def id(self):
        """
        Returns id if reference specifies to the local resource
        """

    @property
    @abstractmethod
    def is_local(self):
        pass


def serialize(resource: Any) -> dict:
    # TODO: make serialization pluggable

    def convert_fn(item):
        if isinstance(item, BaseResource):
            return serialize(item.to_reference()), True

        if isinstance(item, BaseReference):
            return serialize(item), True

        if _is_serializable_dict_like(item):
            # Handle dict-serializable structures like pydantic Model
            return dict(item), False

        return item, False

    return convert_values(dict(resource), convert_fn)


def _is_serializable_dict_like(item):
    """
    >>> _is_serializable_dict_like({})
    True
    >>> _is_serializable_dict_like([])
    False
    >>> _is_serializable_dict_like(())
    False
    >>> _is_serializable_dict_like(set())
    False
    >>> _is_serializable_dict_like("string")
    False
    >>> _is_serializable_dict_like(42)
    False
    >>> _is_serializable_dict_like(True)
    False
    >>> _is_serializable_dict_like(None)
    False
    """
    return isinstance(item, Iterable) and not isinstance(item, (Sequence, set))

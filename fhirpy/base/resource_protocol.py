from collections.abc import Iterator
from typing import Any, Protocol, TypeVar, Union, get_args, get_type_hints


class ResourceProtocol(Protocol):
    resourceType: Any  # noqa: N815
    id: Union[str, None]

    def __iter__(self) -> Iterator:
        ...


TResource = TypeVar("TResource", bound=ResourceProtocol)


def get_resource_type_from_class(cls: type[TResource]):
    try:
        return cls.resourceType
    except AttributeError:
        pass

    try:
        return get_args(get_type_hints(cls)["resourceType"])[0]
    except KeyError:
        pass

    raise NotImplementedError(
        f"Unsupported model {cls}. It should provide `resourceType` as class variable or as type annotation"
    )


def get_resource_path(resource: TResource) -> str:
    if resource.id:
        return f"{resource.resourceType}/{resource.id}"

    if resource.resourceType == "Bundle":
        return ""

    return resource.resourceType

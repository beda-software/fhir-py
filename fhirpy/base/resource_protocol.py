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
    except KeyError:  # pragma: no cover
        pass

    raise NotImplementedError(  # pragma: no cover
        f"Unsupported model {cls}. It should provide `resourceType` as class variable or as type annotation"
    )


def get_resource_path(resource: TResource) -> str:
    if resource.id:
        return f"{resource.resourceType}/{resource.id}"

    if resource.resourceType == "Bundle":
        return ""

    return resource.resourceType


def get_resource_type_id_and_class(
    resource_type_or_resource: Union[str, type[TResource], TResource],
    id: Union[str, None],  # noqa: A002
) -> tuple[str, Union[str, None], Union[type[TResource], None]]:
    if isinstance(resource_type_or_resource, str):
        resource_type = resource_type_or_resource
        resource_id = id
        custom_resource_class = None
    elif isinstance(resource_type_or_resource, type):
        resource_type = get_resource_type_from_class(resource_type_or_resource)
        resource_id = id
        custom_resource_class = resource_type_or_resource
    else:
        resource_type = resource_type_or_resource.resourceType
        resource_id = resource_type_or_resource.id
        custom_resource_class = resource_type_or_resource.__class__

    return (resource_type, resource_id, custom_resource_class)

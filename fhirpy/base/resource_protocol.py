from typing import Any, Protocol, TypeVar, Union, get_args, get_type_hints


class ResourceProtocol(Protocol):
    resourceType: Any  # noqa: N815
    id: Union[str, None]


TResource = TypeVar("TResource", bound=ResourceProtocol)
TReference = TypeVar("TReference")


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
    resource_type_or_resource_or_ref: Union[str, type[TResource], TResource],
    id_or_ref: Union[str, None],
) -> tuple[str, Union[str, None], Union[type[TResource], None]]:
    resource_id: Union[str, None]

    if isinstance(resource_type_or_resource_or_ref, str):
        if "/" in resource_type_or_resource_or_ref:
            resource_type, resource_id = resource_type_or_resource_or_ref.split("/", 2)
        else:
            resource_type = resource_type_or_resource_or_ref
            resource_id = _get_id_from_ref(id_or_ref) if id_or_ref else None
        custom_resource_class = None
    elif isinstance(resource_type_or_resource_or_ref, type):
        resource_type = get_resource_type_from_class(resource_type_or_resource_or_ref)
        resource_id = _get_id_from_ref(id_or_ref) if id_or_ref else None
        custom_resource_class = resource_type_or_resource_or_ref
    else:
        resource_type = resource_type_or_resource_or_ref.resourceType
        resource_id = resource_type_or_resource_or_ref.id
        custom_resource_class = resource_type_or_resource_or_ref.__class__

    if id_or_ref and "/" in id_or_ref:
        if _get_resource_type_from_ref(id_or_ref) != resource_type:
            raise TypeError(
                "Resource type mismatch, expected {resource_type} for reference {id_or_ref}"
            )

    return (resource_type, resource_id, custom_resource_class)


def _get_id_from_ref(ref: str) -> str:
    """
    >>> _get_id_from_ref("Patient/id")
    'id'
    """
    return ref.split("/")[-1]


def _get_resource_type_from_ref(ref: str) -> str:
    """
    >>> _get_resource_type_from_ref("Patient/id")
    'Patient'
    """
    return ref.split("/")[-2]

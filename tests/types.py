from typing import Literal, Union

from pydantic import BaseModel


class HumanName(BaseModel):
    text: str


class Identifier(BaseModel):
    system: str
    value: str


class Reference(BaseModel):
    reference: str


class Patient(BaseModel):
    resourceType: Literal["Patient"] = "Patient"  # noqa: N815
    id: Union[str, None] = None
    name: list[HumanName]
    identifier: list[Identifier]
    managingOrganization: Union[Reference, None] = None  # noqa: N815

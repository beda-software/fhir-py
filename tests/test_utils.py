from typing import Literal

from pydantic import BaseModel

from fhirpy.base.resource_protocol import get_resource_type_from_class


def test_get_resource_type_from_class_for_pydantic_model_value():
    class Patient(BaseModel):
        resourceType: Literal["Patient"] = "Patient"  # noqa: N815

    assert get_resource_type_from_class(Patient) == "Patient"


def test_get_resource_type_from_class_for_pydantic_model_annotation():
    class Patient(BaseModel):
        resourceType: Literal["Patient"]  # noqa: N815

    assert get_resource_type_from_class(Patient) == "Patient"

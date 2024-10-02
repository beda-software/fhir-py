from typing import Literal

import pytest
from pydantic import BaseModel

from fhirpy.base.resource_protocol import (
    get_resource_type_from_class,
    get_resource_type_id_and_class,
)
from fhirpy.base.utils import clean_empty_values, remove_nulls_from_dicts


def test_get_resource_type_from_class_for_pydantic_model_value():
    class PatientResource(BaseModel):
        resourceType: Literal["PatientResource"] = "PatientResource"  # noqa: N815

    assert get_resource_type_from_class(PatientResource) == "PatientResource"


def test_get_resource_type_from_class_for_pydantic_model_annotation():
    class PatientResource(BaseModel):
        resourceType: Literal["PatientResource"]  # noqa: N815

    assert get_resource_type_from_class(PatientResource) == "PatientResource"


class Patient(BaseModel):
    resourceType: Literal["Patient"] = "Patient"  # noqa: N815
    id: str


def test_get_resource_type_id_and_class_for_resource():
    patient = Patient(id="patient")

    assert get_resource_type_id_and_class(patient, None) == ("Patient", "patient", Patient)


def test_get_resource_type_id_and_class_for_resource_class_id_missing():
    assert get_resource_type_id_and_class(Patient, None) == ("Patient", None, Patient)


def test_get_resource_type_id_and_class_for_resource_class_with_id():
    assert get_resource_type_id_and_class(Patient, "patient") == ("Patient", "patient", Patient)


def test_get_resource_type_id_and_class_for_resource_class_with_ref():
    assert get_resource_type_id_and_class(Patient, "Patient/patient") == (
        "Patient",
        "patient",
        Patient,
    )


def test_get_resource_type_id_and_class_for_resource_class_with_ref_mismatch():
    with pytest.raises(TypeError):
        get_resource_type_id_and_class(Patient, "Practitioner/patient")


def test_get_resource_type_id_and_class_for_ref():
    assert get_resource_type_id_and_class("Patient/patient", None) == (
        "Patient",
        "patient",
        None,
    )


def test_remove_nulls_from_dicts():
    assert remove_nulls_from_dicts({}) == {}
    assert remove_nulls_from_dicts({"item": []}) == {"item": []}
    assert remove_nulls_from_dicts({"item": [None]}) == {"item": [None]}
    assert remove_nulls_from_dicts({"item": [None, {"item": None}]}) == {"item": [None, {}]}
    assert remove_nulls_from_dicts({"item": [None, {"item": None}, {}]}) == {"item": [None, {}, {}]}


def test_clean_empty_values():
    assert clean_empty_values({}) == {}
    assert clean_empty_values({"str": ""}) == {"str": ""}
    assert clean_empty_values({"nested": {"nested2": [{}]}}) == {"nested": {"nested2": [None]}}
    assert clean_empty_values({"nested": {"nested2": {}}}) == {}
    assert clean_empty_values({"item": []}) == {}
    assert clean_empty_values({"item": []}) == {}
    assert clean_empty_values({"item": [None]}) == {"item": [None]}
    assert clean_empty_values({"item": [None, {"item": None}]}) == {"item": [None, {"item": None}]}
    assert clean_empty_values({"item": [None, {"item": None}, {}]}) == {
        "item": [None, {"item": None}, None]
    }

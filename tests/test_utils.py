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


def test_serialize_preserves_empty_list_for_specified_fields():
    """serialize() must preserve empty lists/dicts when the key is in `fields`.

    Regression test for https://github.com/beda-software/fhir-py/issues/146:
    save(update_fields=["generalPractitioner"]) fails with KeyError when the
    field value is [] because clean_empty_values strips it.
    """
    from fhirpy.base.resource import serialize

    # Simulate a resource dict with an empty list field
    resource_data = {
        "resourceType": "Patient",
        "id": "test-123",
        "generalPractitioner": [],
        "name": [{"family": "Smith"}],
    }

    # Without fields: empty list is stripped (existing behavior)
    result_no_fields = serialize(resource_data)
    assert "generalPractitioner" not in result_no_fields
    assert result_no_fields["name"] == [{"family": "Smith"}]

    # With fields including the empty list: it must be preserved
    result_with_fields = serialize(resource_data, fields=["generalPractitioner"])
    assert "generalPractitioner" in result_with_fields
    assert result_with_fields["generalPractitioner"] == []

    # With fields NOT including the empty list: it should still be stripped
    result_other_field = serialize(resource_data, fields=["name"])
    assert "generalPractitioner" not in result_other_field
    assert result_other_field["name"] == [{"family": "Smith"}]


def test_serialize_preserves_empty_dict_for_specified_fields():
    """serialize() must also preserve empty dicts when in `fields`."""
    from fhirpy.base.resource import serialize

    resource_data = {
        "resourceType": "Patient",
        "id": "test-456",
        "contact": {},
        "active": True,
    }

    # Empty dict stripped without fields
    result_no_fields = serialize(resource_data)
    assert "contact" not in result_no_fields

    # Empty dict preserved when in fields
    result_with_fields = serialize(resource_data, fields=["contact"])
    assert "contact" in result_with_fields
    assert result_with_fields["contact"] == {}

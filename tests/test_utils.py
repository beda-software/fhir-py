from typing import Literal

import pytest
from pydantic import BaseModel

from fhirpy.base.resource_protocol import (
    get_resource_type_from_class,
    get_resource_type_id_and_class,
)
from fhirpy.base.utils import AttrDict, clean_empty_values, remove_nulls_from_dicts


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


def test_attrdict_dict_methods_win_over_same_named_keys():
    # https://github.com/beda-software/fhir-py/issues/110
    # AttrDict aliases self.__dict__ to itself for dot access, so a key
    # named e.g. "items" must not shadow the real dict method.
    data = AttrDict({"items": {"a": 1}, "keys": [1, 2], "nested": {"b": 2}})

    assert list(data.items()) == [("items", {"a": 1}), ("keys", [1, 2]), ("nested", {"b": 2})]
    assert list(data.keys()) == ["items", "keys", "nested"]
    assert list(data.values()) == [{"a": 1}, [1, 2], {"b": 2}]
    assert data.get("missing") is None

    # Key access and dot access for non-colliding names are unchanged
    assert data["items"] == {"a": 1}
    assert data["keys"] == [1, 2]
    assert data.nested == {"b": 2}


def test_serialize_resource_with_dict_method_named_keys():
    # https://github.com/beda-software/fhir-py/issues/110
    # serialize() crashed with `TypeError: 'AttrDict' object is not callable`
    # for resources containing keys named like dict methods.
    import json

    from fhirpy import SyncFHIRClient

    client = SyncFHIRClient("http://example.com/fhir")
    resource = client.resource("CustomResource", nested={"items": {"a": 1}})

    assert list(resource["nested"].items()) == [("items", {"a": 1})]
    assert list(resource.serialize().items()) == [
        ("nested", {"items": {"a": 1}}),
        ("resourceType", "CustomResource"),
    ]
    json.dumps(resource.serialize())

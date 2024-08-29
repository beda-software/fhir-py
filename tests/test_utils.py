from typing import Literal

from pydantic import BaseModel

from fhirpy.base.resource_protocol import get_resource_type_from_class
from fhirpy.base.utils import clean_empty_values, remove_nulls_from_dicts


def test_get_resource_type_from_class_for_pydantic_model_value():
    class Patient(BaseModel):
        resourceType: Literal["Patient"] = "Patient"  # noqa: N815

    assert get_resource_type_from_class(Patient) == "Patient"


def test_get_resource_type_from_class_for_pydantic_model_annotation():
    class Patient(BaseModel):
        resourceType: Literal["Patient"]  # noqa: N815

    assert get_resource_type_from_class(Patient) == "Patient"


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

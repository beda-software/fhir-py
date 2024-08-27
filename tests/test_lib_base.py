from typing import Union

import pytest

from fhirpy import AsyncFHIRClient, SyncFHIRClient
from fhirpy.base.resource import serialize
from fhirpy.base.utils import AttrDict, SearchList, parse_pagination_url, set_by_path
from fhirpy.lib import BaseFHIRReference

from .types import HumanName, Identifier, Patient


@pytest.mark.parametrize("client", [SyncFHIRClient("mock"), AsyncFHIRClient("mock")])
class TestLibBase:
    def test_to_reference_for_reference(self, client: Union[SyncFHIRClient, AsyncFHIRClient]):
        reference = client.reference("Patient", "p1")
        reference_copy = reference.to_reference(display="patient")
        assert isinstance(reference_copy, BaseFHIRReference)
        assert reference_copy.serialize() == {
            "reference": "Patient/p1",
            "display": "patient",
        }

    def test_serialize_with_dict_null_values(self, client: Union[SyncFHIRClient, AsyncFHIRClient]):
        patient = client.resource(
            "Patient",
            id="patient",
            managingOrganization=None,
        )
        assert patient.serialize() == {
            "resourceType": "Patient",
            "id": "patient",
        }

    def test_serialize(self, client: Union[SyncFHIRClient, AsyncFHIRClient]):
        practitioner1 = client.resource("Practitioner", id="pr1")
        practitioner2 = client.resource("Practitioner", id="pr2")
        patient = client.resource(
            "Patient",
            id="patient",
            generalPractitioner=[
                practitioner1.to_reference(display="practitioner"),
                practitioner2,
            ],
        )

        assert patient.serialize() == {
            "resourceType": "Patient",
            "id": "patient",
            "generalPractitioner": [
                {
                    "reference": "Practitioner/pr1",
                    "display": "practitioner",
                },
                {
                    "reference": "Practitioner/pr2",
                },
            ],
        }

    def test_equality(self, client: Union[SyncFHIRClient, AsyncFHIRClient]):
        resource = client.resource("Patient", id="p1")
        reference = client.reference("Patient", "p1")
        assert resource == reference

    def test_bundle_path(self, client: Union[SyncFHIRClient, AsyncFHIRClient]):
        bundle_resource = client.resource("Bundle")
        assert bundle_resource._get_path() == ""

    def test_resource_success(self, client: Union[SyncFHIRClient, AsyncFHIRClient]):
        resource = client.resource("Patient", id="p1")
        assert resource.resource_type == "Patient"
        assert resource["resourceType"] == "Patient"
        assert resource.id == "p1"
        assert resource["id"] == "p1"
        assert resource.reference == "Patient/p1"
        assert resource.serialize() == {
            "resourceType": "Patient",
            "id": "p1",
        }

    def test_reference_is_not_provided_failed(self, client: Union[SyncFHIRClient, AsyncFHIRClient]):
        with pytest.raises(TypeError):
            client.reference()

    def test_reference_from_local_reference(self, client: Union[SyncFHIRClient, AsyncFHIRClient]):
        reference = client.reference(reference="Patient/p1")
        assert reference.is_local is True
        assert reference.resource_type == "Patient"
        assert reference.id == "p1"
        assert reference.reference == "Patient/p1"
        assert reference["reference"] == "Patient/p1"
        assert reference.serialize() == {"reference": "Patient/p1"}

    def test_reference_from_external_reference(
        self, client: Union[SyncFHIRClient, AsyncFHIRClient]
    ):
        reference = client.reference(reference="http://external.com/Patient/p1")
        assert reference.is_local is False
        assert reference.resource_type is None
        assert reference.id is None
        assert reference.reference == "http://external.com/Patient/p1"
        assert reference["reference"] == "http://external.com/Patient/p1"
        assert reference.serialize() == {"reference": "http://external.com/Patient/p1"}

    def test_reference_from_resource_type_and_id(
        self, client: Union[SyncFHIRClient, AsyncFHIRClient]
    ):
        reference = client.reference("Patient", "p1")
        assert reference.resource_type == "Patient"
        assert reference.id == "p1"
        assert reference.reference == "Patient/p1"
        assert reference["reference"] == "Patient/p1"
        assert reference.serialize() == {"reference": "Patient/p1"}

    def test_get_by_path(self, client: Union[SyncFHIRClient, AsyncFHIRClient]):
        resource = client.resource(
            "Patient",
            **{
                "id": "patient",
                "name": [{"given": ["Firstname"], "family": "Lastname"}],
                "generalPractitioner": [
                    {
                        "reference": "Practitioner/pr1",
                        "display": "practitioner",
                    },
                    {
                        "reference": "Practitioner/pr2",
                    },
                ],
            },
        )
        assert (
            resource.get_by_path(
                ["generalPractitioner", {"reference": "Practitioner/pr1"}, "display"]
            )
            == "practitioner"
        )
        assert (
            resource.get_by_path(["generalPractitioner", {"reference": "Practitioner/100"}]) is None
        )
        assert (
            resource.get_by_path(
                ["generalPractitioner", {"reference": "Practitioner/pr2"}, "display"],
                "practitioner2",
            )
            == "practitioner2"
        )
        assert (
            resource.get_by_path(["generalPractitioner", 1, "reference"], "Practitioner/pr_test")
            == "Practitioner/pr2"
        )
        assert resource.get_by_path(["generalPractitioner", 2, "reference"]) is None
        names = resource.name
        assert isinstance(names, SearchList)
        assert names.get_by_path([0, "given", 0]) == "Firstname"
        name = names[0]
        assert isinstance(name, AttrDict)
        assert name.get_by_path(["given", 0]) == "Firstname"

    def test_set_by_path(self, client: Union[SyncFHIRClient, AsyncFHIRClient]):
        resource = {
            "name": [{"given": ["Firstname"], "family": "Lastname"}],
        }

        resource1 = resource.copy()
        set_by_path(resource1, ["name", 0, "given", 0], "FirstnameUpdated")
        assert resource1["name"][0]["given"][0] == "FirstnameUpdated"

        resource2 = resource.copy()
        with pytest.raises(IndexError):
            set_by_path(resource2, ["name", 1, "given", 0], "FirstnameUpdated")

        resource3 = resource.copy()
        set_by_path(resource3, ["name"], None)
        assert resource3["name"] is None

        resource4 = resource.copy()
        set_by_path(resource4, ["name", 0], {"text": "Firstname Lastname"})
        assert resource4["name"][0]["text"] == "Firstname Lastname"
        with pytest.raises(KeyError):
            assert resource4["name"][0]["given"]

    def test_set_resource_setdefault(self, client: Union[SyncFHIRClient, AsyncFHIRClient]):
        resource = client.resource("Patient", id="patient")
        resource.setdefault("id", "new_patient")
        assert resource.id == "patient"
        resource.setdefault("active", True)
        assert resource.active is True

    def test_set_resource_type_failed(self, client: Union[SyncFHIRClient, AsyncFHIRClient]):
        resource = client.resource("Patient")
        with pytest.raises(KeyError):
            resource["resourceType"] = "Practitioner"
        # It doesn't throw an exception because resourceType
        # is not changing actually
        resource["resourceType"] = "Patient"

    def test_reference_for_local_resource(self, client: Union[SyncFHIRClient, AsyncFHIRClient]):
        resource = client.resource("Patient")
        resource.id = "id"
        assert resource.reference == "Patient/id"

    def test_parse_pagination_url_absolute(self, client: Union[SyncFHIRClient, AsyncFHIRClient]):
        url = "https://github.com/beda-software/fhir-py/search?q=fhir-py&unscoped_q=fhir-py"
        path, params = parse_pagination_url(url)
        assert path == url
        assert params is None

    def test_parse_pagination_url_relative(self, client: Union[SyncFHIRClient, AsyncFHIRClient]):
        url = "/Patient?_count=100&name=ivan&name=petrov"
        path, params = parse_pagination_url(url)
        assert path == "/Patient"
        assert params == {"_count": ["100"], "name": ["ivan", "petrov"]}

    def test_accessing_property_as_attribute(self, client: Union[SyncFHIRClient, AsyncFHIRClient]):
        patient = client.resource(
            "Patient",
            **{
                "id": "patient",
                "name": [{"given": ["Firstname"], "family": "Lastname"}],
                "gender": "male",
            },
        )
        assert patient.gender == "male"
        assert patient.name[0].family == "Lastname"
        assert patient.name[0].given[0] == "Firstname"
        patient.gender = "female"
        assert patient["gender"] == "female"
        patient.name[0].family = "Jackson"
        assert patient["name"][0]["family"] == "Jackson"
        patient.name[0].given.append("Hellen")
        assert patient["name"][0]["given"] == ["Firstname", "Hellen"]

    def test_pluggable_type_model_resource_instantiation(
        self, client: Union[SyncFHIRClient, AsyncFHIRClient]
    ):
        patient = client.resource(
            Patient,
            **{
                "resourceType": "Patient",
                "id": "pid",
                "identifier": [{"system": "url", "value": "value"}],
                "name": [{"text": "Name"}],
            },
        )
        assert isinstance(patient, Patient)
        assert patient.resourceType == "Patient"
        assert patient.id == "pid"
        assert isinstance(patient.identifier[0], Identifier)
        assert patient.identifier[0].system == "url"
        assert patient.identifier[0].value == "value"
        assert isinstance(patient.name[0], HumanName)
        assert patient.name[0].text == "Name"

    def test_pluggable_type_model_serialize_with_dict_null_values(
        self, client: Union[SyncFHIRClient, AsyncFHIRClient]
    ):
        patient = client.resource(
            Patient,
            **{
                "resourceType": "Patient",
                "identifier": [{"system": "url", "value": "value"}],
                "name": [{"text": "Name"}],
                "managingOrganization": None,
            },
        )
        assert serialize(patient) == {
            "resourceType": "Patient",
            "identifier": [{"system": "url", "value": "value"}],
            "name": [{"text": "Name"}],
        }

    def test_resource_resource_type_setter(self, client: Union[SyncFHIRClient, AsyncFHIRClient]):
        patient = client.resource("Patient", id="p1")
        patient.resourceType = "Patient"

    def test_resource_id_setter(self, client: Union[SyncFHIRClient, AsyncFHIRClient]):
        patient = client.resource("Patient")
        patient.id = "p1"
        assert patient.id == "p1"

    def test_resource_str(self, client: Union[SyncFHIRClient, AsyncFHIRClient]):
        assert "FHIRResource Patient/p1" in str(client.resource("Patient", id="p1"))

    def test_reference_str(self, client: Union[SyncFHIRClient, AsyncFHIRClient]):
        assert "FHIRReference Patient/p1" in str(client.reference("Patient", "p1"))

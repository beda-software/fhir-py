import pytest
from fhirpy import SyncFHIRClient, AsyncFHIRClient
from fhirpy.lib import BaseFHIRReference
from fhirpy.base.utils import AttrDict, SearchList, parse_pagination_url


@pytest.mark.parametrize("client", [SyncFHIRClient("mock"), AsyncFHIRClient("mock")])
class TestLibBase(object):
    def test_to_reference_for_reference(self, client):
        reference = client.reference("Patient", "p1")
        reference_copy = reference.to_reference(display="patient")
        assert isinstance(reference_copy, BaseFHIRReference)
        assert reference_copy.serialize() == {
            "reference": "Patient/p1",
            "display": "patient",
        }

    def test_serialize(self, client):
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

    def test_equality(self, client):
        resource = client.resource("Patient", id="p1")
        reference = client.reference("Patient", "p1")
        assert resource == reference

    def test_bundle_path(self, client):
        bundle_resource = client.resource("Bundle")
        assert bundle_resource._get_path() == ""

    def test_resource_without_resource_type_failed(self, client):
        with pytest.raises(TypeError):
            client.resource()

    def test_resource_success(self, client):
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

    def test_reference_is_not_provided_failed(self, client):
        with pytest.raises(TypeError):
            client.reference()

    def test_reference_from_local_reference(self, client):
        reference = client.reference(reference="Patient/p1")
        assert reference.is_local is True
        assert reference.resource_type == "Patient"
        assert reference.id == "p1"
        assert reference.reference == "Patient/p1"
        assert reference["reference"] == "Patient/p1"
        assert reference.serialize() == {"reference": "Patient/p1"}

    def test_reference_from_external_reference(self, client):
        reference = client.reference(reference="http://external.com/Patient/p1")
        assert reference.is_local == False
        assert reference.resource_type is None
        assert reference.id is None
        assert reference.reference == "http://external.com/Patient/p1"
        assert reference["reference"] == "http://external.com/Patient/p1"
        assert reference.serialize() == {"reference": "http://external.com/Patient/p1"}

    def test_reference_from_resource_type_and_id(self, client):
        reference = client.reference("Patient", "p1")
        assert reference.resource_type == "Patient"
        assert reference.id == "p1"
        assert reference.reference == "Patient/p1"
        assert reference["reference"] == "Patient/p1"
        assert reference.serialize() == {"reference": "Patient/p1"}

    def test_get_by_path(self, client):
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
            }
        )
        assert (
            resource.get_by_path(
                ["generalPractitioner", {"reference": "Practitioner/pr1"}, "display"]
            )
            == "practitioner"
        )
        assert (
            resource.get_by_path(
                ["generalPractitioner", {"reference": "Practitioner/100"}]
            )
            is None
        )
        assert (
            resource.get_by_path(
                ["generalPractitioner", {"reference": "Practitioner/pr2"}, "display"],
                "practitioner2",
            )
            == "practitioner2"
        )
        assert (
            resource.get_by_path(
                ["generalPractitioner", 1, "reference"], "Practitioner/pr_test"
            )
            == "Practitioner/pr2"
        )
        assert resource.get_by_path(["generalPractitioner", 2, "reference"]) is None
        names = resource.name
        assert isinstance(names, SearchList)
        assert names.get_by_path([0, "given", 0]) == "Firstname"
        name = names[0]
        assert isinstance(name, AttrDict)
        assert name.get_by_path(["given", 0]) == "Firstname"

    def test_set_resource_setdefault(self, client):
        resource = client.resource("Patient", id="patient")
        resource.setdefault("id", "new_patient")
        assert resource.id == "patient"
        resource.setdefault("active", True)
        assert resource.active is True

    def test_set_resource_type_failed(self, client):
        resource = client.resource("Patient")
        with pytest.raises(KeyError):
            resource["resourceType"] = "Practitioner"
        # It doesn't throw an exception because resourceType
        # is not changing actually
        resource["resourceType"] = "Patient"

    def test_reference_for_local_resource(self, client):
        resource = client.resource("Patient")
        resource.id = "id"
        assert resource.reference == "Patient/id"

    def test_parse_pagination_url_absolute(self, client):
        url = "https://github.com/beda-software/fhir-py/search?q=fhir-py&unscoped_q=fhir-py"
        path, params = parse_pagination_url(url)
        assert path == url
        assert params is None

    def test_parse_pagination_url_relative(self, client):
        url = "/Patient?_count=100&name=ivan&name=petrov"
        path, params = parse_pagination_url(url)
        assert path == "/Patient"
        assert params == {"_count": ["100"], "name": ["ivan", "petrov"]}

    def test_accessing_property_as_attribute(self, client):
        patient = client.resource(
            "Patient",
            **{
                "id": "patient",
                "name": [{"given": ["Firstname"], "family": "Lastname"}],
                "gender": "male",
            }
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

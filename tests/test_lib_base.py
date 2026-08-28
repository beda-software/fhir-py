from typing import Union

import pytest

from fhirpy import AsyncFHIRClient, SyncFHIRClient
from fhirpy.base.utils import AttrDict, SearchList, parse_pagination_url, set_by_path
from fhirpy.lib import BaseFHIRReference

from .types import HumanName, Identifier, Patient
from .utils import dump_resource


@pytest.mark.parametrize(
    "client",
    [
        SyncFHIRClient("mock", dump_resource=dump_resource),
        AsyncFHIRClient("mock", dump_resource=dump_resource),
    ],
)
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

    def test_serialize_with_empty_array(self, client: Union[SyncFHIRClient, AsyncFHIRClient]):
        patient = client.resource("Patient", id="patient", generalPractitioner=[])
        assert patient.serialize() == {
            "resourceType": "Patient",
            "id": "patient",
        }

    def test_serialize_with_empty_dict(self, client: Union[SyncFHIRClient, AsyncFHIRClient]):
        patient = client.resource(
            "Patient",
            id="patient",
            name=[{"given": ["Name"], "_given": [{}], "text": "Name", "_text": {}}],
        )
        assert patient.serialize() == {
            "resourceType": "Patient",
            "id": "patient",
            "name": [{"given": ["Name"], "_given": [None], "text": "Name"}],
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


@pytest.mark.parametrize("client_class", [SyncFHIRClient, AsyncFHIRClient])
class TestBaseUrlAliases:
    def build_client(
        self, client_class, aliases: Union[list[str], None] = None
    ) -> Union[SyncFHIRClient, AsyncFHIRClient]:
        return client_class("http://devbox:80/fhir", url_aliases=aliases)

    def test_alias_is_rewritten_onto_base_url(self, client_class):
        client = self.build_client(client_class, ["https://myprod.com/fhir"])
        url = client._build_request_url("https://myprod.com/fhir/Patient?_count=100", None)
        assert url == "http://devbox:80/fhir/Patient?_count=100"

    def test_alias_without_path_is_rewritten_onto_base_url_path(self, client_class):
        client = self.build_client(client_class, ["https://myprod.com"])
        url = client._build_request_url("https://myprod.com/Patient", None)
        assert url == "http://devbox:80/fhir/Patient"

    def test_base_url_trailing_slash_is_insignificant(self, client_class):
        client = client_class("http://devbox:80/fhir/", url_aliases=["https://myprod.com/fhir"])
        url = client._build_request_url("https://myprod.com/fhir/Patient", None)
        assert url == "http://devbox:80/fhir/Patient"

    def test_alias_trailing_slash_is_insignificant(self, client_class):
        client = self.build_client(client_class, ["https://myprod.com/fhir/"])
        url = client._build_request_url("https://myprod.com/fhir/Patient", None)
        assert url == "http://devbox:80/fhir/Patient"

    def test_non_matching_alias_is_skipped(self, client_class):
        client = self.build_client(client_class, ["https://other.com", "https://myprod.com/fhir"])
        url = client._build_request_url("https://myprod.com/fhir/Patient", None)
        assert url == "http://devbox:80/fhir/Patient"

    def test_host_extending_alias_is_not_matched(self, client_class):
        client = self.build_client(client_class, ["https://myprod.com"])
        with pytest.raises(ValueError):  # noqa: PT011
            client._build_request_url("https://myprod.com.evil.com/Patient", None)

    def test_unknown_absolute_url_still_raises(self, client_class):
        client = self.build_client(client_class, ["https://myprod.com/fhir"])
        with pytest.raises(ValueError):  # noqa: PT011
            client._build_request_url("https://example.com/Patient", None)

    def test_scheme_must_match_alias(self, client_class):
        client = self.build_client(client_class, ["https://myprod.com/fhir"])
        with pytest.raises(ValueError):  # noqa: PT011
            client._build_request_url("http://myprod.com/fhir/Patient", None)

    def test_without_aliases_absolute_url_raises(self, client_class):
        client = self.build_client(client_class)
        with pytest.raises(ValueError):  # noqa: PT011
            client._build_request_url("https://myprod.com/fhir/Patient", None)

    def test_relative_path_is_unaffected_by_aliases(self, client_class):
        client = self.build_client(client_class, ["https://myprod.com/fhir"])
        url = client._build_request_url("/Patient", {"_count": 100})
        assert url == "http://devbox:80/fhir/Patient?_count=100"

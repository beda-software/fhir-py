import json
from typing import ClassVar
from unittest.mock import ANY, patch

import pytest
import responses

from fhirpy import SyncFHIRClient
from fhirpy.base.exceptions import (
    InvalidResponse,
    MultipleResourcesFound,
    OperationOutcome,
    ResourceNotFound,
)
from fhirpy.base.utils import AttrDict
from fhirpy.lib import SyncFHIRReference, SyncFHIRResource

from .config import FHIR_SERVER_AUTHORIZATION, FHIR_SERVER_URL
from .types import HumanName, Identifier, Patient, Reference
from .utils import MockRequestsResponse, dump_resource


class TestLibSyncCase:
    URL = FHIR_SERVER_URL
    client = None
    identifier: ClassVar = [{"system": "http://example.com/env", "value": "fhirpy"}]

    @classmethod
    def get_search_set(cls, resource_type):
        return cls.client.resources(resource_type).search(**{"identifier": "fhirpy"})

    @classmethod
    @pytest.fixture(autouse=True)
    def _clear_db(cls):
        for resource_type in ["Patient", "Practitioner"]:
            search_set = cls.get_search_set(resource_type)
            for item in search_set:
                item.delete()

    @classmethod
    def setup_class(cls):
        cls.client = SyncFHIRClient(
            cls.URL,
            authorization=FHIR_SERVER_AUTHORIZATION,
            extra_headers={"Access-Control-Allow-Origin": "*"},
            dump_resource=dump_resource,
        )

    def create_resource(self, resource_type, **kwargs):
        return self.client.resource(resource_type, identifier=self.identifier, **kwargs).create()

    def create_patient_model(self, **kwargs):
        patient = Patient(
            name=[HumanName(text="My patient")],
            identifier=[
                Identifier(
                    system=self.identifier[0]["system"],
                    value=self.identifier[0]["system"],
                )
            ],
            **kwargs,
        )
        return self.client.create(patient)

    def test_create_patient_model(self):
        patient = self.create_patient_model()

        fetched_patient = self.client.resources(Patient).search(_id=patient.id).first()

        assert fetched_patient.id == patient.id

    def test_client_create(self):
        patient = Patient(
            name=[HumanName(text="My patient")],
            identifier=[
                Identifier(
                    system=self.identifier[0]["system"],
                    value=self.identifier[0]["system"],
                )
            ],
        )
        created_patient = self.client.create(patient)

        assert isinstance(created_patient, Patient)
        assert created_patient.id is not None

    def test_client_update(self):
        patient = self.create_patient_model()
        patient.identifier = [
            *patient.identifier,
            Identifier(system="url", value="value"),
        ]

        updated_patient = self.client.update(patient)

        assert isinstance(updated_patient, Patient)
        assert updated_patient.id == patient.id
        assert len(updated_patient.identifier) == 2  # noqa: PLR2004

    def test_client_update_fails_without_id(self):
        patient = self.create_patient_model()
        patient.id = None

        with pytest.raises(TypeError):
            self.client.update(patient)

    def test_client_save_new(self):
        patient = Patient(
            name=[HumanName(text="My patient")],
            identifier=[
                Identifier(
                    system=self.identifier[0]["system"],
                    value=self.identifier[0]["system"],
                )
            ],
        )

        created_patient = self.client.save(patient)
        assert isinstance(created_patient, Patient)
        assert created_patient.id is not None

    def test_client_save_existing(self):
        patient = self.create_patient_model()
        patient.identifier = [
            *patient.identifier,
            Identifier(system="url", value="value"),
        ]

        updated_patient = self.client.save(patient)

        assert isinstance(updated_patient, Patient)
        assert updated_patient.id == patient.id
        assert len(updated_patient.identifier) == 2  # noqa: PLR2004

    def test_client_save_partial_update(self):
        patient = self.create_patient_model(
            managingOrganization=Reference(reference="urn:organization")
        )

        patient.identifier = [
            *patient.identifier,
            Identifier(system="url", value="value"),
        ]
        patient.name[0].text = "New patient"
        patient.managingOrganization = None

        updated_patient = self.client.save(patient, fields=["identifier", "managingOrganization"])

        assert isinstance(updated_patient, Patient)
        assert updated_patient.id == patient.id
        assert len(updated_patient.identifier) == 2  # noqa: PLR2004
        assert updated_patient.name[0].text == "My patient"
        assert updated_patient.managingOrganization is None

    def test_client_save_partial_update_fails_without_id(self):
        patient = self.create_patient_model()
        patient.id = None

        with pytest.raises(TypeError):
            self.client.save(patient, fields=["identifier"])

    def test_client_get_specifying_reference(self):
        patient = self.create_patient_model()

        fetched_patient = self.client.get(f"{patient.resourceType}/{patient.id}")

        assert isinstance(fetched_patient, dict)

    def test_client_get_specifying_resource_type_str_and_id(self):
        patient = self.create_patient_model()

        fetched_patient = self.client.get(patient.resourceType, patient.id)

        assert isinstance(fetched_patient, dict)

    def test_client_get_specifying_resource_type_type_and_id(self):
        patient = self.create_patient_model()

        fetched_patient = self.client.get(Patient, patient.id)

        assert isinstance(fetched_patient, Patient)

    def test_client_get_specifying_resource_type_type_and_ref(self):
        patient = self.create_patient_model()

        fetched_patient = self.client.get(Patient, f"Patient/{patient.id}")

        assert isinstance(fetched_patient, Patient)

    def test_client_get_specifying_resource_type_fails_without_id(self):
        patient = self.create_patient_model()

        with pytest.raises(TypeError):
            self.client.get(patient.resourceType)

    def test_client_patch_specifying_reference(self):
        patient = self.create_patient_model(
            managingOrganization=Reference(reference="urn:organization")
        )
        new_identifier = [*patient.identifier, Identifier(system="url", value="value")]

        patched_patient = self.client.patch(
            f"{patient.resourceType}/{patient.id}",
            identifier=[x.model_dump(exclude_none=True) for x in new_identifier],
            managingOrganization=None,
        )

        assert isinstance(patched_patient, dict)
        assert len(patched_patient["identifier"]) == 2  # noqa: PLR2004
        assert patched_patient["name"] == [{"text": "My patient"}]
        assert patched_patient.get("managingOrganization") is None
        assert patched_patient["id"] == patient.id

    def test_client_patch_specifying_resource_type_str_and_id(self):
        patient = self.create_patient_model()
        new_identifier = [*patient.identifier, Identifier(system="url", value="value")]

        patched_patient = self.client.patch(
            patient.resourceType,
            patient.id,
            identifier=[x.model_dump(exclude_none=True) for x in new_identifier],
        )

        assert isinstance(patched_patient, dict)
        assert len(patched_patient["identifier"]) == 2  # noqa: PLR2004

    def test_client_patch_specifying_resource_type_type_and_id(self):
        patient = self.create_patient_model()
        new_identifier = [*patient.identifier, Identifier(system="url", value="value")]

        patched_patient = self.client.patch(
            Patient,
            patient.id,
            identifier=[x.model_dump(exclude_none=True) for x in new_identifier],
        )

        assert isinstance(patched_patient, Patient)
        assert len(patched_patient.identifier) == 2  # noqa: PLR2004

    def test_client_patch_specifying_resource_type_type_and_ref(self):
        patient = self.create_patient_model()
        new_identifier = [*patient.identifier, Identifier(system="url", value="value")]

        patched_patient = self.client.patch(
            Patient,
            f"Patient/{patient.id}",
            identifier=[x.model_dump(exclude_none=True) for x in new_identifier],
        )

        assert isinstance(patched_patient, Patient)
        assert len(patched_patient.identifier) == 2  # noqa: PLR2004

    def test_client_patch_specifying_resource(self):
        patient = self.create_patient_model()
        new_identifier = [*patient.identifier, Identifier(system="url", value="value")]

        patched_patient = self.client.patch(
            patient, identifier=[x.model_dump(exclude_none=True) for x in new_identifier]
        )

        assert isinstance(patched_patient, Patient)
        assert len(patched_patient.identifier) == 2  # noqa: PLR2004

    def test_client_patch_specifying_resource_type_fails_without_id(self):
        patient = self.create_patient_model()

        with pytest.raises(TypeError):
            self.client.patch(patient.resourceType)

    def test_client_patch_specifying_resource_fails_without_id(self):
        patient = self.create_patient_model()
        patient.id = None

        with pytest.raises(TypeError):
            self.client.patch(patient)

    def test_client_delete_specifying_reference(self):
        patient = self.create_patient_model()

        self.client.delete(f"{patient.resourceType}/{patient.id}")

        fetched_patient = self.client.resources(Patient).search(_id=patient.id).first()
        assert fetched_patient is None

    def test_client_delete_specifying_resource_type_str_and_id(self):
        patient = self.create_patient_model()

        self.client.delete(patient.resourceType, patient.id)

        fetched_patient = self.client.resources(Patient).search(_id=patient.id).first()
        assert fetched_patient is None

    def test_client_delete_specifying_resource_type_type_and_id(self):
        patient = self.create_patient_model()

        self.client.delete(Patient, patient.id)

        fetched_patient = self.client.resources(Patient).search(_id=patient.id).first()
        assert fetched_patient is None

    def test_client_delete_specifying_resource_type_type_and_ref(self):
        patient = self.create_patient_model()

        self.client.delete(Patient, f"Patient/{patient.id}")

        fetched_patient = self.client.resources(Patient).search(_id=patient.id).first()
        assert fetched_patient is None

    def test_client_delete_specifying_resource(self):
        patient = self.create_patient_model()

        self.client.delete(patient)

        fetched_patient = self.client.resources(Patient).search(_id=patient.id).first()
        assert fetched_patient is None

    def test_client_delete_specifying_resource_type_fails_without_id(self):
        patient = self.create_patient_model()

        with pytest.raises(TypeError):
            self.client.delete(patient.resourceType)

    def test_client_delete_specifying_resource_fails_without_id(self):
        patient = self.create_patient_model()
        patient.id = None

        with pytest.raises(TypeError):
            self.client.delete(patient)

    def test_create_patient(self):
        self.create_resource("Patient", id="patient", name=[{"text": "My patient"}])

        patient = self.client.resources("Patient").search(_id="patient").get()
        assert patient["name"] == [{"text": "My patient"}]

    def test_conditional_create__create_on_no_match(self):
        self.create_resource("Patient", id="patient")

        patient = self.client.resource(
            "Patient",
            identifier=[{"system": "http://example.com/env", "value": "other"}, self.identifier[0]],
            name=[{"text": "Indiana Jones"}],
        )
        patient.create(identifier="other")

        assert patient.id != "patient"
        assert patient.get_by_path(["name", 0, "text"]) == "Indiana Jones"

    def test_conditional_create__skip_on_one_match(self):
        existing_patient = self.create_resource("Patient", id="patient")

        patient = self.client.resource(
            "Patient", identifier=self.identifier, name=[{"text": "Indiana Jones"}]
        )
        patient.create(identifier="fhirpy")

        assert patient.id == "patient"
        assert patient.get("name") is None
        assert patient.get_by_path(["meta", "versionId"]) == existing_patient.get_by_path(
            ["meta", "versionId"]
        )

    def test_conditional_create__fail_on_multiple_matches(self):
        self.create_resource("Patient", id="patient-one")
        self.create_resource("Patient", id="patient-two")

        with pytest.raises(MultipleResourcesFound):
            self.client.resource("Patient", identifier=self.identifier).create(identifier="fhirpy")

    def test_get_or_create__create_on_no_match(self):
        self.create_resource("Patient", id="patient")

        patient_to_save = self.client.resource(
            "Patient",
            identifier=[{"system": "http://example.com/env", "value": "other"}, self.identifier[0]],
            name=[{"text": "Indiana Jones"}],
        )
        patient, created = (
            self.client.resources("Patient")
            .search(identifier="other")
            .get_or_create(patient_to_save)
        )
        assert patient.id != "patient"
        assert patient.get_by_path(["name", 0, "text"]) == "Indiana Jones"
        assert created is True

    def test_get_or_create__skip_on_one_match(self):
        existing_patient = self.create_resource("Patient", id="patient")

        patient_to_save = self.client.resource("Patient", identifier=self.identifier)
        patient, created = (
            self.client.resources("Patient")
            .search(identifier="fhirpy")
            .get_or_create(patient_to_save)
        )
        assert patient.id == "patient"
        assert created is False
        assert patient.get_by_path(["meta", "versionId"]) == existing_patient.get_by_path(
            ["meta", "versionId"]
        )

    def test_conditional_operations__fail_on_multiple_matches(self):
        self.create_resource("Patient", id="patient-one")
        self.create_resource("Patient", id="patient-two")

        patient_to_save = self.client.resource("Patient", identifier=self.identifier)
        with pytest.raises(MultipleResourcesFound):
            self.client.resources("Patient").search(identifier="fhirpy").get_or_create(
                patient_to_save
            )
        with pytest.raises(MultipleResourcesFound):
            self.client.resources("Patient").search(identifier="fhirpy").update(patient_to_save)
        with pytest.raises(MultipleResourcesFound):
            self.client.resources("Patient").search(identifier="fhirpy").patch(patient_to_save)

    def test_conditional_update__no_match(self):
        patient = self.create_resource("Patient", id="patient", active=True)

        patient_to_update = self.client.resource(
            "Patient",
            identifier=[{"system": "http://example.com/env", "value": "other"}, self.identifier[0]],
            active=False,
        )
        new_patient, created = (
            self.client.resources("Patient").search(identifier="other").update(patient_to_update)
        )

        patient.refresh()
        assert patient.active is True
        assert new_patient.id != "patient"
        assert new_patient.active is False
        assert created is True

    def test_conditional_update__one_match(self):
        patient = self.create_resource("Patient", id="patient", active=True)

        patient_to_update = self.client.resource(
            "Patient", identifier=self.identifier, name=[{"text": "Indiana Jones"}]
        )
        updated_patient, created = (
            self.client.resources("Patient").search(identifier="fhirpy").update(patient_to_update)
        )
        assert updated_patient.id == patient.id
        assert created is False
        assert updated_patient.get_by_path(["meta", "versionId"]) != patient.get_by_path(
            ["meta", "versionId"]
        )
        assert updated_patient.get_by_path(["name", 0, "text"]) == "Indiana Jones"

        patient.refresh()
        assert updated_patient.get_by_path(["meta", "versionId"]) == patient.get_by_path(
            ["meta", "versionId"]
        )
        assert patient.get("active") is None

    def test_conditional_patch__no_match(self):
        patient_to_patch = self.client.resource(
            "Patient",
            identifier=[{"system": "http://example.com/env", "value": "other"}, self.identifier[0]],
            active=False,
        )
        with pytest.raises(ResourceNotFound):
            self.client.resources("Patient").search(identifier="other").patch(patient_to_patch)

    def test_conditional_patch__one_match(self):
        patient = self.create_resource(
            "Patient",
            id="patient",
            active=True,
            managingOrganization={"reference": "urn:organization"},
        )

        patched_patient = (
            self.client.resources("Patient")
            .search(identifier="fhirpy")
            .patch(
                identifier=self.identifier,
                name=[{"text": "Indiana Jones"}],
                managingOrganization=None,
            )
        )
        assert patched_patient.id == patient.id
        assert patched_patient.get_by_path(["meta", "versionId"]) != patient.get_by_path(
            ["meta", "versionId"]
        )
        assert patched_patient.get_by_path(["name", 0, "text"]) == "Indiana Jones"
        assert patched_patient.get("managingOrganization") is None

        patient.refresh()
        assert patched_patient.get_by_path(["meta", "versionId"]) == patient.get_by_path(
            ["meta", "versionId"]
        )
        assert patient.active is True
        assert patient.get("managingOrganization") is None

    def test_conditional_patch__one_match_deprecated(self):
        patient = self.create_resource("Patient", id="patient", active=True)

        patient_to_patch = self.client.resource(
            "Patient", identifier=self.identifier, name=[{"text": "Indiana Jones"}]
        )
        patched_patient = (
            self.client.resources("Patient").search(identifier="fhirpy").patch(patient_to_patch)
        )
        assert patched_patient.id == patient.id
        assert patched_patient.get_by_path(["meta", "versionId"]) != patient.get_by_path(
            ["meta", "versionId"]
        )
        assert patched_patient.get_by_path(["name", 0, "text"]) == "Indiana Jones"

        patient.refresh()
        assert patched_patient.get_by_path(["meta", "versionId"]) == patient.get_by_path(
            ["meta", "versionId"]
        )
        assert patient.active is True

    def test_update_patient(self):
        patient = self.create_resource("Patient", id="patient", name=[{"text": "My patient"}])
        patient["active"] = True
        patient.birthDate = "1945-01-12"
        patient.name[0].text = "SomeName"
        patient.save()

        check_patient = self.client.resources("Patient").search(_id="patient").get()
        assert check_patient.active is True
        assert check_patient["birthDate"] == "1945-01-12"
        assert check_patient.get_by_path(["name", 0, "text"]) == "SomeName"

    def test_count(self):
        search_set = self.get_search_set("Patient")

        assert search_set.count() == 0

        self.create_resource("Patient", id="patient1", name=[{"text": "John Smith FHIRPy"}])

        assert search_set.count() == 1

    def test_create_without_id(self):
        patient = self.create_resource("Patient")

        assert patient.id is not None

    def test_reference_delete(self):
        patient = self.create_resource("Patient", id="patient")

        patient.to_reference().delete()

        with pytest.raises(ResourceNotFound):
            self.get_search_set("Patient").search(_id="patient").get()

    def test_delete(self):
        patient = self.create_resource("Patient", id="patient")
        patient.delete()

        with pytest.raises(ResourceNotFound):
            self.get_search_set("Patient").search(_id="patient").get()

    def test_delete_without_id_failed(self):
        patient = self.client.resource("Patient", **{})

        with pytest.raises(TypeError):
            patient.delete()

    def test_conditional_delete__no_match(self):
        self.create_resource("Patient", id="patient")

        _, status_code = self.client.resources("Patient").search(identifier="other").delete()

        self.get_search_set("Patient").search(_id="patient").get()
        assert status_code == 204  # noqa: PLR2004

    def test_conditional_delete__one_match(self):
        patient = self.client.resource(
            "Patient",
            id="patient",
            identifier=[{"system": "http://example.com/env", "value": "other"}, self.identifier[0]],
        )
        patient.save()

        _, status_code = self.client.resources("Patient").search(identifier="other").delete()

        with pytest.raises(ResourceNotFound):
            self.get_search_set("Patient").search(_id="patient").get()
        assert status_code == 200  # noqa: PLR2004

    def test_conditional_delete__multiple_matches(self):
        self.create_resource("Patient", id="patient-1")
        self.create_resource("Patient", id="patient-2")

        with pytest.raises(MultipleResourcesFound):
            self.client.resources("Patient").search(identifier="fhirpy").delete()

    def test_get_not_existing_id(self):
        with pytest.raises(ResourceNotFound):
            self.client.resources("Patient").search(_id="FHIRPypy_not_existing_id").get()

    def test_get_more_than_one_resources(self):
        self.create_resource("Patient", birthDate="1901-05-25")
        self.create_resource("Patient", birthDate="1905-05-25")
        with pytest.raises(MultipleResourcesFound):
            self.client.resources("Patient").get()
        with pytest.raises(MultipleResourcesFound):
            self.client.resources("Patient").search(birthdate__gt="1900").get()

    def test_get_resource_by_id_is_deprecated(self):
        self.create_resource("Patient", id="patient", gender="male")
        with pytest.warns(DeprecationWarning):
            patient = self.client.resources("Patient").search(gender="male").get(id="patient")
        assert patient.id == "patient"

    def test_get_resource_by_search_with_id(self):
        self.create_resource("Patient", id="patient", gender="male")
        patient = self.client.resources("Patient").search(gender="male", _id="patient").get()
        assert patient.id == "patient"
        with pytest.raises(ResourceNotFound):
            self.client.resources("Patient").search(gender="female", _id="patient").get()

    def test_get_resource_by_search(self):
        self.create_resource("Patient", id="patient1", gender="male", birthDate="1901-05-25")
        self.create_resource("Patient", id="patient2", gender="female", birthDate="1905-05-25")
        patient_1 = (
            self.client.resources("Patient").search(gender="male", birthdate="1901-05-25").get()
        )
        assert patient_1.id == "patient1"
        patient_2 = (
            self.client.resources("Patient").search(gender="female", birthdate="1905-05-25").get()
        )
        assert patient_2.id == "patient2"

    def test_not_found_error(self):
        with pytest.raises(ResourceNotFound):
            self.client.resources("FHIRPyNotExistingResource").fetch()

    def test_operation_outcome_error(self):
        with pytest.raises(OperationOutcome):
            self.create_resource("Patient", name="invalid")

    def test_to_resource_for_local_reference(self):
        self.create_resource("Patient", id="p1", name=[{"text": "Name"}])

        patient_ref = self.client.reference("Patient", "p1")
        result = patient_ref.to_resource().serialize()
        result.pop("meta")
        result.pop("identifier")

        assert result == {
            "resourceType": "Patient",
            "id": "p1",
            "name": [{"text": "Name"}],
        }

    def test_to_resource_for_external_reference(self):
        reference = self.client.reference(reference="http://external.com/Patient/p1")

        with pytest.raises(ResourceNotFound):
            reference.to_resource()

    def test_to_resource_for_resource(self):
        resource = self.client.resource("Patient", id="p1", name=[{"text": "Name"}])
        resource_copy = resource.to_resource()
        assert isinstance(resource_copy, SyncFHIRResource)
        assert resource_copy.serialize() == {
            "resourceType": "Patient",
            "id": "p1",
            "name": [{"text": "Name"}],
        }

    def test_to_reference_for_resource_without_id(self):
        resource = self.client.resource("Patient")
        with pytest.raises(ResourceNotFound):
            resource.to_reference()

    def test_to_reference_for_resource(self):
        patient = self.create_resource("Patient", id="p1")

        assert patient.to_reference().serialize() == {"reference": "Patient/p1"}

        assert patient.to_reference(display="patient").serialize() == {
            "reference": "Patient/p1",
            "display": "patient",
        }

    def test_create_bundle(self):
        bundle = {
            "resourceType": "bundle",
            "type": "transaction",
            "entry": [
                {
                    "request": {"method": "POST", "url": "/Patient"},
                    "resource": {
                        "id": "bundle_patient_1",
                        "identifier": self.identifier,
                    },
                },
                {
                    "request": {"method": "POST", "url": "/Patient"},
                    "resource": {
                        "id": "bundle_patient_2",
                        "identifier": self.identifier,
                    },
                },
            ],
        }
        self.create_resource("Bundle", **bundle)
        self.client.resources("Patient").search(_id="bundle_patient_1").get()
        self.client.resources("Patient").search(_id="bundle_patient_2").get()

    def test_is_valid(self):
        resource = self.client.resource
        assert resource("Patient", id="id123").is_valid() is True
        assert resource("Patient", gender="female").is_valid(raise_exception=True) is True

        assert resource("Patient", gender=True).is_valid() is False
        with pytest.raises(OperationOutcome):
            resource("Patient", gender=True).is_valid(raise_exception=True)

        assert resource("Patient", gender="female", custom_prop="123").is_valid() is False
        with pytest.raises(OperationOutcome):
            resource("Patient", gender="female", custom_prop="123").is_valid(raise_exception=True)

        assert resource("Patient", gender="female", custom_prop="123").is_valid() is False

    def test_get_first(self):
        self.create_resource("Patient", id="patient_first", name=[{"text": "Abc"}])
        self.create_resource("Patient", id="patient_second", name=[{"text": "Bbc"}])
        patient = self.client.resources("Patient").sort("name").first()
        assert isinstance(patient, SyncFHIRResource)
        assert patient.id == "patient_first"

    def test_fetch_raw(self):
        self.create_resource("Patient", name=[{"text": "RareName"}])
        self.create_resource("Patient", name=[{"text": "RareName"}])
        bundle = self.client.resources("Patient").search(name="RareName").fetch_raw()
        assert bundle.resourceType == "Bundle"
        for entry in bundle.entry:
            assert isinstance(entry.resource, SyncFHIRResource)
        assert len(bundle.entry) == 2  # noqa: PLR2004

    def test_typed_fetch_raw(self):
        self.create_resource("Patient", name=[{"text": "RareName"}])
        self.create_resource("Patient", name=[{"text": "RareName"}])
        bundle = self.client.resources(Patient).search(name="RareName").fetch_raw()
        assert bundle.resourceType == "Bundle"
        for entry in bundle.entry:
            assert not isinstance(entry.resource, SyncFHIRResource)
        assert len(bundle.entry) == 2  # noqa: PLR2004

    def create_test_patients(self, count=10, name="Not Rare Name"):
        bundle = {
            "type": "transaction",
            "entry": [],
        }
        patient_ids = set()
        for i in range(count):
            p_id = f"patient-{i}"
            patient_ids.add(p_id)
            bundle["entry"].append(
                {
                    "request": {"method": "POST", "url": "/Patient"},
                    "resource": {
                        "id": p_id,
                        "name": [{"text": f"{name}{i}"}],
                        "identifier": self.identifier,
                    },
                }
            )
        self.create_resource("Bundle", **bundle)
        return patient_ids

    def test_fetch_all(self):
        patients_count = 18
        name = "Jack Johnson J"
        patient_ids = self.create_test_patients(patients_count, name)
        patient_set = self.client.resources("Patient").search(name=name).limit(5)

        patients = patient_set.fetch_all()

        received_ids = {p.id for p in patients}

        assert len(received_ids) == patients_count
        assert patient_ids == received_ids

    def test_for_iterator(self):
        patients_count = 22
        name = "Rob Robinson R"
        patient_ids = self.create_test_patients(patients_count, name)
        patient_set = self.client.resources("Patient").search(name=name).limit(3)

        received_ids = set()
        for patient in patient_set:
            received_ids.add(patient.id)

        assert len(received_ids) == patients_count
        assert patient_ids == received_ids

    @responses.activate
    def test_fetch_bundle_invalid_response_resource_type(self):
        patients = self.client.resources("Patient")
        responses.add(
            responses.GET,
            self.URL + "/Patient",
            json={"resourceType": "Patient"},
            status=200,
        )
        with pytest.raises(InvalidResponse):
            patients.fetch()

    @responses.activate
    def test_client_headers(self):
        patients = self.client.resources("Patient")
        responses.add(
            responses.GET,
            self.URL + "/Patient",
            json={"resourceType": "Bundle"},
            status=200,
        )
        patients.fetch()
        request_headers = responses.calls[0].request.headers
        assert request_headers["Access-Control-Allow-Origin"] == "*"

    def test_save_fields(self):
        patient = self.create_resource(
            "Patient",
            id="patient_to_update",
            gender="female",
            active=False,
            birthDate="1998-01-01",
            name=[{"text": "Abc"}],
            managingOrganization={"reference": "urn:organization"},
        )
        patient["gender"] = "male"
        patient["birthDate"] = "1998-02-02"
        patient["active"] = True
        patient["name"] = [{"text": "Bcd"}]
        patient["managingOrganization"] = None
        patient.save(fields=["gender", "birthDate", "managingOrganization"])

        patient_refreshed = patient.to_reference().to_resource()
        assert patient_refreshed["gender"] == patient["gender"]
        assert patient_refreshed["birthDate"] == patient["birthDate"]
        assert patient_refreshed["active"] is False
        assert patient_refreshed["name"] == [{"text": "Abc"}]
        assert patient_refreshed.get("managingOrganization") is None

    def test_update_patch_without_id(self):
        patient = self.client.resource(
            "Patient", identifier=self.identifier, name=[{"text": "J London"}]
        )
        new_name = [
            {
                "text": "Jack London",
                "family": "London",
                "given": ["Jack"],
            }
        ]
        with pytest.raises(TypeError):
            patient.update()
        with pytest.raises(TypeError):
            patient.patch(active=True, name=new_name)
        patient["name"] = new_name
        with pytest.raises(TypeError):
            patient.save(fields=["name"])
        patient.save()

    def test_update(self):
        patient_id = "patient_to_update"
        patient_initial = self.create_resource(
            "Patient", id=patient_id, name=[{"text": "J London"}], active=False
        )
        patient_updated = self.client.resource(
            "Patient", id=patient_id, identifier=self.identifier, active=True
        )
        patient_updated.update()

        patient_initial.refresh()

        assert patient_initial.id == patient_updated.id
        assert patient_updated.get("name") is None
        assert patient_initial.get("name") is None
        assert patient_initial["active"] is True

    def test_patch(self):
        patient_id = "patient_to_patch"
        patient_instance_1 = self.create_resource(
            "Patient",
            id=patient_id,
            name=[{"text": "J London"}],
            active=False,
            birthDate="1998-01-01",
            managingOrganization={"reference": "urn:organization"},
        )
        new_name = [
            {
                "text": "Jack London",
                "family": "London",
                "given": ["Jack"],
            }
        ]
        patient_instance_2 = self.client.resource("Patient", id=patient_id, birthDate="2001-01-01")
        patient_instance_2.patch(active=True, name=new_name, managingOrganization=None)
        patient_instance_1_refreshed = patient_instance_1.to_reference().to_resource()

        assert patient_instance_1_refreshed.serialize() == patient_instance_2.serialize()
        assert patient_instance_1_refreshed.active is True
        assert patient_instance_1_refreshed.birthDate == "1998-01-01"
        assert patient_instance_1_refreshed["name"] == new_name
        assert patient_instance_1_refreshed.get("managingOrganization") is None

    def test_reference_patch(self):
        patient = self.create_resource(
            "Patient",
            name=[{"text": "J London"}],
            active=False,
            birthDate="1998-01-01",
        )
        new_name = [
            {
                "text": "Jack London",
                "family": "London",
                "given": ["Jack"],
            }
        ]
        patient.patch(active=True, name=new_name)
        patient = patient.to_reference().to_resource()
        assert patient["active"] is True
        assert patient["name"] == new_name

    def test_refresh(self):
        patient_id = "refresh-patient-id"
        patient = self.create_resource("Patient", id=patient_id, active=True)

        test_patient = self.client.reference("Patient", patient_id).to_resource()
        test_patient.patch(gender="male", name=[{"text": "Jack London"}])
        assert patient.serialize() != test_patient.serialize()

        patient.refresh()
        assert patient.serialize() == test_patient.serialize()

    def test_client_execute_lastn(self):
        patient = self.create_resource("Patient", name=[{"text": "John First"}])
        observation = self.create_resource(
            "Observation",
            status="registered",
            subject=patient,
            category=[
                {
                    "coding": [
                        {
                            "code": "vital-signs",
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "display": "Vital Signs",
                        }
                    ]
                }
            ],
            code={"coding": [{"code": "10000-8", "system": "http://loinc.org"}]},
        )
        response = self.client.execute(
            "Observation/$lastn",
            method="get",
            params={"patient": f"Patient/{patient.id}", "category": "vital-signs"},
        )
        assert response["resourceType"] == "Bundle"
        assert response["total"] == 1
        assert response["entry"][0]["resource"]["id"] == observation["id"]

    def test_searchset_execute_lastn(self):
        patient = self.create_resource("Patient", name=[{"text": "John First"}])
        observation = self.create_resource(
            "Observation",
            status="registered",
            subject=patient,
            category=[
                {
                    "coding": [
                        {
                            "code": "vital-signs",
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "display": "Vital Signs",
                        }
                    ]
                }
            ],
            code={"coding": [{"code": "10000-8", "system": "http://loinc.org"}]},
        )
        response = self.client.resources("Observation").execute(
            "$lastn",
            method="get",
            params={"patient": f"Patient/{patient.id}", "category": "vital-signs"},
        )
        assert response["resourceType"] == "Bundle"
        assert response["total"] == 1
        assert response["entry"][0]["resource"]["id"] == observation["id"]

    def test_resource_execute_lastn(self):
        patient = self.create_resource("Patient", name=[{"text": "John First"}])
        observation = self.create_resource(
            "Observation",
            status="registered",
            subject=patient,
            category=[
                {
                    "coding": [
                        {
                            "code": "vital-signs",
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "display": "Vital Signs",
                        }
                    ]
                }
            ],
            code={"coding": [{"code": "10000-8", "system": "http://loinc.org"}]},
        )
        response = patient.execute(
            "Observation/$lastn", method="get", params={"category": "vital-signs"}
        )
        assert response["resourceType"] == "Bundle"
        assert response["total"] == 1
        assert response["entry"][0]["resource"]["id"] == observation["id"]

    def test_client_execute_history(self):
        patient = self.create_resource("Patient", name=[{"text": "John First"}])
        response = self.client.execute(f"Patient/{patient.id}/_history", "get")
        assert response["resourceType"] == "Bundle"
        assert response["type"] == "history"
        assert "entry" in response

    def test_resource_execute_history(self):
        patient = self.create_resource("Patient", name=[{"text": "John First"}])
        response = patient.execute("_history", "get")
        assert response["resourceType"] == "Bundle"
        assert response["type"] == "history"
        assert response["total"] == 1
        assert "entry" in response

    def test_reference_execute_history(self):
        patient = self.create_resource("Patient", name=[{"text": "John First"}])
        patient_ref = patient.to_reference()
        response = patient_ref.execute("_history", "get")
        assert response["resourceType"] == "Bundle"
        assert response["type"] == "history"
        assert response["total"] == 1
        assert "entry" in response

    def test_reference_execute_history_not_local(self):
        patient_ref = self.client.reference(reference="http://external.com/Patient/p1")
        with pytest.raises(ResourceNotFound):
            patient_ref.execute("_history", "get")

    def test_references_after_save(self):
        patient = self.create_resource("Patient", name=[{"text": "John First"}])
        practitioner = self.create_resource("Practitioner", name=[{"text": "Jack"}])
        appointment = self.client.resource(
            "Appointment",
            **{
                "status": "booked",
                "participant": [
                    {"actor": patient, "status": "accepted"},
                    {"actor": practitioner, "status": "accepted"},
                ],
            },
        )
        appointment.save()
        assert isinstance(appointment.participant[0].actor, SyncFHIRReference)
        assert isinstance(appointment.participant[0], AttrDict)
        test_patient = appointment.participant[0].actor.to_resource()
        assert test_patient

        assert isinstance(appointment.participant[1].actor, SyncFHIRReference)
        assert isinstance(appointment.participant[1], AttrDict)
        test_practitioner = appointment.participant[1].actor.to_resource()
        assert test_practitioner

    def test_references_in_resource(self):
        patient = self.create_resource("Patient", name=[{"text": "John First"}])
        practitioner = self.create_resource("Practitioner", name=[{"text": "Jack"}])
        appointment = self.client.resource(
            "Appointment",
            **{
                "status": "booked",
                "participant": [
                    {"actor": patient, "status": "accepted"},
                    {"actor": practitioner, "status": "accepted"},
                ],
            },
        )
        appointment.save()
        test_appointment = self.client.resources("Appointment").search(_id=appointment.id).get()

        assert isinstance(test_appointment.participant[0].actor, SyncFHIRReference)
        assert isinstance(test_appointment.participant[0], AttrDict)
        test_patient = test_appointment.participant[0].actor.to_resource()
        assert test_patient

        assert isinstance(test_appointment.participant[1].actor, SyncFHIRReference)
        assert isinstance(test_appointment.participant[1], AttrDict)
        test_practitioner = test_appointment.participant[1].actor.to_resource()
        assert test_practitioner

    def test_types_fetch_all(self):
        patients_count = 18
        name = "Jack Johnson J"
        patient_ids = self.create_test_patients(patients_count, name)
        patient_set = self.client.resources(Patient).search(name=name).limit(5)

        patients = patient_set.fetch_all()

        received_ids = {p.id for p in patients}
        assert len(received_ids) == patients_count
        assert patient_ids == received_ids
        assert isinstance(patients[0], Patient)

    def test_typed_fetch(self):
        patients_count = 18
        limit = 5
        name = "Jack Johnson J"
        self.create_test_patients(patients_count, name)
        patient_set = self.client.resources(Patient).search(name=name).limit(limit)

        patients = patient_set.fetch()

        received_ids = {p.id for p in patients}
        assert len(received_ids) == limit
        assert isinstance(patients[0], Patient)

    def test_typed_get(self):
        name = "Jack Johnson J"
        self.create_test_patients(1, name)
        patient_set = self.client.resources(Patient).search(name=name)

        patient = patient_set.get()

        assert isinstance(patient, Patient)

    def test_typed_first(self):
        name = "Jack Johnson J"
        self.create_test_patients(1, name)
        patient_set = self.client.resources(Patient).search(name=name)

        patient = patient_set.first()

        assert isinstance(patient, Patient)

    def test_typed_get_or_create(self):
        name = "Jack Johnson J"
        self.create_test_patients(1, name)
        new_patient = Patient(
            name=[HumanName(text=name)],
            identifier=[Identifier(system="url", value="value"), Identifier(**self.identifier[0])],
        )

        patient, created = (
            self.client.resources(Patient).search(name=name).get_or_create(new_patient)
        )

        assert created is False
        assert isinstance(patient, Patient)
        assert patient.identifier[0].system == self.identifier[0]["system"]
        assert patient.identifier[0].value == self.identifier[0]["value"]

    def test_typed_update(self):
        name = "Jack Johnson J"
        self.create_test_patients(1, name)
        new_patient = Patient(
            name=[HumanName(text=name)],
            identifier=[Identifier(system="url", value="value"), Identifier(**self.identifier[0])],
        )

        patient, created = self.client.resources(Patient).search(name=name).update(new_patient)

        assert created is False
        assert isinstance(patient, Patient)
        assert patient.identifier[0].system == "url"
        assert patient.identifier[0].value == "value"
        assert patient.identifier[1].system == self.identifier[0]["system"]
        assert patient.identifier[1].value == self.identifier[0]["value"]

    def test_typed_patch(self):
        name = "Jack Johnson J"
        self.create_test_patients(1, name)

        patient = (
            self.client.resources(Patient)
            .search(name=name)
            .patch(
                identifier=[
                    x.model_dump(exclude_none=True)
                    for x in [
                        Identifier(system="url", value="value"),
                        Identifier(**self.identifier[0]),
                    ]
                ],
            )
        )

        assert isinstance(patient, Patient)
        assert patient.identifier[0].system == "url"
        assert patient.identifier[0].value == "value"
        assert patient.identifier[1].system == self.identifier[0]["system"]
        assert patient.identifier[1].value == self.identifier[0]["value"]


def test_requests_config():
    client = SyncFHIRClient(
        FHIR_SERVER_URL,
        authorization=FHIR_SERVER_AUTHORIZATION,
        requests_config={"verify": False, "cert": "some_cert"},
    )
    json_resp_str = json.dumps(
        {"resourceType": "Bundle", "type": "searchset", "total": 0, "entry": []}
    )
    resp = MockRequestsResponse(bytes(json_resp_str, "utf-8"), 200)
    with patch("requests.request", return_value=resp) as patched_request:
        client.resources("Patient").first()
        patched_request.assert_called_with(
            ANY, ANY, json=ANY, headers=ANY, verify=False, cert="some_cert"
        )

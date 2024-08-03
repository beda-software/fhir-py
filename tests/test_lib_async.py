import json
from math import ceil
from typing import ClassVar
from unittest.mock import ANY, Mock, patch

import pytest

from fhirpy import AsyncFHIRClient
from fhirpy.base.exceptions import MultipleResourcesFound, OperationOutcome, ResourceNotFound
from fhirpy.base.utils import AttrDict
from fhirpy.lib import AsyncFHIRReference, AsyncFHIRResource
from tests.utils import MockAiohttpResponse

from .config import FHIR_SERVER_AUTHORIZATION, FHIR_SERVER_URL
from .types import HumanName, Identifier, Patient


class TestLibAsyncCase:
    URL = FHIR_SERVER_URL
    client = None
    identifier: ClassVar = [{"system": "http://example.com/env", "value": "fhirpy"}]

    @classmethod
    def get_search_set(cls, resource_type):
        return cls.client.resources(resource_type).search(**{"identifier": "fhirpy"})

    @pytest.fixture(autouse=True)
    async def _clear_db(self):
        for resource_type in ["Patient", "Practitioner"]:
            search_set = self.get_search_set(resource_type)
            async for item in search_set:
                await item.delete()

    @classmethod
    def setup_class(cls):
        cls.client = AsyncFHIRClient(cls.URL, authorization=FHIR_SERVER_AUTHORIZATION)

    async def create_resource(self, resource_type, **kwargs):
        return await self.client.resource(
            resource_type, identifier=self.identifier, **kwargs
        ).create()

    async def create_patient_model(self):
        patient = Patient(
            name=[HumanName(text="My patient")],
            identifier=[
                Identifier(
                    system=self.identifier[0]["system"],
                    value=self.identifier[0]["system"],
                )
            ],
        )
        return await self.client.create(patient)

    @pytest.mark.asyncio()
    async def test_client_str(self):
        assert str(self.client) == f"<AsyncFHIRClient {self.URL}>"

    @pytest.mark.asyncio()
    async def test_create_patient_model(self):
        patient = await self.create_patient_model()

        fetched_patient = await self.client.resources(Patient).search(_id=patient.id).first()

        assert fetched_patient.id == patient.id

    @pytest.mark.asyncio()
    async def test_client_create(self):
        patient = Patient(
            name=[HumanName(text="My patient")],
            identifier=[
                Identifier(
                    system=self.identifier[0]["system"],
                    value=self.identifier[0]["system"],
                )
            ],
        )
        created_patient = await self.client.create(patient)

        assert isinstance(created_patient, Patient)
        assert created_patient.id is not None

    @pytest.mark.asyncio()
    async def test_client_update(self):
        patient = await self.create_patient_model()
        patient.identifier = [
            *patient.identifier,
            Identifier(system="url", value="value"),
        ]

        updated_patient = await self.client.update(patient)

        assert isinstance(updated_patient, Patient)
        assert updated_patient.id == patient.id
        assert len(updated_patient.identifier) == 2  # noqa: PLR2004

    @pytest.mark.asyncio()
    async def test_client_update_fails_without_id(self):
        patient = await self.create_patient_model()
        patient.id = None

        with pytest.raises(TypeError):
            await self.client.update(patient)

    @pytest.mark.asyncio()
    async def test_client_save_new(self):
        patient = Patient(
            name=[HumanName(text="My patient")],
            identifier=[
                Identifier(
                    system=self.identifier[0]["system"],
                    value=self.identifier[0]["system"],
                )
            ],
        )

        created_patient = await self.client.save(patient)
        assert isinstance(created_patient, Patient)
        assert created_patient.id is not None

    @pytest.mark.asyncio()
    async def test_client_save_existing(self):
        patient = await self.create_patient_model()
        patient.identifier = [
            *patient.identifier,
            Identifier(system="url", value="value"),
        ]

        updated_patient = await self.client.save(patient)

        assert isinstance(updated_patient, Patient)
        assert updated_patient.id == patient.id
        assert len(updated_patient.identifier) == 2  # noqa: PLR2004

    @pytest.mark.asyncio()
    async def test_client_save_partial_update(self):
        patient = await self.create_patient_model()

        patient.identifier = [
            *patient.identifier,
            Identifier(system="url", value="value"),
        ]
        patient.name[0].text = "New patient"

        updated_patient = await self.client.save(patient, fields=["identifier"])

        assert isinstance(updated_patient, Patient)
        assert updated_patient.id == patient.id
        assert len(updated_patient.identifier) == 2  # noqa: PLR2004
        assert updated_patient.name[0].text == "My patient"

    @pytest.mark.asyncio()
    async def test_client_save_partial_update_fails_without_id(self):
        patient = await self.create_patient_model()
        patient.id = None

        with pytest.raises(TypeError):
            await self.client.save(patient, fields=["identifier"])

    @pytest.mark.asyncio()
    async def test_client_patch_specifying_reference(self):
        patient = await self.create_patient_model()
        new_identifier = [*patient.identifier, Identifier(system="url", value="value")]

        patched_patient = await self.client.patch(
            f"{patient.resourceType}/{patient.id}", identifier=new_identifier
        )

        assert isinstance(patched_patient, dict)
        assert len(patched_patient["identifier"]) == 2  # noqa: PLR2004

    @pytest.mark.asyncio()
    async def test_client_patch_specifying_resource_type_str_and_id(self):
        patient = await self.create_patient_model()
        new_identifier = [*patient.identifier, Identifier(system="url", value="value")]

        patched_patient = await self.client.patch(
            patient.resourceType, patient.id, identifier=new_identifier
        )

        assert isinstance(patched_patient, dict)
        assert len(patched_patient["identifier"]) == 2  # noqa: PLR2004

    @pytest.mark.asyncio()
    async def test_client_patch_specifying_resource_type_type_and_id(self):
        patient = await self.create_patient_model()
        new_identifier = [*patient.identifier, Identifier(system="url", value="value")]

        patched_patient = await self.client.patch(Patient, patient.id, identifier=new_identifier)

        assert isinstance(patched_patient, Patient)
        assert len(patched_patient.identifier) == 2  # noqa: PLR2004

    @pytest.mark.asyncio()
    async def test_client_patch_specifying_resource(self):
        patient = await self.create_patient_model()
        new_identifier = [*patient.identifier, Identifier(system="url", value="value")]

        patched_patient = await self.client.patch(patient, identifier=new_identifier)

        assert isinstance(patched_patient, Patient)
        assert len(patched_patient.identifier) == 2  # noqa: PLR2004

    @pytest.mark.asyncio()
    async def test_client_patch_specifying_resource_type_fails_without_id(self):
        patient = await self.create_patient_model()

        with pytest.raises(TypeError):
            await self.client.patch(patient.resourceType)

    @pytest.mark.asyncio()
    async def test_client_patch_specifying_resource_fails_without_id(self):
        patient = await self.create_patient_model()
        patient.id = None

        with pytest.raises(TypeError):
            await self.client.patch(patient)

    @pytest.mark.asyncio()
    async def test_client_delete_specifying_reference(self):
        patient = await self.create_patient_model()

        await self.client.delete(f"{patient.resourceType}/{patient.id}")

        fetched_patient = await self.client.resources(Patient).search(_id=patient.id).first()
        assert fetched_patient is None

    @pytest.mark.asyncio()
    async def test_client_delete_specifying_resource_type_str_and_id(self):
        patient = await self.create_patient_model()

        await self.client.delete(patient.resourceType, patient.id)

        fetched_patient = await self.client.resources(Patient).search(_id=patient.id).first()
        assert fetched_patient is None

    @pytest.mark.asyncio()
    async def test_client_delete_specifying_resource_type_type_and_id(self):
        patient = await self.create_patient_model()

        await self.client.delete(Patient, patient.id)

        fetched_patient = await self.client.resources(Patient).search(_id=patient.id).first()
        assert fetched_patient is None

    @pytest.mark.asyncio()
    async def test_client_delete_specifying_resource(self):
        patient = await self.create_patient_model()

        await self.client.delete(patient)

        fetched_patient = await self.client.resources(Patient).search(_id=patient.id).first()
        assert fetched_patient is None

    @pytest.mark.asyncio()
    async def test_client_delete_specifying_resource_type_fails_without_id(self):
        patient = await self.create_patient_model()

        with pytest.raises(TypeError):
            await self.client.delete(patient.resourceType)

    @pytest.mark.asyncio()
    async def test_client_delete_specifying_resource_fails_without_id(self):
        patient = await self.create_patient_model()
        patient.id = None

        with pytest.raises(TypeError):
            await self.client.delete(patient)

    @pytest.mark.asyncio()
    async def test_create_patient(self):
        await self.create_resource("Patient", id="patient", name=[{"text": "My patient"}])

        patient = await self.client.resources("Patient").search(_id="patient").get()
        assert patient["name"] == [{"text": "My patient"}]

    @pytest.mark.asyncio()
    async def test_conditional_create__create_on_no_match(self):
        await self.create_resource("Patient", id="patient")

        patient = self.client.resource(
            "Patient",
            identifier=[{"system": "http://example.com/env", "value": "other"}, self.identifier[0]],
            name=[{"text": "Indiana Jones"}],
        )
        await patient.create(identifier="other")

        assert patient.id != "patient"
        assert patient.get_by_path(["name", 0, "text"]) == "Indiana Jones"

    @pytest.mark.asyncio()
    async def test_conditional_create__skip_on_one_match(self):
        existing_patient = await self.create_resource("Patient", id="patient")

        patient = self.client.resource(
            "Patient", identifier=self.identifier, name=[{"text": "Indiana Jones"}]
        )
        await patient.create(identifier="fhirpy")

        assert patient.id == "patient"
        assert patient.get("name") is None
        assert patient.get_by_path(["meta", "versionId"]) == existing_patient.get_by_path(
            ["meta", "versionId"]
        )

    @pytest.mark.asyncio()
    async def test_conditional_create__fail_on_multiple_matches(self):
        await self.create_resource("Patient", id="patient-one")
        await self.create_resource("Patient", id="patient-two")

        with pytest.raises(MultipleResourcesFound):
            await self.client.resource("Patient", identifier=self.identifier).create(
                identifier="fhirpy"
            )

    @pytest.mark.asyncio()
    async def test_get_or_create__create_on_no_match(self):
        await self.create_resource("Patient", id="patient")

        patient_to_save = self.client.resource(
            "Patient",
            identifier=[{"system": "http://example.com/env", "value": "other"}, self.identifier[0]],
            name=[{"text": "Indiana Jones"}],
        )
        patient, created = (
            await self.client.resources("Patient")
            .search(identifier="other")
            .get_or_create(patient_to_save)
        )
        assert patient.id != "patient"
        assert patient.get_by_path(["name", 0, "text"]) == "Indiana Jones"
        assert created is True

    @pytest.mark.asyncio()
    async def test_get_or_create__skip_on_one_match(self):
        existing_patient = await self.create_resource("Patient", id="patient")

        patient_to_save = self.client.resource("Patient", identifier=self.identifier)
        patient, created = (
            await self.client.resources("Patient")
            .search(identifier="fhirpy")
            .get_or_create(patient_to_save)
        )
        assert patient.id == "patient"
        assert created is False
        assert patient.get_by_path(["meta", "versionId"]) == existing_patient.get_by_path(
            ["meta", "versionId"]
        )

    @pytest.mark.asyncio()
    async def test_conditional_operations__fail_on_multiple_matches(self):
        await self.create_resource("Patient", id="patient-one")
        await self.create_resource("Patient", id="patient-two")

        patient_to_save = self.client.resource("Patient", identifier=self.identifier)
        with pytest.raises(MultipleResourcesFound):
            await (
                self.client.resources("Patient")
                .search(identifier="fhirpy")
                .get_or_create(patient_to_save)
            )
        with pytest.raises(MultipleResourcesFound):
            await (
                self.client.resources("Patient").search(identifier="fhirpy").update(patient_to_save)
            )
        with pytest.raises(MultipleResourcesFound):
            await (
                self.client.resources("Patient").search(identifier="fhirpy").patch(patient_to_save)
            )

    @pytest.mark.asyncio()
    async def test_update_with_params__no_match(self):
        patient = await self.create_resource("Patient", id="patient", active=True)

        patient_to_update = self.client.resource(
            "Patient",
            identifier=[{"system": "http://example.com/env", "value": "other"}, self.identifier[0]],
            active=False,
        )
        new_patient, created = await (
            self.client.resources("Patient").search(identifier="other").update(patient_to_update)
        )

        await patient.refresh()
        assert patient.active is True
        assert new_patient.id != "patient"
        assert new_patient.active is False
        assert created is True

    @pytest.mark.asyncio()
    async def test_update_with_params__one_match(self):
        patient = await self.create_resource("Patient", id="patient", active=True)

        patient_to_update = self.client.resource(
            "Patient", identifier=self.identifier, name=[{"text": "Indiana Jones"}]
        )
        updated_patient, created = await (
            self.client.resources("Patient").search(identifier="fhirpy").update(patient_to_update)
        )
        assert updated_patient.id == patient.id
        assert created is False
        assert updated_patient.get_by_path(["meta", "versionId"]) != patient.get_by_path(
            ["meta", "versionId"]
        )
        assert updated_patient.get_by_path(["name", 0, "text"]) == "Indiana Jones"

        await patient.refresh()
        assert updated_patient.get_by_path(["meta", "versionId"]) == patient.get_by_path(
            ["meta", "versionId"]
        )
        assert patient.get("active") is None

    @pytest.mark.asyncio()
    async def test_patch_with_params__no_match(self):
        patient_to_patch = self.client.resource(
            "Patient",
            identifier=[{"system": "http://example.com/env", "value": "other"}, self.identifier[0]],
            active=False,
        )
        with pytest.raises(ResourceNotFound):
            await (
                self.client.resources("Patient").search(identifier="other").patch(patient_to_patch)
            )

    @pytest.mark.asyncio()
    async def test_patch_with_params__one_match(self):
        patient = await self.create_resource("Patient", id="patient", active=True)

        patched_patient = await (
            self.client.resources("Patient")
            .search(identifier="fhirpy")
            .patch(identifier=self.identifier, name=[{"text": "Indiana Jones"}])
        )
        assert patched_patient.id == patient.id
        assert patched_patient.get_by_path(["meta", "versionId"]) != patient.get_by_path(
            ["meta", "versionId"]
        )
        assert patched_patient.get_by_path(["name", 0, "text"]) == "Indiana Jones"

        await patient.refresh()
        assert patched_patient.get_by_path(["meta", "versionId"]) == patient.get_by_path(
            ["meta", "versionId"]
        )
        assert patient.active is True

    @pytest.mark.asyncio()
    async def test_patch_with_params__one_match_deprecated(self):
        patient = await self.create_resource("Patient", id="patient", active=True)

        patient_to_patch = self.client.resource(
            "Patient", identifier=self.identifier, name=[{"text": "Indiana Jones"}]
        )
        patched_patient = await (
            self.client.resources("Patient").search(identifier="fhirpy").patch(patient_to_patch)
        )
        assert patched_patient.id == patient.id
        assert patched_patient.get_by_path(["meta", "versionId"]) != patient.get_by_path(
            ["meta", "versionId"]
        )
        assert patched_patient.get_by_path(["name", 0, "text"]) == "Indiana Jones"

        await patient.refresh()
        assert patched_patient.get_by_path(["meta", "versionId"]) == patient.get_by_path(
            ["meta", "versionId"]
        )
        assert patient.active is True

    @pytest.mark.asyncio()
    async def test_update_patient(self):
        patient = await self.create_resource("Patient", id="patient", name=[{"text": "My patient"}])
        patient["active"] = True
        patient.birthDate = "1945-01-12"
        patient.name[0].text = "SomeName"
        await patient.save()

        check_patient = await self.client.resources("Patient").search(_id="patient").get()
        assert check_patient.active is True
        assert check_patient["birthDate"] == "1945-01-12"
        assert check_patient.get_by_path(["name", 0, "text"]) == "SomeName"

    @pytest.mark.asyncio()
    async def test_count(self):
        search_set = self.get_search_set("Patient")

        assert await search_set.count() == 0

        await self.create_resource("Patient", id="patient1", name=[{"text": "John Smith FHIRPy"}])

        assert await search_set.count() == 1

    @pytest.mark.asyncio()
    async def test_create_without_id(self):
        patient = await self.create_resource("Patient")

        assert patient.id is not None

    @pytest.mark.asyncio()
    async def test_reference_delete(self):
        patient = await self.create_resource("Patient", id="patient")

        await patient.to_reference().delete()

        with pytest.raises(ResourceNotFound):
            await self.get_search_set("Patient").search(_id="patient").get()

    @pytest.mark.asyncio()
    async def test_delete(self):
        patient = await self.create_resource("Patient", id="patient")
        await patient.delete()

        with pytest.raises(ResourceNotFound):
            await self.get_search_set("Patient").search(_id="patient").get()

    @pytest.mark.asyncio()
    async def test_delete_without_id_failed(self):
        patient = self.client.resource("Patient", **{})

        with pytest.raises(TypeError):
            await patient.delete()

    @pytest.mark.asyncio()
    async def test_delete_with_params__no_match(self):
        await self.create_resource("Patient", id="patient")

        _, status_code = await self.client.resources("Patient").search(identifier="other").delete()

        await self.get_search_set("Patient").search(_id="patient").get()
        assert status_code == 204  # noqa: PLR2004

    @pytest.mark.asyncio()
    async def test_delete_with_params__one_match(self):
        patient = self.client.resource(
            "Patient",
            id="patient",
            identifier=[{"system": "http://example.com/env", "value": "other"}, self.identifier[0]],
        )
        await patient.save()

        data, status_code = (
            await self.client.resources("Patient").search(identifier="other").delete()
        )

        with pytest.raises(ResourceNotFound):
            await self.get_search_set("Patient").search(_id="patient").get()
        assert status_code == 200  # noqa: PLR2004

    @pytest.mark.asyncio()
    async def test_delete_with_params__multiple_matches(self):
        await self.create_resource("Patient", id="patient-1")
        await self.create_resource("Patient", id="patient-2")

        with pytest.raises(MultipleResourcesFound):
            await self.client.resources("Patient").search(identifier="fhirpy").delete()

    @pytest.mark.asyncio()
    async def test_get_not_existing_id(self):
        with pytest.raises(ResourceNotFound):
            await self.client.resources("Patient").search(_id="FHIRPypy_not_existing_id").get()

    @pytest.mark.asyncio()
    async def test_get_more_than_one_resources(self):
        await self.create_resource("Patient", birthDate="1901-05-25")
        await self.create_resource("Patient", birthDate="1905-05-25")
        with pytest.raises(MultipleResourcesFound):
            await self.client.resources("Patient").get()
        with pytest.raises(MultipleResourcesFound):
            await self.client.resources("Patient").search(birthdate__gt="1900").get()

    @pytest.mark.asyncio()
    async def test_get_resource_by_id_is_deprecated(self):
        await self.create_resource("Patient", id="patient", gender="male")
        with pytest.warns(DeprecationWarning):
            patient = await self.client.resources("Patient").search(gender="male").get(id="patient")
        assert patient.id == "patient"

    @pytest.mark.asyncio()
    async def test_get_resource_by_search_with_id(self):
        await self.create_resource("Patient", id="patient", gender="male")
        patient = await self.client.resources("Patient").search(gender="male", _id="patient").get()
        assert patient.id == "patient"
        with pytest.raises(ResourceNotFound):
            await self.client.resources("Patient").search(gender="female", _id="patient").get()

    @pytest.mark.asyncio()
    async def test_get_resource_by_search(self):
        await self.create_resource("Patient", id="patient1", gender="male", birthDate="1901-05-25")
        await self.create_resource(
            "Patient", id="patient2", gender="female", birthDate="1905-05-25"
        )
        patient_1 = (
            await self.client.resources("Patient")
            .search(gender="male", birthdate="1901-05-25")
            .get()
        )
        assert patient_1.id == "patient1"
        patient_2 = (
            await self.client.resources("Patient")
            .search(gender="female", birthdate="1905-05-25")
            .get()
        )
        assert patient_2.id == "patient2"

    @pytest.mark.asyncio()
    async def test_not_found_error(self):
        with pytest.raises(ResourceNotFound):
            await self.client.resources("FHIRPyNotExistingResource").fetch()

    @pytest.mark.asyncio()
    async def test_operation_outcome_error(self):
        with pytest.raises(OperationOutcome):
            await self.create_resource("Patient", name="invalid")

    @pytest.mark.asyncio()
    async def test_to_resource_for_local_reference(self):
        await self.create_resource("Patient", id="p1", name=[{"text": "Name"}])

        patient_ref = self.client.reference("Patient", "p1")
        result = (await patient_ref.to_resource()).serialize()
        result.pop("meta")
        result.pop("identifier")

        assert result == {
            "resourceType": "Patient",
            "id": "p1",
            "name": [{"text": "Name"}],
        }

    @pytest.mark.asyncio()
    async def test_to_resource_for_external_reference(self):
        reference = self.client.reference(reference="http://external.com/Patient/p1")

        with pytest.raises(ResourceNotFound):
            await reference.to_resource()

    @pytest.mark.asyncio()
    async def test_to_resource_for_resource(self):
        resource = self.client.resource("Patient", id="p1", name=[{"text": "Name"}])
        resource_copy = await resource.to_resource()
        assert isinstance(resource_copy, AsyncFHIRResource)
        assert resource_copy.serialize() == {
            "resourceType": "Patient",
            "id": "p1",
            "name": [{"text": "Name"}],
        }

    def test_to_reference_for_resource_without_id(self):
        resource = self.client.resource("Patient")
        with pytest.raises(ResourceNotFound):
            resource.to_reference()

    @pytest.mark.asyncio()
    async def test_to_reference_for_resource(self):
        patient = await self.create_resource("Patient", id="p1")

        assert patient.to_reference().serialize() == {"reference": "Patient/p1"}

        assert patient.to_reference(display="patient").serialize() == {
            "reference": "Patient/p1",
            "display": "patient",
        }

    @pytest.mark.asyncio()
    async def test_create_bundle(self):
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
        await self.create_resource("Bundle", **bundle)
        await self.client.resources("Patient").search(_id="bundle_patient_1").get()
        await self.client.resources("Patient").search(_id="bundle_patient_2").get()

    @pytest.mark.asyncio()
    async def test_is_valid(self):
        resource = self.client.resource
        assert await resource("Patient", id="id123").is_valid() is True
        assert await resource("Patient", gender="female").is_valid(raise_exception=True) is True

        assert await resource("Patient", gender=True).is_valid() is False
        with pytest.raises(OperationOutcome):
            await resource("Patient", gender=True).is_valid(raise_exception=True)

        assert await resource("Patient", gender="female", custom_prop="123").is_valid() is False
        with pytest.raises(OperationOutcome):
            await resource("Patient", gender="female", custom_prop="123").is_valid(
                raise_exception=True
            )

        assert await resource("Patient", gender="female", custom_prop="123").is_valid() is False
        with pytest.raises(OperationOutcome):
            await resource("Patient", birthDate="date", custom_prop="123", telecom=True).is_valid(
                raise_exception=True
            )

    @pytest.mark.asyncio()
    async def test_get_first(self):
        await self.create_resource("Patient", id="patient_first", name=[{"text": "Abc"}])
        await self.create_resource("Patient", id="patient_second", name=[{"text": "Bbc"}])
        patient = await self.client.resources("Patient").sort("name").first()
        assert isinstance(patient, AsyncFHIRResource)
        assert patient.id == "patient_first"

    @pytest.mark.asyncio()
    async def test_fetch_raw(self):
        await self.create_resource("Patient", name=[{"text": "RareName"}])
        await self.create_resource("Patient", name=[{"text": "RareName"}])
        bundle = await self.client.resources("Patient").search(name="RareName").fetch_raw()
        assert bundle.resourceType == "Bundle"
        for entry in bundle.entry:
            assert isinstance(entry.resource, AsyncFHIRResource)
        assert len(bundle.entry) == 2  # noqa: PLR2004

    async def create_test_patients(self, count=10, name="Not Rare Name"):
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
        await self.create_resource("Bundle", **bundle)
        return patient_ids

    @pytest.mark.asyncio()
    async def test_fetch_all(self):
        patients_count = 18
        name = "Jack Johnson J"
        patient_ids = await self.create_test_patients(patients_count, name)
        patient_set = self.client.resources("Patient").search(name=name).limit(5)

        mocked_request = Mock(wraps=self.client._do_request)
        with patch.object(self.client, "_do_request", mocked_request):
            patients = await patient_set.fetch_all()

        received_ids = {p.id for p in patients}

        assert len(received_ids) == patients_count
        assert patient_ids == received_ids

        assert mocked_request.call_count == ceil(patients_count / 5)

        first_call_args, first_call_kwargs = mocked_request.call_args_list[0]
        method, path = first_call_args
        assert method == "get"
        assert "Patient" in path
        params = first_call_kwargs["params"]
        assert params == {"name": [name], "_count": [5]}

    @pytest.mark.asyncio()
    async def test_async_for_iterator(self):
        patients_count = 22
        name = "Rob Robinson R"
        patient_ids = await self.create_test_patients(patients_count, name)
        patient_set = self.client.resources("Patient").search(name=name).limit(3)

        received_ids = set()
        mocked_request = Mock(wraps=self.client._do_request)
        with patch.object(self.client, "_do_request", mocked_request):
            async for patient in patient_set:
                received_ids.add(patient.id)

        assert mocked_request.call_count == ceil(patients_count / 3)

        assert len(received_ids) == patients_count
        assert patient_ids == received_ids

    def test_build_request_url(self):
        url = f"{FHIR_SERVER_URL}/Patient?_count=100&name=ivan&name=petrov"
        request_url = self.client._build_request_url(url, None)
        assert request_url == url

    def test_build_request_url_wrong_path(self):
        url = "https://example.com/Patient?_count=100&name=ivan&name=petrov"
        with pytest.raises(ValueError):  # noqa: PT011
            self.client._build_request_url(url, None)

    @pytest.mark.asyncio()
    async def test_save_fields(self):
        patient = await self.create_resource(
            "Patient",
            id="patient_to_update",
            gender="female",
            active=False,
            birthDate="1998-01-01",
            name=[{"text": "Abc"}],
        )
        patient["gender"] = "male"
        patient["birthDate"] = "1998-02-02"
        patient["active"] = True
        patient["name"] = [{"text": "Bcd"}]
        await patient.save(fields=["gender", "birthDate"])

        patient_refreshed = await patient.to_reference().to_resource()
        assert patient_refreshed["gender"] == patient["gender"]
        assert patient_refreshed["birthDate"] == patient["birthDate"]
        assert patient_refreshed["active"] is False
        assert patient_refreshed["name"] == [{"text": "Abc"}]

    @pytest.mark.asyncio()
    async def test_update(self):
        patient_id = "patient_to_update"
        patient_initial = await self.create_resource(
            "Patient", id=patient_id, name=[{"text": "J London"}], active=False
        )
        patient_updated = self.client.resource(
            "Patient", id=patient_id, identifier=self.identifier, active=True
        )
        await patient_updated.update()

        await patient_initial.refresh()

        assert patient_initial.id == patient_updated.id
        assert patient_updated.get("name") is None
        assert patient_initial.get("name") is None
        assert patient_initial["active"] is True

    @pytest.mark.asyncio()
    async def test_patch(self):
        patient_id = "patient_to_patch"
        patient_instance_1 = await self.create_resource(
            "Patient",
            id=patient_id,
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
        patient_instance_2 = self.client.resource("Patient", id=patient_id, birthDate="2001-01-01")
        await patient_instance_2.patch(active=True, name=new_name)
        patient_instance_1_refreshed = await patient_instance_1.to_reference().to_resource()

        assert patient_instance_1_refreshed.serialize() == patient_instance_2.serialize()
        assert patient_instance_1_refreshed.active is True
        assert patient_instance_1_refreshed.birthDate == "1998-01-01"
        assert patient_instance_1_refreshed["name"] == new_name

    @pytest.mark.asyncio()
    async def test_update_without_id(self):
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
            await patient.update()
        with pytest.raises(TypeError):
            await patient.patch(active=True, name=new_name)
        patient["name"] = new_name
        with pytest.raises(TypeError):
            await patient.save(fields=["name"])
        await patient.save()

    @pytest.mark.asyncio()
    async def test_refresh(self):
        patient_id = "refresh-patient-id"
        patient = await self.create_resource("Patient", id=patient_id, active=True)

        test_patient = await self.client.reference("Patient", patient_id).to_resource()
        await test_patient.patch(gender="male", name=[{"text": "Jack London"}])
        assert patient.serialize() != test_patient.serialize()

        await patient.refresh()
        assert patient.serialize() == test_patient.serialize()

    @pytest.mark.asyncio()
    async def test_client_execute_lastn(self):
        patient = await self.create_resource("Patient", name=[{"text": "John First"}])
        observation = await self.create_resource(
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
        response = await self.client.execute(
            "Observation/$lastn",
            method="get",
            params={"patient": f"Patient/{patient.id}", "category": "vital-signs"},
        )
        assert response["resourceType"] == "Bundle"
        assert response["total"] == 1
        assert response["entry"][0]["resource"]["id"] == observation["id"]

    @pytest.mark.asyncio()
    async def test_resource_execute_lastn(self):
        patient = await self.create_resource("Patient", name=[{"text": "John First"}])
        observation = await self.create_resource(
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
        response = await patient.execute(
            "Observation/$lastn", method="get", params={"category": "vital-signs"}
        )
        assert response["resourceType"] == "Bundle"
        assert response["total"] == 1
        assert response["entry"][0]["resource"]["id"] == observation["id"]

    @pytest.mark.asyncio()
    async def test_client_execute_history(self):
        patient = await self.create_resource("Patient", name=[{"text": "John First"}])
        response = await self.client.execute(f"Patient/{patient.id}/_history", "get")
        assert response["resourceType"] == "Bundle"
        assert response["type"] == "history"
        assert "entry" in response

    @pytest.mark.asyncio()
    async def test_resource_execute_history(self):
        patient = await self.create_resource("Patient", name=[{"text": "John First"}])
        response = await patient.execute("_history", "get")
        assert response["resourceType"] == "Bundle"
        assert response["type"] == "history"
        assert response["total"] == 1
        assert "entry" in response

    @pytest.mark.asyncio()
    async def test_reference_execute_history(self):
        patient = await self.create_resource("Patient", name=[{"text": "John First"}])
        patient_ref = patient.to_reference()
        response = await patient_ref.execute("_history", "get")
        assert response["resourceType"] == "Bundle"
        assert response["type"] == "history"
        assert response["total"] == 1
        assert "entry" in response

    @pytest.mark.asyncio()
    async def test_reference_execute_history_not_local(self):
        patient_ref = self.client.reference(reference="http://external.com/Patient/p1")
        with pytest.raises(ResourceNotFound):
            await patient_ref.execute("_history", "get")

    @pytest.mark.asyncio()
    async def test_references_after_save(self):
        patient = await self.create_resource("Patient", name=[{"text": "John First"}])
        practitioner = await self.create_resource("Practitioner", name=[{"text": "Jack"}])
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
        await appointment.save()
        assert isinstance(appointment.participant[0].actor, AsyncFHIRReference)
        assert isinstance(appointment.participant[0], AttrDict)
        test_patient = await appointment.participant[0].actor.to_resource()
        assert test_patient

        assert isinstance(appointment.participant[1].actor, AsyncFHIRReference)
        assert isinstance(appointment.participant[1], AttrDict)
        test_practitioner = await appointment.participant[1].actor.to_resource()
        assert test_practitioner

    @pytest.mark.asyncio()
    async def test_references_in_resource(self):
        patient = await self.create_resource("Patient", name=[{"text": "John First"}])
        practitioner = await self.create_resource("Practitioner", name=[{"text": "Jack"}])
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
        await appointment.save()
        test_appointment = (
            await self.client.resources("Appointment").search(_id=appointment.id).get()
        )

        assert isinstance(test_appointment.participant[0].actor, AsyncFHIRReference)
        assert isinstance(test_appointment.participant[0], AttrDict)
        test_patient = await test_appointment.participant[0].actor.to_resource()
        assert test_patient

        assert isinstance(test_appointment.participant[1].actor, AsyncFHIRReference)
        assert isinstance(test_appointment.participant[1], AttrDict)
        test_practitioner = await test_appointment.participant[1].actor.to_resource()
        assert test_practitioner

    @pytest.mark.asyncio()
    async def test_types_fetch_all(self):
        patients_count = 18
        name = "Jack Johnson J"
        patient_ids = await self.create_test_patients(patients_count, name)
        patient_set = self.client.resources(Patient).search(name=name).limit(5)

        patients = await patient_set.fetch_all()

        received_ids = {p.id for p in patients}
        assert len(received_ids) == patients_count
        assert patient_ids == received_ids
        assert isinstance(patients[0], Patient)

    @pytest.mark.asyncio()
    async def test_typed_fetch(self):
        patients_count = 18
        limit = 5
        name = "Jack Johnson J"
        await self.create_test_patients(patients_count, name)
        patient_set = self.client.resources(Patient).search(name=name).limit(limit)

        patients = await patient_set.fetch()

        received_ids = {p.id for p in patients}
        assert len(received_ids) == limit
        assert isinstance(patients[0], Patient)

    @pytest.mark.asyncio()
    async def test_typed_get(self):
        name = "Jack Johnson J"
        await self.create_test_patients(1, name)
        patient_set = self.client.resources(Patient).search(name=name)

        patient = await patient_set.get()

        assert isinstance(patient, Patient)

    @pytest.mark.asyncio()
    async def test_typed_first(self):
        name = "Jack Johnson J"
        await self.create_test_patients(1, name)
        patient_set = self.client.resources(Patient).search(name=name)

        patient = await patient_set.first()

        assert isinstance(patient, Patient)

    @pytest.mark.asyncio()
    async def test_typed_get_or_create(self):
        name = "Jack Johnson J"
        await self.create_test_patients(1, name)
        new_patient = Patient(
            name=[HumanName(text=name)],
            identifier=[Identifier(system="url", value="value"), Identifier(**self.identifier[0])],
        )

        patient, created = (
            await self.client.resources(Patient).search(name=name).get_or_create(new_patient)
        )

        assert created is False
        assert isinstance(patient, Patient)
        assert patient.identifier[0].system == self.identifier[0]["system"]
        assert patient.identifier[0].value == self.identifier[0]["value"]

    @pytest.mark.asyncio()
    async def test_typed_update(self):
        name = "Jack Johnson J"
        await self.create_test_patients(1, name)
        new_patient = Patient(
            name=[HumanName(text=name)],
            identifier=[Identifier(system="url", value="value"), Identifier(**self.identifier[0])],
        )

        patient, created = (
            await self.client.resources(Patient).search(name=name).update(new_patient)
        )

        assert created is False
        assert isinstance(patient, Patient)
        assert patient.identifier[0].system == "url"
        assert patient.identifier[0].value == "value"
        assert patient.identifier[1].system == self.identifier[0]["system"]
        assert patient.identifier[1].value == self.identifier[0]["value"]

    @pytest.mark.asyncio()
    async def test_typed_patch(self):
        name = "Jack Johnson J"
        await self.create_test_patients(1, name)

        patient = (
            await self.client.resources(Patient)
            .search(name=name)
            .patch(
                identifier=[
                    Identifier(system="url", value="value"),
                    Identifier(**self.identifier[0]),
                ],
            )
        )

        assert isinstance(patient, Patient)
        assert patient.identifier[0].system == "url"
        assert patient.identifier[0].value == "value"
        assert patient.identifier[1].system == self.identifier[0]["system"]
        assert patient.identifier[1].value == self.identifier[0]["value"]


@pytest.mark.asyncio()
async def test_aiohttp_config():
    client = AsyncFHIRClient(
        FHIR_SERVER_URL,
        authorization=FHIR_SERVER_AUTHORIZATION,
        aiohttp_config={"ssl": False, "proxy": "http://example.com"},
    )
    resp = MockAiohttpResponse(
        bytes(
            json.dumps({"resourceType": "Bundle", "type": "searchset", "total": 0, "entry": []}),
            "utf-8",
        ),
        200,
    )
    with patch("aiohttp.ClientSession.request", return_value=resp) as patched_request:
        await client.resources("Patient").first()
        patched_request.assert_called_with(
            ANY, ANY, json=None, ssl=False, proxy="http://example.com"
        )

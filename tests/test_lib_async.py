import json
import pytest
from math import ceil
from aiohttp import request
from unittest.mock import Mock, patch, ANY
from urllib.parse import parse_qs, urlparse

from fhirpy import AsyncFHIRClient
from fhirpy.base.utils import AttrDict
from fhirpy.lib import AsyncFHIRResource, AsyncFHIRReference
from fhirpy.base.exceptions import (
    ResourceNotFound,
    OperationOutcome,
    MultipleResourcesFound,
)
from .config import FHIR_SERVER_URL, FHIR_SERVER_AUTHORIZATION


class TestLibAsyncCase:
    URL = FHIR_SERVER_URL
    client = None
    identifier = [{"system": "http://example.com/env", "value": "fhirpy"}]

    @classmethod
    def get_search_set(cls, resource_type):
        return cls.client.resources(resource_type).search(**{"identifier": "fhirpy"})

    @pytest.fixture(autouse=True)
    @pytest.mark.asyncio
    async def clearDb(self):
        for resource_type in ["Patient", "Practitioner"]:
            search_set = self.get_search_set(resource_type)
            async for item in search_set:
                await item.delete()

    @classmethod
    def setup_class(cls):
        cls.client = AsyncFHIRClient(cls.URL, authorization=FHIR_SERVER_AUTHORIZATION)

    async def create_resource(self, resource_type, **kwargs):
        p = self.client.resource(resource_type, identifier=self.identifier, **kwargs)
        await p.save()

        return p

    @pytest.mark.asyncio
    async def test_create_patient(self):
        await self.create_resource(
            "Patient", id="patient", name=[{"text": "My patient"}]
        )

        patient = await self.client.resources("Patient").search(_id="patient").get()
        assert patient["name"] == [{"text": "My patient"}]

    @pytest.mark.asyncio
    async def test_update_patient(self):
        patient = await self.create_resource(
            "Patient", id="patient", name=[{"text": "My patient"}]
        )
        patient["active"] = True
        patient.birthDate = "1945-01-12"
        patient.name[0].text = "SomeName"
        await patient.save()

        check_patient = (
            await self.client.resources("Patient").search(_id="patient").get()
        )
        assert check_patient.active is True
        assert check_patient["birthDate"] == "1945-01-12"
        assert check_patient.get_by_path(["name", 0, "text"]) == "SomeName"

    @pytest.mark.asyncio
    async def test_count(self):
        search_set = self.get_search_set("Patient")

        assert await search_set.count() == 0

        await self.create_resource(
            "Patient", id="patient1", name=[{"text": "John Smith FHIRPy"}]
        )

        assert await search_set.count() == 1

    @pytest.mark.asyncio
    async def test_create_without_id(self):
        patient = await self.create_resource("Patient")

        assert patient.id is not None

    @pytest.mark.asyncio
    async def test_delete(self):
        patient = await self.create_resource("Patient", id="patient")
        await patient.delete()

        with pytest.raises(ResourceNotFound):
            await self.get_search_set("Patient").search(_id="patient").get()

    @pytest.mark.asyncio
    async def test_get_not_existing_id(self):
        with pytest.raises(ResourceNotFound):
            await self.client.resources("Patient").search(
                _id="FHIRPypy_not_existing_id"
            ).get()

    @pytest.mark.asyncio
    async def test_get_more_than_one_resources(self):
        await self.create_resource("Patient", birthDate="1901-05-25")
        await self.create_resource("Patient", birthDate="1905-05-25")
        with pytest.raises(MultipleResourcesFound):
            await self.client.resources("Patient").get()
        with pytest.raises(MultipleResourcesFound):
            await self.client.resources("Patient").search(birthdate__gt="1900").get()

    @pytest.mark.asyncio
    async def test_get_resource_by_id_is_deprecated(self):
        await self.create_resource("Patient", id="patient", gender="male")
        with pytest.warns(DeprecationWarning):
            patient = (
                await self.client.resources("Patient")
                .search(gender="male")
                .get(id="patient")
            )
        assert patient.id == "patient"

    @pytest.mark.asyncio
    async def test_get_resource_by_search_with_id(self):
        await self.create_resource("Patient", id="patient", gender="male")
        patient = (
            await self.client.resources("Patient")
            .search(gender="male", _id="patient")
            .get()
        )
        assert patient.id == "patient"
        with pytest.raises(ResourceNotFound):
            await self.client.resources("Patient").search(
                gender="female", _id="patient"
            ).get()

    @pytest.mark.asyncio
    async def test_get_resource_by_search(self):
        await self.create_resource(
            "Patient", id="patient1", gender="male", birthDate="1901-05-25"
        )
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

    @pytest.mark.asyncio
    async def test_not_found_error(self):
        with pytest.raises(ResourceNotFound):
            await self.client.resources("FHIRPyNotExistingResource").fetch()

    @pytest.mark.asyncio
    async def test_operation_outcome_error(self):
        with pytest.raises(OperationOutcome):
            await self.create_resource("Patient", name="invalid")

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_to_resource_for_external_reference(self):
        reference = self.client.reference(reference="http://external.com/Patient/p1")

        with pytest.raises(ResourceNotFound):
            await reference.to_resource()

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_to_reference_for_resource(self):
        patient = await self.create_resource("Patient", id="p1")

        assert patient.to_reference().serialize() == {"reference": "Patient/p1"}

        assert patient.to_reference(display="patient").serialize() == {
            "reference": "Patient/p1",
            "display": "patient",
        }

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_is_valid(self):
        resource = self.client.resource
        assert await resource("Patient", id="id123").is_valid() is True
        assert (
            await resource("Patient", gender="female").is_valid(raise_exception=True)
            is True
        )

        assert await resource("Patient", gender=True).is_valid() is False
        with pytest.raises(OperationOutcome):
            await resource("Patient", gender=True).is_valid(raise_exception=True)

        assert (
            await resource("Patient", gender="female", custom_prop="123").is_valid()
            is False
        )
        with pytest.raises(OperationOutcome):
            await resource("Patient", gender="female", custom_prop="123").is_valid(
                raise_exception=True
            )

        assert (
            await resource("Patient", gender="female", custom_prop="123").is_valid()
            is False
        )
        with pytest.raises(OperationOutcome):
            await resource(
                "Patient", birthDate="date", custom_prop="123", telecom=True
            ).is_valid(raise_exception=True)

    @pytest.mark.asyncio
    async def test_get_first(self):
        await self.create_resource(
            "Patient", id="patient_first", name=[{"text": "Abc"}]
        )
        await self.create_resource(
            "Patient", id="patient_second", name=[{"text": "Bbc"}]
        )
        patient = await self.client.resources("Patient").sort("name").first()
        assert isinstance(patient, AsyncFHIRResource)
        assert patient.id == "patient_first"

    @pytest.mark.asyncio
    async def test_fetch_raw(self):
        await self.create_resource("Patient", name=[{"text": "RareName"}])
        await self.create_resource("Patient", name=[{"text": "RareName"}])
        bundle = (
            await self.client.resources("Patient").search(name="RareName").fetch_raw()
        )
        assert bundle.resourceType == "Bundle"
        for entry in bundle.entry:
            assert isinstance(entry.resource, AsyncFHIRResource)
        assert len(bundle.entry) == 2

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

    @pytest.mark.asyncio
    async def test_fetch_all(self):
        patients_count = 18
        name = "Jack Johnson J"
        patient_ids = await self.create_test_patients(patients_count, name)
        patient_set = self.client.resources("Patient").search(name=name).limit(5)

        mocked_request = Mock(wraps=request)
        with patch("aiohttp.request", mocked_request):
            patients = await patient_set.fetch_all()

        received_ids = set(p.id for p in patients)

        assert len(received_ids) == patients_count
        assert patient_ids == received_ids

        assert mocked_request.call_count == ceil(patients_count / 5)

        first_call_args = mocked_request.call_args_list[0][0]
        first_call_url = list(first_call_args)[1]
        parsed = urlparse(first_call_url)
        params = parse_qs(parsed.query)
        path = parsed.path
        assert "/Patient" in path
        assert params == {"name": [name], "_count": ["5"]}

    @pytest.mark.asyncio
    async def test_async_for_iterator(self):
        patients_count = 22
        name = "Rob Robinson R"
        patient_ids = await self.create_test_patients(patients_count, name)
        patient_set = self.client.resources("Patient").search(name=name).limit(3)

        received_ids = set()
        mocked_request = Mock(wraps=request)
        with patch("aiohttp.request", mocked_request):
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
        url = f"https://example.com/Patient?_count=100&name=ivan&name=petrov"
        with pytest.raises(ValueError):
            self.client._build_request_url(url, None)

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_update(self):
        patient = await self.create_resource(
            "Patient", id="patient_to_update", name=[{"text": "J London"}], active=False
        )
        new_name = [
            {
                "text": "Jack London",
                "family": "London",
                "given": ["Jack"],
            }
        ]
        await patient.update(active=True, name=new_name)
        patient_refreshed = await patient.to_reference().to_resource()
        assert patient_refreshed.serialize() == patient.serialize()
        assert patient["name"] == new_name
        assert patient["active"] is True

    @pytest.mark.asyncio
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
            await patient.update(active=True, name=new_name)
        with pytest.raises(TypeError):
            patient["name"] = new_name
            await patient.save(fields=["name"])
        await patient.save()

    @pytest.mark.asyncio
    async def test_refresh(self):
        patient_id = "refresh-patient-id"
        patient = await self.create_resource("Patient", id=patient_id, active=True)

        test_patient = await self.client.reference("Patient", patient_id).to_resource()
        await test_patient.update(gender="male", name=[{"text": "Jack London"}])
        assert patient.serialize() != test_patient.serialize()

        await patient.refresh()
        assert patient.serialize() == test_patient.serialize()

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_client_execute_history(self):
        patient = await self.create_resource("Patient", name=[{"text": "John First"}])
        response = await self.client.execute(f"Patient/{patient.id}/_history", "get")
        assert response["resourceType"] == "Bundle"
        assert response["type"] == "history"
        assert "entry" in response

    @pytest.mark.asyncio
    async def test_resource_execute_history(self):
        patient = await self.create_resource("Patient", name=[{"text": "John First"}])
        response = await patient.execute("_history", "get")
        assert response["resourceType"] == "Bundle"
        assert response["type"] == "history"
        assert response["total"] == 1
        assert "entry" in response

    @pytest.mark.asyncio
    async def test_reference_execute_history(self):
        patient = await self.create_resource("Patient", name=[{"text": "John First"}])
        patient_ref = patient.to_reference()
        response = await patient_ref.execute("_history", "get")
        assert response["resourceType"] == "Bundle"
        assert response["type"] == "history"
        assert response["total"] == 1
        assert "entry" in response

    @pytest.mark.asyncio
    async def test_reference_execute_history_not_local(self):
        patient_ref = self.client.reference(reference="http://external.com/Patient/p1")
        with pytest.raises(ResourceNotFound):
            await patient_ref.execute("_history", "get")

    @pytest.mark.asyncio
    async def test_references_after_save(self):
        patient = await self.create_resource("Patient", name=[{"text": "John First"}])
        practitioner = await self.create_resource(
            "Practitioner", name=[{"text": "Jack"}]
        )
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

    @pytest.mark.asyncio
    async def test_references_in_resource(self):
        patient = await self.create_resource("Patient", name=[{"text": "John First"}])
        practitioner = await self.create_resource(
            "Practitioner", name=[{"text": "Jack"}]
        )
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


@pytest.mark.asyncio
async def test_aiohttp_config():
    client = AsyncFHIRClient(
        FHIR_SERVER_URL,
        authorization=FHIR_SERVER_AUTHORIZATION,
        aiohttp_config={"ssl": False, "proxy": "http://example.com"},
    )
    resp = MockAiohttpResponse(
        bytes(
            json.dumps(
                {"resourceType": "Bundle", "type": "searchset", "total": 0, "entry": []}
            ),
            "utf-8",
        ),
        200,
    )
    with patch("aiohttp.ClientSession.request", return_value=resp) as patched_request:
        await client.resources("Patient").first()
        patched_request.assert_called_with(
            ANY, ANY, json=None, ssl=False, proxy="http://example.com"
        )

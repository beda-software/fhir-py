import pytest
import logging
from requests.auth import _basic_auth_str

from fhirpy import AsyncFHIRClient
from fhirpy.lib import AsyncFHIRReference, AsyncFHIRResource
from fhirpy.lib import load_schema
from fhirpy.base.exceptions import ResourceNotFound, OperationOutcome

# pytestmark = pytest.mark.asyncio

class TestLibAsyncCase(object):
    URL = 'http://localhost:8080/fhir'
    client = None
    identifier = [{'system': 'http://example.com/env',
                   'value': 'fhirpy'}]

    @classmethod
    def get_search_set(cls, resource_type):
        return cls.client.resources(resource_type).search(**{
            'identifier': 'fhirpy'
        })
    
    @pytest.fixture(autouse=True)
    @pytest.mark.asyncio
    async def clearDb(self):
        for resource_type in ['Patient', 'Practitioner']:
            search_set = await self.get_search_set(resource_type).fetch()
            for item in search_set:
                await item.delete()

    @classmethod
    def setup_class(cls):
        cls.client = AsyncFHIRClient(cls.URL, authorization=_basic_auth_str('root', 'secret'))

    @classmethod
    def teardown_class(self):
        self.client.clear_resources_cache()

    def test_load_schema_for_invalid_path_failed(self):
        with pytest.raises(FileNotFoundError):
            load_schema('invalid')
    
    async def create_resource(self, resource_type, **kwargs):
        logging.error('Self client: %s', self.client)
        p = self.client.resource(
            resource_type,
            identifier=self.identifier,
            **kwargs)
        await p.save()

        return p

    @pytest.mark.asyncio
    async def test_create_patient(self):
        await self.create_resource(
            'Patient',
            id='patient',
            name=[{'text': 'My patient'}])

        patient = await self.client.resources('Patient').get('patient')
        assert patient['name'] == [{'text': 'My patient'}]

    @pytest.mark.asyncio
    async def test_count(self):
        search_set = self.get_search_set('Patient')

        assert await search_set.count() == 0

        await self.create_resource(
            'Patient',
            id='patient1',
            name=[{'text': 'John Smith FHIRPy'}])

        assert await search_set.count() == 1

    @pytest.mark.asyncio
    async def test_create_without_id(self):
        patient = await self.create_resource('Patient')

        assert patient.id is not None

    @pytest.mark.asyncio
    async def test_delete(self):
        patient = await self.create_resource('Patient', id='patient')
        await patient.delete()

        with pytest.raises(OperationOutcome):
            await self.get_search_set('Patient').get(id='patient')

    @pytest.mark.asyncio
    async def test_get_not_existing_id(self):
        with pytest.raises(ResourceNotFound):
            await self.client.resources('Patient').get(id='FHIRPypy_not_existing_id')

    def test_get_set_bad_attr(self):
        with pytest.raises(KeyError):
            self.client.resource('Patient', notPatientField='field')

        with pytest.raises(KeyError):
            patient = self.client.resource('Patient')
            patient['notPatientField'] = 'field'

        with pytest.raises(KeyError):
            patient = self.client.resource('Patient')
            _ = patient['notPatientField']

    def test_resource_without_resource_type_failed(self):
        with pytest.raises(TypeError):
            self.client.resource()

    def test_resource_success(self):
        resource = self.client.resource('Patient', id='p1')
        assert resource.resource_type == 'Patient'
        assert resource['resourceType'] == 'Patient'
        assert resource.id == 'p1'
        assert resource['id'] == 'p1'
        assert resource.reference == 'Patient/p1'
        assert resource.serialize() == {
            'resourceType': 'Patient',
            'id': 'p1',
        }

    def test_reference_from_local_reference(self):
        reference = self.client.reference(reference='Patient/p1')
        assert reference.is_local is True
        assert reference.resource_type == 'Patient'
        assert reference.id == 'p1'
        assert reference.reference == 'Patient/p1'
        assert reference['reference'] == 'Patient/p1'
        reference.serialize() == {
            'reference': 'Patient/p1'
        }

    def test_reference_from_external_reference(self):
        reference = self.client.reference(
            reference='http://external.com/Patient/p1')
        assert reference.is_local == False
        assert reference.resource_type is None
        assert reference.id is None
        assert reference.reference == 'http://external.com/Patient/p1'
        assert reference['reference'] == 'http://external.com/Patient/p1'
        assert reference.serialize() == {
            'reference': 'http://external.com/Patient/p1'
        }

    def test_reference_from_resource_type_and_id(self):
        reference = self.client.reference('Patient', 'p1')
        assert reference.resource_type == 'Patient'
        assert reference.id == 'p1'
        assert reference.reference == 'Patient/p1'
        assert reference['reference'] == 'Patient/p1'
        assert reference.serialize() == {
            'reference': 'Patient/p1'
        }

    @pytest.mark.asyncio
    async def test_not_found_error(self):
        with pytest.raises(ResourceNotFound):
            await self.client.resources('FHIRPyNotExistingResource').fetch()

    @pytest.mark.asyncio
    async def test_operation_outcome_error(self):
        with pytest.raises(OperationOutcome):
            await self.create_resource('Patient', name='invalid')

    @pytest.mark.asyncio
    async def test_to_resource_for_local_reference(self):
        await self.create_resource(
            'Patient', id='p1', name=[{'text': 'Name'}])

        patient_ref = self.client.reference('Patient', 'p1')
        result = (await patient_ref.to_resource()).serialize()
        result.pop('meta')
        result.pop('identifier')

        assert result == {
            'resourceType': 'Patient',
            'id': 'p1',
            'name': [{'text': 'Name'}]
        }

    @pytest.mark.asyncio
    async def test_to_resource_for_external_reference(self):
        reference = self.client.reference(
            reference='http://external.com/Patient/p1')

        with pytest.raises(ResourceNotFound):
            await reference.to_resource()

    def test_to_resource_for_resource(self):
        resource = self.client.resource(
            'Patient', id='p1', name=[{'text': 'Name'}])
        resource_copy = resource.to_resource()
        assert isinstance(resource_copy, AsyncFHIRResource)
        assert resource_copy.serialize() == {'resourceType': 'Patient',
            'id': 'p1',
            'name': [{'text': 'Name'}]
        }

    def test_to_reference_for_resource_without_id(self):
        resource = self.client.resource('Patient')
        with pytest.raises(ResourceNotFound):
            resource.to_reference()

    @pytest.mark.asyncio
    async def test_to_reference_for_resource(self):
        patient = await self.create_resource('Patient', id='p1')

        assert patient.to_reference().serialize() == \
            {'reference': 'Patient/p1'}

        assert patient.to_reference(display='patient').serialize() == {
            'reference': 'Patient/p1',
            'display': 'patient',
        }

    def test_to_reference_for_reference(self):
        reference = self.client.reference('Patient', 'p1')
        reference_copy = reference.to_reference(display='patient')
        assert isinstance(reference_copy, AsyncFHIRReference)
        assert reference_copy.serialize() == {
            'reference': 'Patient/p1',
            'display': 'patient',
        }

    def test_serialize(self):
        practitioner1 = self.client.resource('Practitioner', id='pr1')
        practitioner2 = self.client.resource('Practitioner', id='pr2')
        patient = self.client.resource(
            'Patient',
            id='patient',
            generalPractitioner=[
                practitioner1.to_reference(display='practitioner'),
                practitioner2])

        assert patient.serialize() == {
            'resourceType': 'Patient',
            'id': 'patient',
            'generalPractitioner': [
                {
                    'reference': 'Practitioner/pr1',
                    'display': 'practitioner',
                },
                {
                    'reference': 'Practitioner/pr2',
                },
            ],
        }

    def test_equality(self):
        resource = self.client.resource('Patient', id='p1')
        reference = self.client.reference('Patient', 'p1')
        assert resource == reference

    def test_bundle_path(self):
        bundle_resource = self.client.resource('Bundle')
        assert bundle_resource._get_path() == ''

    @pytest.mark.asyncio
    async def test_create_bundle(self): 
        bundle = {
            'resourceType': 'bundle',
            'type': 'transaction',
            'entry': [
                {
                    'request': {
                        'method': 'POST',
                        'url': '/Patient'
                    },
                    'resource': {
                        'id': 'bundle_patient_1',
                        'identifier': self.identifier,
                    }
                },
                {
                    'request': {
                        'method': 'POST',
                        'url': '/Patient'
                    },
                    'resource': {
                        'id': 'bundle_patient_2',
                        'identifier': self.identifier,
                    }
                },
            ],
        }
        bundle_resource = await self.create_resource('Bundle', **bundle)
        patient_1 = await self.client.resources('Patient').get(id='bundle_patient_1')
        patient_2 = await self.client.resources('Patient').get(id='bundle_patient_2')


class TestSearchSet(object):
    @classmethod
    def setup_class(cls):
        cls.client = AsyncFHIRClient('mock')

    def test_search(self):
        search_set = self.client.resources('Patient') \
            .search(name='John,Ivan') \
            .search(name='Smith') \
            .search(birth_date='2010-01-01')
        assert search_set.params == {
            'name': ['John,Ivan', 'Smith'],
            'birth_date': ['2010-01-01']
        }

    def test_sort(self):
        search_set = self.client.resources('Patient') \
            .sort('id').sort('deceased')
        assert search_set.params == {'_sort': ['deceased']}

    def test_page(self):
        search_set = self.client.resources('Patient') \
            .page(1).page(2)
        assert search_set.params == {'page': [2]}

    def test_limit(self):
        search_set = self.client.resources('Patient') \
            .limit(1).limit(2)
        assert search_set.params == {'_count': [2]}

    def test_elements(self):
        search_set = self.client.resources('Patient') \
            .elements('deceased').elements('gender')

        assert set(search_set.params.keys()) == {'_elements'}
        assert len(search_set.params['_elements']) == 1
        assert set(search_set.params['_elements'][0].split(',')) == {
            'id', 'resourceType', 'gender'
        }

    def test_elements_exclude(self):
        search_set = self.client.resources('Patient') \
            .elements('name', exclude=True)
        assert search_set.params == {'_elements': ['-name']}

    def test_include(self):
        search_set = self.client.resources('Patient') \
            .include('Patient', 'general-practitioner')
        assert search_set.params == {
            '_include': ['Patient:general-practitioner']
        }

    def test_has(self):
        search_set = self.client.resources('Patient') \
            .has('Observation', 'patient', 'AuditEvent', 'entity',
                 user='id',
                 type='test')
        assert search_set.params == {
            '_has:Observation:patient:_has:AuditEvent:entity:user': [
                'id'
            ],
            '_has:Observation:patient:_has:AuditEvent:entity:type': [
                'test'
            ],
        }

    def test_has_failed(self):
        with pytest.raises(TypeError):
            self.client.resources('Patient').has('Observation',code='code')

    def test_include_multiple(self):
        search_set = self.client.resources('Orginaztion') \
            .include('Patient', 'general-practitioner') \
            .include('Patient', 'organization')

        assert search_set.params == {
            '_include': ['Patient:general-practitioner',
                         'Patient:organization']
        }

    def test_include_with_target(self):
        search_set = self.client.resources('Patient') \
            .include('Patient', 'general-practitioner', 'Organization')
        assert search_set.params == {
            '_include': ['Patient:general-practitioner:Organization']
        }

    def test_include_recursive(self):
        search_set = self.client.resources('Patient') \
            .include('Organization', 'partof', recursive=True)
        assert search_set.params == {
            '_include:recursive': ['Organization:partof']
        }

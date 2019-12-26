import pytest
import responses
from requests.auth import _basic_auth_str

from fhirpy import SyncFHIRClient
from fhirpy.lib import SyncFHIRResource
from fhirpy.base.exceptions import (
    ResourceNotFound, OperationOutcome, MultipleResourcesFound, InvalidResponse
)


class TestLibSyncCase(object):
    URL = 'http://localhost:8080/fhir'
    client = None
    identifier = [{'system': 'http://example.com/env', 'value': 'fhirpy'}]

    @classmethod
    def get_search_set(cls, resource_type):
        return cls.client.resources(resource_type).search(
            **{'identifier': 'fhirpy'}
        )

    @classmethod
    @pytest.fixture(autouse=True)
    def clearDb(cls):
        for resource_type in ['Patient', 'Practitioner']:
            search_set = cls.get_search_set(resource_type)
            for item in search_set:
                item.delete()

    @classmethod
    def setup_class(cls):
        cls.client = SyncFHIRClient(
            cls.URL,
            authorization=_basic_auth_str('root', 'secret'),
            extra_headers={'Access-Control-Allow-Origin': '*'}
        )

    def create_resource(self, resource_type, **kwargs):
        p = self.client.resource(
            resource_type, identifier=self.identifier, **kwargs
        )
        p.save()

        return p

    def test_create_patient(self):
        self.create_resource(
            'Patient', id='patient', name=[{
                'text': 'My patient'
            }]
        )

        patient = self.client.resources('Patient').search(id='patient').get()
        assert patient['name'] == [{'text': 'My patient'}]

    def test_update_patient(self):
        patient = self.create_resource(
            'Patient', id='patient', name=[{
                'text': 'My patient'
            }]
        )
        patient['active'] = True
        patient.birthDate = '1945-01-12'
        patient.name[0].text = 'SomeName'
        patient.save()

        check_patient = self.client.resources('Patient') \
            .search(id='patient').get()
        assert check_patient.active is True
        assert check_patient['birthDate'] == '1945-01-12'
        assert check_patient.get_by_path(['name', 0, 'text']) == 'SomeName'

    def test_count(self):
        search_set = self.get_search_set('Patient')

        assert search_set.count() == 0

        self.create_resource(
            'Patient', id='patient1', name=[{
                'text': 'John Smith FHIRPy'
            }]
        )

        assert search_set.count() == 1

    def test_create_without_id(self):
        patient = self.create_resource('Patient')

        assert patient.id is not None

    def test_delete(self):
        patient = self.create_resource('Patient', id='patient')
        patient.delete()

        with pytest.raises(ResourceNotFound):
            self.get_search_set('Patient').search(id='patient').get()

    def test_get_not_existing_id(self):
        with pytest.raises(ResourceNotFound):
            self.client.resources('Patient') \
                .search(id='FHIRPypy_not_existing_id').get()

    def test_get_more_than_one_resources(self):
        self.create_resource('Patient', birthDate='1901-05-25')
        self.create_resource('Patient', birthDate='1905-05-25')
        with pytest.raises(MultipleResourcesFound):
            self.client.resources('Patient').get()
        with pytest.raises(MultipleResourcesFound):
            self.client.resources('Patient') \
                .search(birthdate__gt='1900').get()

    def test_get_resource_by_id_is_deprecated(self):
        self.create_resource('Patient', id='patient', gender='male')
        with pytest.warns(DeprecationWarning):
            patient = self.client.resources('Patient') \
                .search(gender='male').get(id='patient')
        assert patient.id == 'patient'

    def test_get_resource_by_search_with_id(self):
        self.create_resource('Patient', id='patient', gender='male')
        patient = self.client.resources('Patient') \
            .search(gender='male', id='patient').get()
        assert patient.id == 'patient'
        with pytest.raises(ResourceNotFound):
            self.client.resources('Patient') \
                .search(gender='female', id='patient').get()

    def test_get_resource_by_search(self):
        self.create_resource(
            'Patient', id='patient1', gender='male', birthDate='1901-05-25'
        )
        self.create_resource(
            'Patient', id='patient2', gender='female', birthDate='1905-05-25'
        )
        patient_1 = self.client.resources('Patient') \
            .search(gender='male', birthdate='1901-05-25').get()
        assert patient_1.id == 'patient1'
        patient_2 = self.client.resources('Patient') \
            .search(gender='female', birthdate='1905-05-25').get()
        assert patient_2.id == 'patient2'

    def test_not_found_error(self):
        with pytest.raises(ResourceNotFound):
            self.client.resources('FHIRPyNotExistingResource').fetch()

    def test_operation_outcome_error(self):
        with pytest.raises(OperationOutcome):
            self.create_resource('Patient', name='invalid')

    def test_to_resource_for_local_reference(self):
        self.create_resource('Patient', id='p1', name=[{'text': 'Name'}])

        patient_ref = self.client.reference('Patient', 'p1')
        result = patient_ref.to_resource().serialize()
        result.pop('meta')
        result.pop('identifier')

        assert result == {
            'resourceType': 'Patient',
            'id': 'p1',
            'name': [{
                'text': 'Name'
            }]
        }

    def test_to_resource_for_external_reference(self):
        reference = self.client.reference(
            reference='http://external.com/Patient/p1'
        )

        with pytest.raises(ResourceNotFound):
            reference.to_resource()

    def test_to_resource_for_resource(self):
        resource = self.client.resource(
            'Patient', id='p1', name=[{
                'text': 'Name'
            }]
        )
        resource_copy = resource.to_resource()
        assert isinstance(resource_copy, SyncFHIRResource)
        assert resource_copy.serialize() == {
            'resourceType': 'Patient',
            'id': 'p1',
            'name': [{
                'text': 'Name'
            }]
        }

    def test_to_reference_for_resource_without_id(self):
        resource = self.client.resource('Patient')
        with pytest.raises(ResourceNotFound):
            resource.to_reference()

    def test_to_reference_for_resource(self):
        patient = self.create_resource('Patient', id='p1')

        assert patient.to_reference().serialize() == \
            {'reference': 'Patient/p1'}

        assert patient.to_reference(display='patient').serialize() == {
            'reference': 'Patient/p1',
            'display': 'patient',
        }

    def test_create_bundle(self):
        bundle = {
            'resourceType':
                'bundle',
            'type':
                'transaction',
            'entry':
                [
                    {
                        'request': {
                            'method': 'POST',
                            'url': '/Patient'
                        },
                        'resource':
                            {
                                'id': 'bundle_patient_1',
                                'identifier': self.identifier,
                            }
                    },
                    {
                        'request': {
                            'method': 'POST',
                            'url': '/Patient'
                        },
                        'resource':
                            {
                                'id': 'bundle_patient_2',
                                'identifier': self.identifier,
                            }
                    },
                ],
        }
        self.create_resource('Bundle', **bundle)
        self.client.resources('Patient').search(
            id='bundle_patient_1'
        ).get()
        self.client.resources('Patient').search(
            id='bundle_patient_2'
        ).get()

    def test_is_valid(self):
        resource = self.client.resource
        assert resource('Patient', id='id123').is_valid() is True
        assert resource('Patient', gender='female') \
            .is_valid(raise_exception=True) is True

        assert resource('Patient', gender=True).is_valid() is False
        with pytest.raises(OperationOutcome):
            resource('Patient', gender=True) \
                .is_valid(raise_exception=True)

        assert resource('Patient', gender='female', custom_prop='123') \
            .is_valid() is False
        with pytest.raises(OperationOutcome):
            resource('Patient', gender='female', custom_prop='123') \
                .is_valid(raise_exception=True)

        assert resource('Patient', gender='female', custom_prop='123') \
            .is_valid() is False

    def test_get_first(self):
        self.create_resource(
            'Patient', id='patient_first', name=[{
                'text': 'Abc'
            }]
        )
        self.create_resource(
            'Patient', id='patient_second', name=[{
                'text': 'Bbc'
            }]
        )
        patient = self.client.resources('Patient').sort('name').first()
        assert isinstance(patient, SyncFHIRResource)
        assert patient.id == 'patient_first'

    def test_fetch_raw(self):
        self.create_resource('Patient', name=[{'text': 'RareName'}])
        self.create_resource('Patient', name=[{'text': 'RareName'}])
        bundle = self.client.resources('Patient').search(
            name='RareName').fetch_raw()
        assert bundle.resourceType == 'Bundle'
        for entry in bundle.entry:
            assert isinstance(entry.resource, SyncFHIRResource)
        assert len(bundle.entry) == 2

    def test_fetch_all(self):
        bundle = {
            'type': 'transaction',
            'entry': [],
        }
        for i in range(18):
            bundle['entry'].append(
                {
                    'request': {
                        'method': 'POST',
                        'url': '/Patient'
                    },
                    'resource':
                        {
                            'name': [{
                                'text': 'NotSoRareName'
                            }],
                            'identifier': self.identifier
                        },
                }
            )
        self.create_resource('Bundle', **bundle)
        patients = self.client.resources('Patient').search(
            name='NotSoRareName'
        ).limit(5).fetch_all()
        assert isinstance(patients, list)
        assert len(patients) == 18

    @responses.activate
    def test_fetch_bundle_invalid_response_resource_type(self):
        patients = self.client.resources('Patient')
        responses.add(
            responses.GET,
            self.URL + '/Patient',
            json={'resourceType': 'Patient'},
            status=200
        )
        with pytest.raises(InvalidResponse):
            patients.fetch()

    @responses.activate
    def test_client_headers(self):
        patients = self.client.resources('Patient')
        responses.add(
            responses.GET,
            self.URL + '/Patient',
            json={'resourceType': 'Bundle'},
            status=200
        )
        patients.fetch()
        request_headers = responses.calls[0].request.headers
        assert request_headers['Access-Control-Allow-Origin'] == '*'

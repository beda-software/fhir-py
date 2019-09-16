from unittest2 import TestCase
from requests.auth import _basic_auth_str

from fhirpy import SyncFHIRClient
from fhirpy.lib import SyncFHIRReference, SyncFHIRResource
from fhirpy.lib import load_schema
from fhirpy.base.exceptions import ResourceNotFound, OperationOutcome


class LibTestCase(TestCase):
    URL = 'http://localhost:8080/fhir'
    client = None
    identifier = [{'system': 'http://example.com/env',
                   'value': 'fhirpy'}]

    @classmethod
    def get_search_set(cls, resource_type):
        return cls.client.resources(resource_type).search(**{
            'identifier': 'fhirpy'
        })

    @classmethod
    def clearDb(cls):
        for resource_type in ['Patient', 'Practitioner']:
            search_set = cls.get_search_set(resource_type)
            for item in search_set:
                item.delete()

    @classmethod
    def setUpClass(cls):
        cls.client = SyncFHIRClient(cls.URL, authorization=_basic_auth_str('root', 'secret'))
        cls.clearDb()

    def tearDown(self):
        self.client.clear_resources_cache()
        self.clearDb()

    def test_load_schema_for_invalid_path_failed(self):
        with self.assertRaises(FileNotFoundError):
            load_schema('invalid')

    def create_resource(self, resource_type, **kwargs):
        p = self.client.resource(
            resource_type,
            identifier=self.identifier,
            **kwargs)
        p.save()

        return p

    def test_create_patient(self):
        self.create_resource(
            'Patient',
            id='patient',
            name=[{'text': 'My patient'}])

        patient = self.client.resources('Patient').get('patient')
        self.assertEqual(patient['name'], [{'text': 'My patient'}])

    def test_count(self):
        search_set = self.get_search_set('Patient')

        self.assertEqual(search_set.count(), 0)

        self.create_resource(
            'Patient',
            id='patient1',
            name=[{'text': 'John Smith FHIRPy'}])

        self.assertEqual(search_set.count(), 1)

    def test_create_without_id(self):
        patient = self.create_resource('Patient')

        self.assertIsNotNone(patient.id)

    def test_delete(self):
        patient = self.create_resource('Patient', id='patient')
        patient.delete()

        with self.assertRaises(OperationOutcome):
            self.get_search_set('Patient').get(id='patient')

    def test_get_not_existing_id(self):
        with self.assertRaises(ResourceNotFound):
            self.client.resources('Patient').get(id='FHIRPypy_not_existing_id')

    def test_get_set_bad_attr(self):
        with self.assertRaises(KeyError):
            self.client.resource('Patient', notPatientField='field')

        with self.assertRaises(KeyError):
            patient = self.client.resource('Patient')
            patient['notPatientField'] = 'field'

        with self.assertRaises(KeyError):
            patient = self.client.resource('Patient')
            _ = patient['notPatientField']

    def test_resource_without_resource_type_failed(self):
        with self.assertRaises(TypeError):
            self.client.resource()

    def test_resource_success(self):
        resource = self.client.resource('Patient', id='p1')
        self.assertEqual(resource.resource_type, 'Patient')
        self.assertEqual(resource['resourceType'], 'Patient')
        self.assertEqual(resource.id, 'p1')
        self.assertEqual(resource['id'], 'p1')
        self.assertEqual(resource.reference, 'Patient/p1')
        self.assertDictEqual(
            resource.serialize(),
            {
                'resourceType': 'Patient',
                'id': 'p1',
            }
        )

    def test_reference_from_local_reference(self):
        reference = self.client.reference(reference='Patient/p1')
        self.assertTrue(reference.is_local)
        self.assertEqual(reference.resource_type, 'Patient')
        self.assertEqual(reference.id, 'p1')
        self.assertEqual(reference.reference, 'Patient/p1')
        self.assertEqual(reference['reference'], 'Patient/p1')
        self.assertDictEqual(
            reference.serialize(),
            {
                'reference': 'Patient/p1'
            }
        )

    def test_reference_from_external_reference(self):
        reference = self.client.reference(
            reference='http://external.com/Patient/p1')
        self.assertFalse(reference.is_local)
        self.assertIsNone(reference.resource_type)
        self.assertIsNone(reference.id)
        self.assertEqual(reference.reference, 'http://external.com/Patient/p1')
        self.assertEqual(
            reference['reference'], 'http://external.com/Patient/p1')
        self.assertDictEqual(
            reference.serialize(),
            {
                'reference': 'http://external.com/Patient/p1'
            }
        )

    def test_reference_from_resource_type_and_id(self):
        reference = self.client.reference('Patient', 'p1')
        self.assertEqual(reference.resource_type, 'Patient')
        self.assertEqual(reference.id, 'p1')
        self.assertEqual(reference.reference, 'Patient/p1')
        self.assertEqual(reference['reference'], 'Patient/p1')
        self.assertDictEqual(
            reference.serialize(),
            {
                'reference': 'Patient/p1'
            }
        )

    def test_not_found_error(self):
        with self.assertRaises(ResourceNotFound):
            self.client.resources('FHIRPyNotExistingResource').fetch()

    def test_operation_outcome_error(self):
        with self.assertRaises(OperationOutcome):
            self.create_resource('Patient', name='invalid')

    def test_to_resource_for_local_reference(self):
        self.create_resource(
            'Patient', id='p1', name=[{'text': 'Name'}])

        patient_ref = self.client.reference('Patient', 'p1')
        result = patient_ref.to_resource().serialize()
        result.pop('meta')
        result.pop('identifier')

        self.assertEqual(
            result,
            {'resourceType': 'Patient',
             'id': 'p1',
             'name': [{'text': 'Name'}]})

    def test_to_resource_for_external_reference(self):
        reference = self.client.reference(
            reference='http://external.com/Patient/p1')

        with self.assertRaises(ResourceNotFound):
            reference.to_resource()

    def test_to_resource_for_resource(self):
        resource = self.client.resource(
            'Patient', id='p1', name=[{'text': 'Name'}])
        resource_copy = resource.to_resource()
        self.assertTrue(isinstance(resource_copy, SyncFHIRResource))
        self.assertEqual(
            resource_copy.serialize(),
            {'resourceType': 'Patient',
             'id': 'p1',
             'name': [{'text': 'Name'}]})

    def test_to_reference_for_resource_without_id(self):
        resource = self.client.resource('Patient')
        with self.assertRaises(ResourceNotFound):
            resource.to_reference()

    def test_to_reference_for_resource(self):
        patient = self.create_resource('Patient', id='p1')

        self.assertEqual(
            patient.to_reference().serialize(),
            {'reference': 'Patient/p1'})

        self.assertEqual(
            patient.to_reference(display='patient').serialize(),
            {
                'reference': 'Patient/p1',
                'display': 'patient',
            })

    def test_to_reference_for_reference(self):
        reference = self.client.reference('Patient', 'p1')
        reference_copy = reference.to_reference(display='patient')
        self.assertTrue(isinstance(reference_copy, SyncFHIRReference))
        self.assertEqual(
            reference_copy.serialize(),
            {
                'reference': 'Patient/p1',
                'display': 'patient',
            })

    def test_serialize(self):
        practitioner1 = self.client.resource('Practitioner', id='pr1')
        practitioner2 = self.client.resource('Practitioner', id='pr2')
        patient = self.client.resource(
            'Patient',
            id='patient',
            generalPractitioner=[
                practitioner1.to_reference(display='practitioner'),
                practitioner2])

        self.assertEqual(
            patient.serialize(),
            {
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
            })

    def test_equality(self):
        resource = self.client.resource('Patient', id='p1')
        reference = self.client.reference('Patient', 'p1')
        self.assertEqual(resource, reference)

    def test_bundle_path(self):
        bundle_resource = self.client.resource('Bundle')
        self.assertEqual(bundle_resource._get_path(), '')

    def test_create_bundle(self): 
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
        bundle_resource = self.create_resource('Bundle', **bundle)
        patient_1 = self.client.resources('Patient').get(id='bundle_patient_1')
        patient_2 = self.client.resources('Patient').get(id='bundle_patient_2')

from unittest2 import TestCase
from requests.auth import _basic_auth_str

from fhirpy import SyncFHIRClient
from fhirpy.lib import SyncFHIRReference, SyncFHIRResource
from fhirpy.base.exceptions import ResourceNotFound, OperationOutcome, MultipleResourcesFound


class LibTestCase(TestCase):
    URL = 'http://localhost:8080/fhir'
    client = None
    identifier = [{'system': 'http://example.com/env', 'value': 'fhirpy'}]

    @classmethod
    def get_search_set(cls, resource_type):
        return cls.client.resources(resource_type).search(
            **{'identifier': 'fhirpy'}
        )

    @classmethod
    def clearDb(cls):
        for resource_type in ['Patient', 'Practitioner']:
            search_set = cls.get_search_set(resource_type)
            for item in search_set:
                item.delete()

    @classmethod
    def setUpClass(cls):
        cls.client = SyncFHIRClient(
            cls.URL, authorization=_basic_auth_str('root', 'secret')
        )
        cls.clearDb()

    def tearDown(self):
        self.clearDb()

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
        self.assertEqual(patient['name'], [{'text': 'My patient'}])

    def test_count(self):
        search_set = self.get_search_set('Patient')

        self.assertEqual(search_set.count(), 0)

        self.create_resource(
            'Patient', id='patient1', name=[{
                'text': 'John Smith FHIRPy'
            }]
        )

        self.assertEqual(search_set.count(), 1)

    def test_create_without_id(self):
        patient = self.create_resource('Patient')

        self.assertIsNotNone(patient.id)

    def test_delete(self):
        patient = self.create_resource('Patient', id='patient')
        patient.delete()

        with self.assertRaises(ResourceNotFound):
            self.get_search_set('Patient').search(id='patient').get()

    def test_get_not_existing_id(self):
        with self.assertRaises(ResourceNotFound):
            self.client.resources('Patient') \
                .search(id='FHIRPypy_not_existing_id').get()

    def test_get_more_than_one_resources(self):
        self.create_resource('Patient', birthDate='1901-05-25')
        self.create_resource('Patient', birthDate='1905-05-25')
        with self.assertRaises(MultipleResourcesFound):
            self.client.resources('Patient').get()
        with self.assertRaises(MultipleResourcesFound):
            self.client.resources('Patient') \
                .search(birthdate__gt='1900').get()

    def test_get_resource_by_id_is_deprecated(self):
        self.create_resource('Patient', id='patient', gender='male')
        with self.assertWarns(DeprecationWarning):
            patient = self.client.resources('Patient') \
                .search(gender='male').get(id='patient')
        self.assertEqual(patient.id, 'patient')

    def test_get_resource_by_search_with_id(self):
        self.create_resource('Patient', id='patient', gender='male')
        patient = self.client.resources('Patient') \
            .search(gender='male', id='patient').get()
        self.assertEqual(patient.id, 'patient')
        with self.assertRaises(ResourceNotFound):
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
        self.assertEqual(patient_1.id, 'patient1')
        patient_2 = self.client.resources('Patient') \
            .search(gender='female', birthdate='1905-05-25').get()
        self.assertEqual(patient_2.id, 'patient2')

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
            resource.serialize(), {
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
        self.assertDictEqual(reference.serialize(), {'reference': 'Patient/p1'})

    def test_reference_from_external_reference(self):
        reference = self.client.reference(
            reference='http://external.com/Patient/p1'
        )
        self.assertFalse(reference.is_local)
        self.assertIsNone(reference.resource_type)
        self.assertIsNone(reference.id)
        self.assertEqual(reference.reference, 'http://external.com/Patient/p1')
        self.assertEqual(
            reference['reference'], 'http://external.com/Patient/p1'
        )
        self.assertDictEqual(
            reference.serialize(),
            {'reference': 'http://external.com/Patient/p1'}
        )

    def test_reference_from_resource_type_and_id(self):
        reference = self.client.reference('Patient', 'p1')
        self.assertEqual(reference.resource_type, 'Patient')
        self.assertEqual(reference.id, 'p1')
        self.assertEqual(reference.reference, 'Patient/p1')
        self.assertEqual(reference['reference'], 'Patient/p1')
        self.assertDictEqual(reference.serialize(), {'reference': 'Patient/p1'})

    def test_not_found_error(self):
        with self.assertRaises(ResourceNotFound):
            self.client.resources('FHIRPyNotExistingResource').fetch()

    def test_operation_outcome_error(self):
        with self.assertRaises(OperationOutcome):
            self.create_resource('Patient', name='invalid')

    def test_to_resource_for_local_reference(self):
        self.create_resource('Patient', id='p1', name=[{'text': 'Name'}])

        patient_ref = self.client.reference('Patient', 'p1')
        result = patient_ref.to_resource().serialize()
        result.pop('meta')
        result.pop('identifier')

        self.assertEqual(
            result, {
                'resourceType': 'Patient',
                'id': 'p1',
                'name': [{
                    'text': 'Name'
                }]
            }
        )

    def test_to_resource_for_external_reference(self):
        reference = self.client.reference(
            reference='http://external.com/Patient/p1'
        )

        with self.assertRaises(ResourceNotFound):
            reference.to_resource()

    def test_to_resource_for_resource(self):
        resource = self.client.resource(
            'Patient', id='p1', name=[{
                'text': 'Name'
            }]
        )
        resource_copy = resource.to_resource()
        self.assertTrue(isinstance(resource_copy, SyncFHIRResource))
        self.assertEqual(
            resource_copy.serialize(), {
                'resourceType': 'Patient',
                'id': 'p1',
                'name': [{
                    'text': 'Name'
                }]
            }
        )

    def test_to_reference_for_resource_without_id(self):
        resource = self.client.resource('Patient')
        with self.assertRaises(ResourceNotFound):
            resource.to_reference()

    def test_to_reference_for_resource(self):
        patient = self.create_resource('Patient', id='p1')

        self.assertEqual(
            patient.to_reference().serialize(), {'reference': 'Patient/p1'}
        )

        self.assertEqual(
            patient.to_reference(display='patient').serialize(), {
                'reference': 'Patient/p1',
                'display': 'patient',
            }
        )

    def test_to_reference_for_reference(self):
        reference = self.client.reference('Patient', 'p1')
        reference_copy = reference.to_reference(display='patient')
        self.assertTrue(isinstance(reference_copy, SyncFHIRReference))
        self.assertEqual(
            reference_copy.serialize(), {
                'reference': 'Patient/p1',
                'display': 'patient',
            }
        )

    def test_serialize(self):
        practitioner1 = self.client.resource('Practitioner', id='pr1')
        practitioner2 = self.client.resource('Practitioner', id='pr2')
        patient = self.client.resource(
            'Patient',
            id='patient',
            generalPractitioner=[
                practitioner1.to_reference(display='practitioner'),
                practitioner2
            ]
        )

        self.assertEqual(
            patient.serialize(), {
                'resourceType':
                    'Patient',
                'id':
                    'patient',
                'generalPractitioner':
                    [
                        {
                            'reference': 'Practitioner/pr1',
                            'display': 'practitioner',
                        },
                        {
                            'reference': 'Practitioner/pr2',
                        },
                    ],
            }
        )

    def test_equality(self):
        resource = self.client.resource('Patient', id='p1')
        reference = self.client.reference('Patient', 'p1')
        self.assertEqual(resource, reference)

    def test_bundle_path(self):
        bundle_resource = self.client.resource('Bundle')
        self.assertEqual(bundle_resource._get_path(), '')

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
        bundle_resource = self.create_resource('Bundle', **bundle)
        patient_1 = self.client.resources('Patient').search(
            id='bundle_patient_1'
        ).get()
        patient_2 = self.client.resources('Patient').search(
            id='bundle_patient_2'
        ).get()

    def test_is_valid(self):
        self.assertTrue(self.client.resource('Patient', id='id123').is_valid())
        self.assertTrue(
            self.client.resource('Patient', gender='female').is_valid(
                raise_exception=True
            )
        )

        self.assertFalse(
            self.client.resource('Patient', gender=True).is_valid()
        )
        with self.assertRaises(OperationOutcome):
            self.client.resource('Patient', gender=True) \
                .is_valid(raise_exception=True)

        self.assertFalse(
            self.client.resource('Patient', gender='female',
                                 custom_prop='123').is_valid()
        )
        with self.assertRaises(OperationOutcome):
            self.client.resource('Patient', gender='female', custom_prop='123') \
                .is_valid(raise_exception=True)

        self.assertFalse(
            self.client.resource('Patient', gender='female',
                                 custom_prop='123').is_valid()
        )
        with self.assertRaises(OperationOutcome):
            self.client.resource('Patient', birthDate='date', custom_prop='123', telecom=True) \
                .is_valid(raise_exception=True)

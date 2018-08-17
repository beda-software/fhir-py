from unittest2 import TestCase

from fhirpy import FHIRClient

from fhirpy.exceptions import (FHIRResourceNotFound, FHIROperationOutcome)


class LibTestCase(TestCase):
    URL = 'https://jupyterdemo.aidbox.app/fhir'
    AUTHORIZATION = ''
    client = None

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
        cls.client = FHIRClient(cls.URL, cls.AUTHORIZATION, without_cache=True)
        cls.clearDb()

    def tearDown(self):
        self.clearDb()

    def create_resource(self, resource_type, **kwargs):
        p = self.client.resource(
            resource_type,
            identifier=[{'system': 'http://example.com/env',
                         'value': 'fhirpy'}],
            **kwargs)
        p.save()

        return p

    def test_new_patient_entry(self):
        self.create_resource(
            'Patient',
            id='FHIRPy_patient',
            name=[{'text': 'My patient'}])

        patient = self.client.resources('Patient').get('FHIRPy_patient')
        self.assertEqual(patient['name'], [{'text': 'My patient'}])

    def test_patients_search(self):
        search_set = self.get_search_set('Patient')

        self.create_resource(
            'Patient',
            id='FHIRPy_patient1',
            name=[{'text': 'John Smith FHIRPy'}])
        self.create_resource(
            'Patient',
            id='FHIRPy_patient2',
            name=[{'text': 'John Gold FHIRPy'}])
        self.create_resource(
            'Patient',
            id='FHIRPy_patient3',
            name=[{'text': 'Polumna Gold FHIRPy'}])

        # Test search
        patients = search_set.search(name='john').execute()
        self.assertSetEqual(
            set([p.id for p in patients]),
            {'FHIRPy_patient1', 'FHIRPy_patient2'}
        )

        # Test search with AND composition
        patients = search_set.search(name='john').search(name='gold').execute()

        self.assertSetEqual(
            set([p.id for p in patients]),
            {'FHIRPy_patient2'}
        )

        patients = search_set.search(name=['john', 'gold']).execute()
        self.assertSetEqual(
            set([p.id for p in patients]),
            {'FHIRPy_patient2'}
        )

        # Test search with OR composition
        patients = search_set.search(name='smith,polumna').execute()

        self.assertSetEqual(
            set([p.id for p in patients]),
            {'FHIRPy_patient1', 'FHIRPy_patient3'}
        )

        # Test sort
        patient = search_set.sort('-name').first()
        self.assertEqual(patient.id, 'FHIRPy_patient3')

        # Test count
        self.assertEqual(search_set.count(), 3)

        # Test limit and page and iter (by calling list)
        patients = list(search_set.limit(1).page(2))
        self.assertEqual(len(patients), 1)
        self.assertEqual(patients[0].id, 'FHIRPy_patient3')

    def test_create_without_id(self):
        patient = self.create_resource('Patient')

        self.assertIsNotNone(patient.id)

    def test_delete(self):
        patient = self.create_resource('Patient', id='FHIRPy_patient')
        patient.delete()

        with self.assertRaises(FHIROperationOutcome):
            self.get_search_set('Patient').get(id='FHIRPy_patient')

    def test_get_not_existing_id(self):
        with self.assertRaises(FHIRResourceNotFound):
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

    def test_reference(self):
        reference = self.client.reference('Patient', 'FHIRPy_patient_1')
        self.assertDictEqual(
            reference.serialize(),
            {
                'reference': 'Patient/FHIRPy_patient_1'
            }
        )

    def test_not_found_error(self):
        with self.assertRaises(FHIRResourceNotFound):
            self.client.resources('FHIRPyNotExistingResource').execute()

    def test_operation_outcome_error(self):
        with self.assertRaises(FHIROperationOutcome):
            self.create_resource('Patient', name='invalid')

    def test_save_with_reference(self):
        practitioner1 = self.create_resource('Practitioner', id='FHIRPy_pr1')
        practitioner2 = self.create_resource('Practitioner', id='FHIRPy_pr2')
        self.create_resource(
            'Patient',
            id='FHIRPy_patient',
            generalPractitioner=[
                practitioner1.to_reference(display='practitioner'),
                practitioner2])

        patient = self.client.resources('Patient').get(id='FHIRPy_patient')
        self.assertEqual(patient['generalPractitioner'][0], practitioner1)
        self.assertEqual(patient['generalPractitioner'][0]['display'],
                         'practitioner')
        self.assertEqual(patient['generalPractitioner'][1], practitioner2)

    def test_to_reference(self):
        patient = self.create_resource('Patient', id='FHIRPy_patient')

        self.assertEqual(
            patient.to_reference().serialize(),
            {'reference': 'Patient/FHIRPy_patient'})

        self.assertEqual(
            patient.to_reference(display='Patient').serialize(),
            {
                'reference': 'Patient/FHIRPy_patient',
                'display': 'Patient',
            })

    def test_to_resource(self):
        self.create_resource(
            'Patient', id='FHIRPy_patient', name=[{'text': 'Name'}])

        patient_ref = self.client.reference('Patient', 'FHIRPy_patient')
        result = patient_ref.to_resource().serialize()
        result.pop('meta')
        result.pop('identifier')

        self.assertEqual(
            result,
            {'resourceType': 'Patient',
             'id': 'FHIRPy_patient',
             'name': [{'text': 'Name'}]})

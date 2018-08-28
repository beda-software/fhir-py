from unittest2 import TestCase

from fhirpy import FHIRClient
from fhirpy.lib import load_schema, FHIRReference, FHIRResource

from fhirpy.exceptions import (FHIRResourceNotFound, FHIROperationOutcome,
                               FHIRNotSupportedVersionError)


class LibTestCase(TestCase):
    URL = 'https://jupyterdemo.aidbox.app/fhir'
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
        cls.client = FHIRClient(cls.URL)
        cls.clearDb()

    def tearDown(self):
        self.client.clear_resources_cache()
        self.clearDb()

    def test_load_schema_for_invalid_version_failed(self):
        with self.assertRaises(FHIRNotSupportedVersionError):
            load_schema('invalid')

    def create_resource(self, resource_type, **kwargs):
        p = self.client.resource(
            resource_type,
            identifier=[{'system': 'http://example.com/env',
                         'value': 'fhirpy'}],
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

        with self.assertRaises(FHIROperationOutcome):
            self.get_search_set('Patient').get(id='patient')

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

    def test_reference_from_external_reference_2(self):
        reference = self.client.reference(
            reference='notfhirresource/n1')
        self.assertFalse(reference.is_local)
        self.assertIsNone(reference.resource_type)
        self.assertIsNone(reference.id)
        self.assertEqual(reference.reference, 'notfhirresource/n1')
        self.assertEqual(
            reference['reference'], 'notfhirresource/n1')
        self.assertDictEqual(
            reference.serialize(),
            {
                'reference': 'notfhirresource/n1'
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
        with self.assertRaises(FHIRResourceNotFound):
            self.client.resources('FHIRPyNotExistingResource').fetch()

    def test_operation_outcome_error(self):
        with self.assertRaises(FHIROperationOutcome):
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

        with self.assertRaises(FHIRResourceNotFound):
            reference.to_resource()

    def test_to_resource_for_resource(self):
        resource = self.client.resource(
            'Patient', id='p1', name=[{'text': 'Name'}])
        resource_copy = resource.to_resource()
        self.assertTrue(isinstance(resource_copy, FHIRResource))
        self.assertEqual(
            resource_copy.serialize(),
            {'resourceType': 'Patient',
             'id': 'p1',
             'name': [{'text': 'Name'}]})

    def test_to_reference_for_resource_without_id(self):
        resource = self.client.resource('Patient')
        with self.assertRaises(FHIRResourceNotFound):
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
        self.assertTrue(isinstance(reference_copy, FHIRReference))
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


class SearchSetTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = FHIRClient('mock')

    def test_search(self):
        search_set = self.client.resources('Patient') \
            .search(name='John,Ivan') \
            .search(name='Smith') \
            .search(birth_date='2010-01-01')
        self.assertEqual(
            search_set.params,
            {'name': ['John,Ivan', 'Smith'],
             'birth_date': ['2010-01-01']}
        )

    def test_sort(self):
        search_set = self.client.resources('Patient') \
            .sort('id').sort('deceased')
        self.assertEqual(
            search_set.params,
            {'_sort': ['deceased']}
        )

    def test_page(self):
        search_set = self.client.resources('Patient') \
            .page(1).page(2)
        self.assertEqual(
            search_set.params,
            {'_page': [2]}
        )

    def test_limit(self):
        search_set = self.client.resources('Patient') \
            .limit(1).limit(2)
        self.assertEqual(
            search_set.params,
            {'_count': [2]}
        )

    def test_elements(self):
        search_set = self.client.resources('Patient') \
            .elements('deceased').elements('gender')

        self.assertEqual(set(search_set.params.keys()), {'_elements'})
        self.assertEqual(len(search_set.params['_elements']), 1)
        self.assertSetEqual(
            set(search_set.params['_elements'][0].split(',')),
            {'id', 'resourceType', 'gender'})

    def test_elements_exclude(self):
        search_set = self.client.resources('Patient') \
            .elements('name', exclude=True)
        self.assertEqual(
            search_set.params,
            {'_elements': ['-name']}
        )

    def test_include(self):
        search_set = self.client.resources('Patient') \
            .include('Patient', 'general-practitioner')
        self.assertEqual(
            search_set.params,
            {'_include': ['Patient:general-practitioner']}
        )

    def test_include_multiple(self):
        search_set = self.client.resources('Orginaztion') \
            .include('Patient', 'general-practitioner') \
            .include('Patient', 'organization')

        self.assertEqual(
            search_set.params,
            {'_include': ['Patient:general-practitioner',
                          'Patient:organization']}
        )

    def test_include_with_target(self):
        search_set = self.client.resources('Patient') \
            .include('Patient', 'general-practitioner', 'Organization')
        self.assertEqual(
            search_set.params,
            {'_include': ['Patient:general-practitioner:Organization']}
        )

    def test_include_recursive(self):
        search_set = self.client.resources('Patient') \
            .include('Organization', 'partof', recursive=True)
        self.assertEqual(
            search_set.params,
            {'_include:recursive': ['Organization:partof']}
        )

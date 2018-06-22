from unittest2 import TestCase

from aidbox import Aidbox

from aidbox.exceptions import AidboxResourceFieldDoesNotExist, \
    AidboxResourceNotFound, AidboxAuthorizationError, AidboxOperationOutcome


class LibTestCase(TestCase):
    HOST = 'https://sansara.health-samurai.io'
    TOKEN = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJnaXZlbl9uYW1lIjpudWx' \
            'sLCJiaXJ0aGRhdGUiOm51bGwsImVtYWlsIjoicGF0aWVudEBjb20uY29tIiwi' \
            'em9uZWluZm8iOm51bGwsImxvY2FsZSI6bnVsbCwic3ViIjoicGF0aWVudCIsI' \
            'nBob25lIjpudWxsLCJuYW1lIjpudWxsLCJuaWNrbmFtZSI6bnVsbCwidXNlci' \
            '1pZCI6InBhdGllbnQiLCJtaWRkbGVfbmFtZSI6bnVsbCwiZmFtaWx5X25hbWU' \
            'iOm51bGwsInVwZGF0ZWRfYXQiOm51bGwsInBpY3R1cmUiOm51bGwsIndlYnNp' \
            'dGUiOm51bGwsImdlbmRlciI6bnVsbCwicHJlZmVycmVkX3VzZXJuYW1lIjpud' \
            'WxsLCJwcm9maWxlIjpudWxsfQ.ThigRLqfAc-xY9RHy75cI-Wh9s0y6dcRT_m' \
            'SPRon4aOAsFL2BMkhGiLRjkDDRQa-e_BRDzSLgi84aB3q8atwTMSs9fYL79Az' \
            'rNU3dgv9nyyjNy7BzRY_OYeTR3TBdEUklTnNABXiis0pS4JOw1JcDT0xpxtB2' \
            'qBPpT7odPyVlHbjKWRINIqE2iAkTFOY_8UYCA-WU3qGEHDUdWFnav42aiDfcZ' \
            'Na2yBpytv7n8qqj70nCfXu49ShcT86eQ4vQsafNgfttRE1CbzqGVHS3Lv-nX2' \
            '5GSh_DJ_qITDC4Uk_KoMtGLzjW1LqvgRLWydEVbluj4SKlx1oYD07Yu6nCJcw2A'
    ab = None

    @classmethod
    def get_search_set(cls, resource_type):
        return cls.ab.resources(resource_type).search(**{
            'identifier': 'aidboxpy'
        })

    @classmethod
    def clearDb(cls):
        for resource_type in ['Patient', 'Practitioner']:
            search_set = cls.get_search_set(resource_type)
            for item in search_set:
                item.delete()

    @classmethod
    def setUpClass(cls):
        cls.ab = Aidbox(cls.HOST, cls.TOKEN)
        cls.clearDb()

    def tearDown(self):
        self.clearDb()

    def create_resource(self, resource_type, **kwargs):
        p = self.ab.resource(
            resource_type,
            identifier=[{'system': 'http://example.com/env',
                         'value': 'aidboxpy'}],
            **kwargs)
        p.save()

        return p

    def test_new_patient_entry(self):
        self.create_resource(
            'Patient',
            id='AidboxPy_patient',
            name=[{'text': 'My patient'}])

        patient = self.ab.resources('Patient').get('AidboxPy_patient')
        self.assertEqual(patient.name, [{'text': 'My patient'}])

    def test_patients_search(self):
        search_set = self.get_search_set('Patient')

        self.create_resource(
            'Patient',
            id='AidboxPy_patient1',
            name=[{'text': 'John Smith AidboxPy'}])
        self.create_resource(
            'Patient',
            id='AidboxPy_patient2',
            name=[{'text': 'John Gold AidboxPy'}])
        self.create_resource(
            'Patient',
            id='AidboxPy_patient3',
            name=[{'text': 'Polumna Gold AidboxPy'}])

        # Test search
        patients = search_set.search(name='john').execute()

        self.assertSetEqual(
            set([p.id for p in patients]),
            {'AidboxPy_patient1', 'AidboxPy_patient2'}
        )

        # Test search with AND composition
        patients = search_set.search(name='john').search(name='gold').execute()

        self.assertSetEqual(
            set([p.id for p in patients]),
            {'AidboxPy_patient2'}
        )

        patients = search_set.search(name=['john', 'gold']).execute()
        self.assertSetEqual(
            set([p.id for p in patients]),
            {'AidboxPy_patient2'}
        )

        # Test search with OR composition
        patients = search_set.search(name='smith,polumna').execute()

        self.assertSetEqual(
            set([p.id for p in patients]),
            {'AidboxPy_patient1', 'AidboxPy_patient3'}
        )

        # Test sort
        patient = search_set.sort('-name').first()
        self.assertEqual(patient.id, 'AidboxPy_patient3')

        # Test count
        self.assertEqual(search_set.count(), 3)

        # Test limit and page and iter (by calling list)
        patients = list(search_set.limit(1).page(2))
        self.assertEqual(len(patients), 1)
        self.assertEqual(patients[0].id, 'AidboxPy_patient3')

    def test_create_without_id(self):
        patient = self.create_resource('Patient')

        self.assertIsNotNone(patient.id)

    def test_delete(self):
        patient = self.create_resource('Patient', id='AidboxPy_patient')
        patient.delete()

        with self.assertRaises(AidboxResourceNotFound):
            self.get_search_set('Patient').get(id='AidboxPy_patient')

    def test_get_not_existing_id(self):
        with self.assertRaises(AidboxResourceNotFound):
            self.ab.resources('Patient').get(id='aidboxpy_not_existing_id')

    def test_get_set_bad_attr(self):
        with self.assertRaises(AidboxResourceFieldDoesNotExist):
            self.ab.resource('Patient', not_patient_field='field')

        with self.assertRaises(AidboxResourceFieldDoesNotExist):
            patient = self.ab.resource('Patient')
            patient.not_patient_field = 'field'

        with self.assertRaises(AidboxResourceFieldDoesNotExist):
            patient = self.ab.resource('Patient')
            _ = patient.not_patient_field

    def test_reference(self):
        reference = self.ab.reference('Patient', 'aidbox_patient_1')
        self.assertDictEqual(
            reference.to_dict(),
            {
                'id': 'aidbox_patient_1',
                'resource_type': 'Patient'
            }
        )

    def test_not_found_error(self):
        with self.assertRaises(AidboxResourceNotFound):
            self.ab.resources('AidboxPyNotExistingResource').execute()

    def test_operation_outcome_error(self):
        with self.assertRaises(AidboxOperationOutcome):
            self.create_resource('Patient', name='invalid')

    def test_invalid_token_access(self):
        with self.assertRaises(AidboxAuthorizationError):
            Aidbox.obtain_token(self.HOST, 'fake@fake.com', 'fakepass')

    def test_save_with_reference(self):
        practitioner1 = self.create_resource('Practitioner', id='AidboxPy_pr1')
        practitioner2 = self.create_resource('Practitioner', id='AidboxPy_pr2')
        self.create_resource(
            'Patient',
            id='AidboxPy_patient',
            general_practitioner=[practitioner1.to_reference(
                display='practitioner'), practitioner2])

        patient = self.ab.resources('Patient').get(id='AidboxPy_patient')
        self.assertEqual(patient.general_practitioner[0], practitioner1)
        self.assertEqual(patient.general_practitioner[0].display,
                         'practitioner')
        self.assertEqual(patient.general_practitioner[1], practitioner2)

    def test_to_reference(self):
        patient = self.create_resource('Patient', id='AidboxPy_patient')

        self.assertEqual(
            patient.to_reference().to_dict(),
            {'resource_type': 'Patient',
             'id': 'AidboxPy_patient'})

        self.assertEqual(
            patient.to_reference(display='Patient').to_dict(),
            {'resource_type': 'Patient',
             'display': 'Patient',
             'id': 'AidboxPy_patient'})

    def test_to_resource(self):
        self.create_resource(
            'Patient', id='AidboxPy_patient', name=[{'text': 'Name'}])

        patient_ref = self.ab.reference('Patient', 'AidboxPy_patient')

        self.assertEqual(
            patient_ref.to_resource().to_dict(),
            {'resource_type': 'Patient',
             'id': 'AidboxPy_patient',
             'identifier': [{'system': 'http://example.com/env',
                             'value': 'aidboxpy'}],
             'name': [{'text': 'Name'}]})

    def test_empty_reference(self):
        with self.assertRaises(AttributeError):
            self.ab.reference()

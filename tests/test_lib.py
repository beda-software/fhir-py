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
    def setUpClass(cls):
        cls.ab = Aidbox(cls.HOST, cls.TOKEN)

    def test_new_patient_entry(self):
        patient = self.ab.resource('Patient', id='AidboxPy_test_patient')
        patient.name = [{'text': 'My patient'}]
        patient.save()

        patient = self.ab.resources('Patient').get('AidboxPy_test_patient')
        self.assertEqual(patient.name, [{'text': 'My patient'}])

        patient.delete()

    def test_patients_search(self):
        search_set = self.ab.resources('Patient').search(**{
            'name:contains': 'AidboxPy'
        })

        patient = self.ab.resource('Patient', id='AidboxPy_test_patient1')
        patient.name = [{'text': 'John Smith AidboxPy'}]
        patient.save()

        patient2 = self.ab.resource('Patient', id='AidboxPy_test_patient2')
        patient2.name = [{'text': 'John Gold AidboxPy'}]
        patient2.save()

        patient3 = self.ab.resource('Patient', id='AidboxPy_test_patient3')
        patient3.name = [{'text': 'Polumna Gold AidboxPy'}]
        patient3.save()

        # Test search
        patients = search_set.search(name='john').execute()

        self.assertSetEqual(
            set([p.id for p in patients]),
            {'AidboxPy_test_patient1', 'AidboxPy_test_patient2'}
        )

        # Test search with AND composition
        patients = search_set.search(name='john').search(name='gold').execute()

        self.assertSetEqual(
            set([p.id for p in patients]),
            {'AidboxPy_test_patient2'}
        )

        patients = search_set.search(name=['john', 'gold']).execute()
        self.assertSetEqual(
            set([p.id for p in patients]),
            {'AidboxPy_test_patient2'}
        )

        # Test search with OR composition
        patients = search_set.search(name='smith,polumna').execute()

        self.assertSetEqual(
            set([p.id for p in patients]),
            {'AidboxPy_test_patient1', 'AidboxPy_test_patient3'}
        )

        # Test sort
        patient = search_set.sort('-name').first()
        self.assertEqual(patient.id, 'AidboxPy_test_patient3')

        # Test count
        self.assertEqual(search_set.count(), 3)

        # Test limit and page and iter (by calling list)
        patients = list(search_set.limit(1).page(2))
        self.assertEqual(len(patients), 1)
        self.assertEqual(patients[0].id, 'AidboxPy_test_patient3')

        search_set.get('AidboxPy_test_patient1').delete()
        search_set.get('AidboxPy_test_patient2').delete()
        search_set.get('AidboxPy_test_patient3').delete()

        self.assertEqual(search_set.count(), 0)

    def test_create_without_id(self):
        patient = self.ab.resource('Patient')
        patient.name = [{'text': 'John Smith'}]
        patient.save()

        patient.delete()

    def test_get_nonexistent_id(self):
        with self.assertRaises(AidboxResourceNotFound):
            self.ab.resources('Patient').get(id='aidboxpy_not_existent_id')

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
        patient = self.ab.resource('Patient', id='aidbox_patient_1')
        with self.assertRaises(AidboxOperationOutcome):
            patient.name = 'invalid value'
            patient.save()

        patient.delete()

    def test_invalid_token_access(self):
        with self.assertRaises(AidboxAuthorizationError):
            Aidbox.obtain_token(self.HOST, 'fake@fake.com', 'fakepass')

    def test_save_with_reference(self):
        practitioner1 = self.ab.resource('Practitioner', id='AidboxPy_test_pr1')
        practitioner1.save()
        practitioner2 = self.ab.resource('Practitioner', id='AidboxPy_test_pr2')
        practitioner2.save()
        patient = self.ab.resource(
            'Patient',
            id='AidboxPy_test_patient',
            general_practitioner=[practitioner1.to_reference(
                display='practitioner'), practitioner2])
        patient.save()

        patient = self.ab.resources('Patient').get(id='AidboxPy_test_patient')
        self.assertEqual(patient.general_practitioner[0], practitioner1)
        self.assertEqual(patient.general_practitioner[0].display,
                         'practitioner')
        self.assertEqual(patient.general_practitioner[1], practitioner2)

        patient.delete()
        practitioner1.delete()
        practitioner2.delete()

    def test_to_reference(self):
        patient = self.ab.resource('Patient', id='AidboxPy_test_patient')
        patient.save()

        self.assertEqual(
            patient.to_reference().to_dict(),
            {'resource_type': 'Patient',
             'id': 'AidboxPy_test_patient'})


        self.assertEqual(
            patient.to_reference(display='Patient').to_dict(),
            {'resource_type': 'Patient',
             'display': 'Patient',
             'id': 'AidboxPy_test_patient'})

        patient.delete()

    def test_to_resource(self):
        patient = self.ab.resource(
            'Patient', id='AidboxPy_test_patient', name=[{'text': 'Name'}])
        patient.save()

        patient_ref = self.ab.reference('Patient', 'AidboxPy_test_patient')

        self.assertEqual(
            patient_ref.to_resource().to_dict(),
            {'resource_type': 'Patient',
             'id': 'AidboxPy_test_patient',
             'name': [{'text': 'Name'}]})

        patient.delete()

    def test_empty_reference(self):
        with self.assertRaises(AttributeError):
            self.ab.reference()

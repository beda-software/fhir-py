from unittest2 import TestCase

from aidbox import Aidbox
from aidbox.exceptions import AidboxResourceFieldDoesNotExist


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

        # Test limit and page
        patients = search_set.limit(1).page(2).execute()
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

        patient.__repr__()
        patient.__str__()

        patient.delete()

    def test_get_set_bad_attr(self):
        with self.assertRaises(AidboxResourceFieldDoesNotExist):
            self.ab.resource('Patient', not_patient_field='field')

        self.ab.resource('Patient',
                         not_patient_field='field',
                         skip_validation=True)

        with self.assertRaises(AidboxResourceFieldDoesNotExist):
            patient = self.ab.resource('Patient')
            patient.not_patient_field = 'field'

    def test_reference(self):
        reference = self.ab.reference('Patient', 'aidbox_patient_1')
        reference.__repr__()
        reference.__str__()
        self.assertDictEqual(
            reference.to_dict(),
            {
                'id': 'aidbox_patient_1',
                'resource_type': 'Patient'
            }
        )

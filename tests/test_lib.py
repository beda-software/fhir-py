from unittest2 import TestCase

from aidbox import Aidbox


class LibTestCase(TestCase):
    HOST = 'https://sansara.health-samurai.io'
    TOKEN = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJnaXZlbl9uYW1lIjpudWxsLCJiaXJ0aGRhdGUiOm51bGwsImVtYWlsIjoicGF0aWVudEBjb20uY29tIiwiem9uZWluZm8iOm51bGwsImxvY2FsZSI6bnVsbCwic3ViIjoicGF0aWVudCIsInBob25lIjpudWxsLCJuYW1lIjpudWxsLCJuaWNrbmFtZSI6bnVsbCwidXNlci1pZCI6InBhdGllbnQiLCJtaWRkbGVfbmFtZSI6bnVsbCwiZmFtaWx5X25hbWUiOm51bGwsInVwZGF0ZWRfYXQiOm51bGwsInBpY3R1cmUiOm51bGwsIndlYnNpdGUiOm51bGwsImdlbmRlciI6bnVsbCwicHJlZmVycmVkX3VzZXJuYW1lIjpudWxsLCJwcm9maWxlIjpudWxsfQ.ThigRLqfAc-xY9RHy75cI-Wh9s0y6dcRT_mSPRon4aOAsFL2BMkhGiLRjkDDRQa-e_BRDzSLgi84aB3q8atwTMSs9fYL79AzrNU3dgv9nyyjNy7BzRY_OYeTR3TBdEUklTnNABXiis0pS4JOw1JcDT0xpxtB2qBPpT7odPyVlHbjKWRINIqE2iAkTFOY_8UYCA-WU3qGEHDUdWFnav42aiDfcZNa2yBpytv7n8qqj70nCfXu49ShcT86eQ4vQsafNgfttRE1CbzqGVHS3Lv-nX25GSh_DJ_qITDC4Uk_KoMtGLzjW1LqvgRLWydEVbluj4SKlx1oYD07Yu6nCJcw2A'
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

        patient = self.ab.resource('Patient', id='AidboxPy_test_patient')
        patient.name = [{'text': 'John Smith AidboxPy'}]
        patient.save()

        patient2 = self.ab.resource('Patient', id='AidboxPy_test_patient2')
        patient2.name = [{'text': 'John Gold AidboxPy'}]
        patient2.save()

        patient3 = self.ab.resource('Patient', id='AidboxPy_test_patient3')
        patient3.name = [{'text': 'Polumna Lavgud AidboxPy'}]
        patient3.save()

        # Test search
        patients = search_set.search(name='john').execute()

        self.assertSetEqual(
            set([p.id for p in patients]),
            {'AidboxPy_test_patient', 'AidboxPy_test_patient2'}
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

        search_set.get('AidboxPy_test_patient').delete()
        search_set.get('AidboxPy_test_patient2').delete()
        search_set.get('AidboxPy_test_patient3').delete()

        self.assertEqual(search_set.count(), 0)

    # def test_create_without_id(self):
    #     patient = self.ab.resource('Patient')
    #     patient.name = [{'text': 'John Smith'}]
    #     patient.save()


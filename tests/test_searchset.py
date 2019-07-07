import pytest
from fhirpy import SyncFHIRClient, AsyncFHIRClient


@pytest.mark.parametrize('client', [SyncFHIRClient('mock'), AsyncFHIRClient('mock')])
class TestSearchSet(object):

    def test_search(self, client):
        search_set = client.resources('Patient') \
            .search(name='John,Ivan') \
            .search(name='Smith') \
            .search(birth_date='2010-01-01')
        assert search_set.params == {
            'name': ['John,Ivan', 'Smith'],
            'birth_date': ['2010-01-01']
        }

    def test_sort(self, client):
        search_set = client.resources('Patient') \
            .sort('id').sort('deceased')
        assert search_set.params == {'_sort': ['deceased']}

    def test_page(self, client):
        search_set = client.resources('Patient') \
            .page(1).page(2)
        assert search_set.params == {'page': [2]}

    def test_limit(self, client):
        search_set = client.resources('Patient') \
            .limit(1).limit(2)
        assert search_set.params == {'_count': [2]}

    def test_elements(self, client):
        search_set = client.resources('Patient') \
            .elements('deceased').elements('gender')

        assert set(search_set.params.keys()) == {'_elements'}
        assert len(search_set.params['_elements']) == 1
        assert set(search_set.params['_elements'][0].split(',')) == {
            'id', 'resourceType', 'gender'
        }

    def test_elements_exclude(self, client):
        search_set = client.resources('Patient') \
            .elements('name', exclude=True)
        assert search_set.params == {'_elements': ['-name']}

    def test_include(self, client):
        search_set = client.resources('Patient') \
            .include('Patient', 'general-practitioner')
        assert search_set.params == {
            '_include': ['Patient:general-practitioner']
        }

    def test_has(self, client):
        search_set = client.resources('Patient') \
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

    def test_has_failed(self, client):
        with pytest.raises(TypeError):
            client.resources('Patient').has('Observation',code='code')

    def test_include_multiple(self, client):
        search_set = client.resources('Orginaztion') \
            .include('Patient', 'general-practitioner') \
            .include('Patient', 'organization')

        assert search_set.params == {
            '_include': ['Patient:general-practitioner',
                         'Patient:organization']
        }

    def test_include_with_target(self, client):
        search_set = client.resources('Patient') \
            .include('Patient', 'general-practitioner', 'Organization')
        assert search_set.params == {
            '_include': ['Patient:general-practitioner:Organization']
        }

    def test_include_recursive(self, client):
        search_set = client.resources('Patient') \
            .include('Organization', 'partof', recursive=True)
        assert search_set.params == {
            '_include:recursive': ['Organization:partof']
        }

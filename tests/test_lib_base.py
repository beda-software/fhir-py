import pytest
from fhirpy import SyncFHIRClient, AsyncFHIRClient
from fhirpy.base.utils import AttrDict, SearchList


@pytest.mark.parametrize(
    'client',
    [SyncFHIRClient('mock'), AsyncFHIRClient('mock')]
)
class TestLibBase(object):
    def test_reference_is_not_provided_failed(self, client):
        with pytest.raises(TypeError):
            client.reference()

    def test_get_by_path(self, client):
        resource = client.resource(
            'Patient', **{
                'id':
                    'patient',
                'name': [{
                    'given': ['Firstname'],
                    'family': 'Lastname'
                }],
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
        assert resource.get_by_path(
            [
                'generalPractitioner', {
                    'reference': 'Practitioner/pr1'
                }, 'display'
            ]
        ) == 'practitioner'
        assert resource.get_by_path(
            ['generalPractitioner', {
                'reference': 'Practitioner/100'
            }]
        ) is None
        assert resource.get_by_path(
            [
                'generalPractitioner', {
                    'reference': 'Practitioner/pr2'
                }, 'display'
            ], 'practitioner2'
        ) == 'practitioner2'
        assert resource.get_by_path(
            ['generalPractitioner', 1, 'reference'], 'Practitioner/pr_test'
        ) == 'Practitioner/pr2'
        assert resource.get_by_path(
            ['generalPractitioner', 2, 'reference']
        ) is None
        names = resource.name
        assert isinstance(names, SearchList)
        assert names.get_by_path([0, 'given', 0]) == 'Firstname'
        name = names[0]
        assert isinstance(name, AttrDict)
        assert name.get_by_path(['given', 0]) == 'Firstname'

    def test_set_resource_setdefault(self, client):
        resource = client.resource('Patient', id='patient')
        resource.setdefault('id', 'new_patient')
        assert resource.id == 'patient'
        resource.setdefault('active', True)
        assert resource.active is True

    # def test_set_resource_type_failed(self, client):
    #     resource = client.resource('Patient')
    #     with pytest.raises(KeyError):
    #         resource['resourceType'] = 'Practitioner'

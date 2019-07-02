import pickle
from os.path import dirname

from .base import Client, SearchSet, Resource, Reference


class FHIRSearchSet(SearchSet):
    pass


class FHIRResource(Resource):
    def is_reference(self, value):
        if not isinstance(value, dict):
            return False

        return 'reference' in value and \
               not (set(value.keys()) - {'reference', 'display'})

    @property
    def id(self):
        return self.get('id', None)

    @property
    def reference(self):
        """
        Returns reference if local resource is saved
        """
        if self.id:
            return '{0}/{1}'.format(self.resource_type, self.id)


class FHIRReference(Reference):
    def get_root_keys(self):
        return ['reference', 'display']

    @property
    def reference(self):
        return self['reference']

    @property
    def id(self):
        """
        Returns id if reference specifies to the local resource
        """
        if self.is_local:
            return self.reference.split('/', 1)[1]

    @property
    def resource_type(self):
        """
        Returns resource type if reference specifies to the local resource
        """
        if self.is_local:
            return self.reference.split('/', 1)[0]

    @property
    def is_local(self):
        return self.reference.count('/') == 1


def load_schema(version):
    filename = '{0}/schemas/fhir-{1}.pkl'.format(dirname(__file__), version)
    with open(filename, 'rb') as f:
        return pickle.load(f)


class FHIRClient(Client):
    searchset_class = FHIRSearchSet
    resource_class = FHIRResource

    def __init__(self, url, authorization=None, with_cache=False,
                 fhir_version='3.0.1'):
        schema = load_schema(fhir_version)
        super(FHIRClient, self).__init__(url, authorization, with_cache, schema)

    def reference(self, resource_type=None, id=None, reference=None, **kwargs):
        if resource_type and id:
            reference = '{0}/{1}'.format(resource_type, id)

        if not reference:
            raise TypeError(
                'Arguments `resource_type` and `id` or `reference` '
                'are required')
        return FHIRReference(self, reference=reference, **kwargs)

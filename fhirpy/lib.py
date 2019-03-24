from base_fhirpy import Client, SearchSet, Resource, Reference


class FHIRClient(Client):
    @property
    def searchset_class(self):
        return FHIRSearchSet

    @property
    def resource_class(self):
        return FHIRResource

    @property
    def reference_class(self):
        return FHIRReference


class FHIRSearchSet(SearchSet):
    pass


class FHIRResource(Resource):
    @staticmethod
    def is_reference(value):
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

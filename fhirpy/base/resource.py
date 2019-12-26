from abc import ABC, abstractmethod

from fhirpy.base.exceptions import ResourceNotFound
from fhirpy.base.utils import parse_path, get_by_path, convert_values


class AbstractResource(dict):
    client = None

    def __init__(self, client, **kwargs):
        self.client = client

        super(AbstractResource, self).__init__(**kwargs)

    def __eq__(self, other):
        return isinstance(other, AbstractResource) \
               and self.reference == other.reference

    def __setitem__(self, key, value):
        super(AbstractResource, self).__setitem__(key, value)

    def __getitem__(self, key):
        return super(AbstractResource, self).__getitem__(key)

    def __getattribute__(self, key):
        try:
            return super().__getattribute__(key)
        except AttributeError:
            return self[key]

    def __setattr__(self, key, value):
        try:
            super().__getattribute__(key)
            super().__setattr__(key, value)
        except AttributeError:
            self[key] = value

    def get_by_path(self, path, default=None):
        keys = parse_path(path)

        return get_by_path(self, keys, default)

    def get(self, key, default=None):
        return super(AbstractResource, self).get(key, default)

    def setdefault(self, key, default=None):
        return super(AbstractResource, self).setdefault(key, default)

    def serialize(self):
        def convert_fn(item):
            if isinstance(item, BaseResource):
                return item.to_reference().serialize(), True
            elif isinstance(item, BaseReference):
                return item.serialize(), True
            else:
                return item, False

        return convert_values(
            {key: value
             for key, value in self.items()}, convert_fn
        )

    @property
    def id(self):  # pragma: no cover
        raise NotImplementedError()

    @property
    def resource_type(self):  # pragma: no cover
        raise NotImplementedError()

    @property
    def reference(self):  # pragma: no cover
        raise NotImplementedError()


class BaseResource(AbstractResource, ABC):
    resource_type = None

    def __init__(self, client, resource_type, **kwargs):
        def convert_fn(item):
            if isinstance(item, AbstractResource):
                return item, True

            if self.is_reference(item):
                return client.reference(**item), True

            return item, False

        self.resource_type = resource_type
        kwargs['resourceType'] = resource_type
        converted_kwargs = convert_values(kwargs, convert_fn)

        super(BaseResource, self).__init__(client, **converted_kwargs)

    def __setitem__(self, key, value):
        if key == 'resourceType':
            raise KeyError(
                'Can not change `resourceType` after instantiating resource. '
                'You must re-instantiate resource using '
                '`Client.resource` method'
            )

        super(BaseResource, self).__setitem__(key, value)

    def __str__(self):  # pragma: no cover
        return '<{0} {1}>'.format(self.__class__.__name__, self._get_path())

    def __repr__(self):  # pragma: no cover
        return self.__str__()

    @abstractmethod  # pragma: no cover
    def save(self):
        pass

    @abstractmethod  # pragma: no cover
    def delete(self):
        pass

    def to_resource(self):
        """
        Returns Resource instance for this resource
        """
        return self

    def to_reference(self, **kwargs):
        """
        Returns Reference instance for this resource
        """
        if not self.reference:
            raise ResourceNotFound(
                'Can not get reference to unsaved resource without id'
            )

        return self.client.reference(reference=self.reference, **kwargs)

    @abstractmethod  # pragma: no cover
    def is_reference(self, value):
        pass

    @abstractmethod  # pragma: no cover
    def is_valid(self, raise_exception=False):
        pass

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

    def _get_path(self):
        if self.id:
            return '{0}/{1}'.format(self.resource_type, self.id)
        elif self.resource_type == 'Bundle':
            return ''

        return self.resource_type


class BaseReference(AbstractResource):
    def __str__(self):  # pragma: no cover
        return '<{0} {1}>'.format(self.__class__.__name__, self.reference)

    def __repr__(self):  # pragma: no cover
        return self.__str__()

    @abstractmethod  # pragma: no cover
    def to_resource(self):
        pass

    def to_reference(self, **kwargs):
        """
        Returns Reference instance for this reference
        """
        return self.client.reference(reference=self.reference, **kwargs)

    @property  # pragma: no cover
    @abstractmethod
    def reference(self):
        pass

    @property  # pragma: no cover
    @abstractmethod
    def id(self):
        """
        Returns id if reference specifies to the local resource
        """
        pass

    @property  # pragma: no cover
    @abstractmethod
    def resource_type(self):
        """
        Returns resource type if reference specifies to the local resource
        """
        pass

    @property  # pragma: no cover
    @abstractmethod
    def is_local(self):
        pass

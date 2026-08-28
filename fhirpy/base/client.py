import warnings
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, TypeVar, Union

from yarl import URL

from fhirpy.base.utils import (
    encode_params,
    remove_prefix,
)


class AbstractClient(ABC):
    url: str
    url_aliases: list[str]
    authorization: Union[str, None]
    extra_headers: Union[dict, None]
    dump_resource: Callable[[Any], Any]

    # Deprecated
    @property  # pragma: no cover
    def searchset_class(self):
        raise NotImplementedError()

    # Deprecated
    @property  # pragma: no cover
    def resource_class(self):
        raise NotImplementedError()

    def __init__(
        self,
        url: str,
        authorization: Union[str, None] = None,
        extra_headers: Union[dict, None] = None,
        *,
        url_aliases: Union[list[str], None] = None,
        dump_resource: Callable[[Any], dict] = lambda x: dict(x),
    ):
        """
        url_aliases are public addresses of the same server, e.g. an ingress hostname
        that appears in Bundle.link. An absolute request url starting with one of them
        is rewritten onto `url` before the request is made.

        dump kwarg is a function that is called for all CRUD operations.
        It's needed for custom typing model like pydantic
        """
        self.url = url
        self.url_aliases = url_aliases or []
        self.authorization = authorization
        self.extra_headers = extra_headers
        self.dump_resource = dump_resource

    def __str__(self) -> str:
        return f"<{self.__class__.__name__} {self.url}>"

    def __repr__(self) -> str:
        return self.__str__()

    @abstractmethod
    def reference(self, resource_type=None, id=None, reference=None, **kwargs):  # noqa: A002
        pass

    def resource(self, resource_type, **kwargs):  # pragma: no cover
        warnings.warn(
            "class var `resource_class` is deprecated "
            "and will be removed in future versions. "
            "Please redefine `resource` method of client",
            DeprecationWarning,
            stacklevel=2,
        )

        return self.resource_class(self, resource_type=resource_type, **kwargs)

    def resources(self, resource_type):  # pragma: no cover
        warnings.warn(
            "class var `searchset_class` is deprecated "
            "and will be removed in future versions. "
            "Please redefine `resource` method of client",
            DeprecationWarning,
            stacklevel=2,
        )

        return self.searchset_class(self, resource_type=resource_type)

    @abstractmethod
    def execute(
        self,
        path: str,
        method: str = "post",
        data: Union[dict, None] = None,
        params: Union[dict, None] = None,
    ):
        pass

    @abstractmethod
    def get(self, resource_type_or_resource_or_ref, id_or_ref=None):
        pass

    @abstractmethod
    def save(self, resource, fields):
        pass

    @abstractmethod
    def create(self, resource):
        pass

    @abstractmethod
    def update(self, resource):
        pass

    @abstractmethod
    def patch(self, resource_type_or_resource_or_ref, id_or_ref=None, **kwargs):
        pass

    @abstractmethod
    def delete(self, resource_type_or_resource_or_ref, id_or_ref=None):
        pass

    @abstractmethod
    def _do_request(  # noqa: PLR0913
        self,
        method: str,
        path: str,
        data: Union[dict, None] = None,
        params: Union[dict, None] = None,
        extra_headers: Union[dict, None] = None,
        *,
        returning_status=False,
    ) -> Union[Any, tuple[dict, int]]:
        pass

    @abstractmethod
    def _fetch_resource(self, path, params=None):
        pass

    def _build_request_headers(self) -> dict:
        headers = {"Accept": "application/fhir+json"}

        if self.authorization:
            headers["Authorization"] = self.authorization

        if self.extra_headers is not None:
            headers = {**headers, **self.extra_headers}

        return headers

    def _build_request_url(self, path, params) -> str:
        if URL(path).is_absolute():
            path = self._replace_url_alias(path)
            if self.url in path:
                return path

            raise ValueError(
                f'Request url "{path}" does not contain base url "{self.url}"'
                " (possible security issue)"
            )
        path = path.lstrip("/")
        base_url_path = URL(self.url.rstrip("/")).path.lstrip("/") + "/"
        path = remove_prefix(path, base_url_path)
        params = params or {}

        return f'{self.url.rstrip("/")}/{path.lstrip("/")}?{encode_params(params)}'

    def _replace_url_alias(self, url: str) -> str:
        """Rewrites a public address of the same server onto the configured base url"""
        for alias in self.url_aliases:
            alias_prefix = f'{alias.rstrip("/")}/'
            if url.startswith(alias_prefix):
                return f'{self.url.rstrip("/")}/{remove_prefix(url, alias_prefix)}'

        return url


TClient = TypeVar("TClient", bound=AbstractClient)

import asyncio
import inspect
import json
import warnings
from unittest.mock import Mock, patch

import pytest

from fhirpy import AsyncFHIRClient, SyncFHIRClient

from .utils import MockAiohttpResponse, MockRequestsResponse


@pytest.fixture(params=[SyncFHIRClient, AsyncFHIRClient], ids=["sync", "async"])
def client_transport(request):
    client = request.param("http://example.com/fhir")
    response_text = json.dumps({"resourceType": "Patient", "id": "example", "active": True})
    if isinstance(client, SyncFHIRClient):
        response = MockRequestsResponse(response_text.encode(), 200)
        with patch("requests.request", return_value=response) as request_mock:
            yield client, request_mock
    else:
        session = Mock()
        session.request.return_value = MockAiohttpResponse(response_text, 200)
        with patch("aiohttp.ClientSession") as session_mock:
            session_mock.return_value.__aenter__.return_value = session
            yield client, session.request


def run(result):
    return asyncio.run(result) if inspect.isawaitable(result) else result


def test_conditional_patch_with_kwargs_does_not_warn(client_transport):
    client, request_mock = client_transport
    searchset = client.resources("Patient").search(identifier="fhirpy")

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        patched = run(searchset.patch(active=True))

    assert patched.id == "example"
    method, url = request_mock.call_args.args
    assert method.lower() == "patch"
    assert url == "http://example.com/fhir/Patient?identifier=fhirpy"
    assert request_mock.call_args.kwargs["json"] == {"active": True}


def test_conditional_patch_with_resource_is_deprecated(client_transport):
    client, request_mock = client_transport
    searchset = client.resources("Patient").search(identifier="fhirpy")
    resource = client.resource("Patient", active=True)

    with pytest.warns(DeprecationWarning, match="first arg of method patch"):
        run(searchset.patch(resource))

    assert request_mock.call_args.kwargs["json"] == {"resourceType": "Patient", "active": True}

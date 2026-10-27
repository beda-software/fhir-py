import asyncio
import inspect
import json
from unittest.mock import Mock, patch

import pytest

from fhirpy import AsyncFHIRClient, SyncFHIRClient
from fhirpy.base.exceptions import MultipleResourcesFound

from .utils import MockAiohttpResponse, MockRequestsResponse


@pytest.fixture(params=[SyncFHIRClient, AsyncFHIRClient], ids=["sync", "async"])
def client_transport(request):
    client = request.param(
        "http://example.com/fhir",
        authorization="Bearer test-token",
        extra_headers={"X-Client": "default"},
    )
    response_text = json.dumps({"resourceType": "Patient", "id": "example"})
    if isinstance(client, SyncFHIRClient):
        response = MockRequestsResponse(response_text.encode(), 200)
        with patch("requests.request", return_value=response) as request_mock:
            yield client, request_mock, request_mock, response
    else:
        response = MockAiohttpResponse(response_text, 200)
        session = Mock()
        session.request.return_value = response
        with patch("aiohttp.ClientSession") as session_mock:
            session_mock.return_value.__aenter__.return_value = session
            yield client, session.request, session_mock, response


def execute(client, *args, **kwargs):
    result = client.execute(*args, **kwargs)
    return asyncio.run(result) if inspect.isawaitable(result) else result


@pytest.mark.parametrize("method", ["get", "post", "put", "patch", "delete"])
def test_execute_request_headers(client_transport, method):
    client, request_mock, headers_mock, _ = client_transport
    data = (
        {"resourceType": "Patient", "id": "example"} if method in {"post", "put", "patch"} else None
    )
    result = execute(
        client,
        "Patient/example",
        method,
        data,
        {"_format": "json"},
        extra_headers={"If-Match": 'W/"42"', "X-Client": "request"},
    )

    assert result == {"resourceType": "Patient", "id": "example"}
    assert request_mock.call_args.args == (
        method,
        "http://example.com/fhir/Patient/example?_format=json",
    )
    assert request_mock.call_args.kwargs["json"] == data
    headers = headers_mock.call_args.kwargs["headers"]
    assert headers["If-Match"] == 'W/"42"'
    assert headers["X-Client"] == "request"
    assert headers["Authorization"] == "Bearer test-token"


@pytest.mark.parametrize(
    "options",
    [{}, {"extra_headers": None}, {"extra_headers": {}}],
    ids=["omitted", "none", "empty"],
)
def test_execute_default_headers(client_transport, options):
    client, request_mock, headers_mock, _ = client_transport

    result = execute(client, "Patient/example", **options)

    assert result == {"resourceType": "Patient", "id": "example"}
    assert request_mock.call_args.args == ("post", "http://example.com/fhir/Patient/example?")
    headers = headers_mock.call_args.kwargs["headers"]
    assert headers["X-Client"] == "default"
    assert headers["Authorization"] == "Bearer test-token"
    assert "If-Match" not in headers


def test_execute_headers_do_not_affect_later_requests(client_transport):
    client, _, headers_mock, _ = client_transport
    request_headers = {"If-Match": 'W/"42"', "X-Client": "request"}

    execute(client, "Patient/example", "put", extra_headers=request_headers)
    execute(client, "Patient/example", "get")

    first, second = [call.kwargs["headers"] for call in headers_mock.call_args_list]
    assert first["If-Match"] == 'W/"42"'
    assert first["X-Client"] == "request"
    assert "If-Match" not in second
    assert second["X-Client"] == "default"
    assert client.extra_headers == {"X-Client": "default"}
    assert request_headers == {"If-Match": 'W/"42"', "X-Client": "request"}


def test_execute_preserves_precondition_failed_exception(client_transport):
    client, _, _, response = client_transport
    if isinstance(client, SyncFHIRClient):
        response.status_code = 412
        response.content = b"Version conflict"
    else:
        response.status = 412
        response._text = "Version conflict"

    with pytest.raises(MultipleResourcesFound, match="Version conflict"):
        execute(client, "Patient/example", "put", extra_headers={"If-Match": 'W/"41"'})

from unittest import mock

import pytest

from fhirpy import AsyncFHIRClient, SyncFHIRClient

OPS = [{"op": "replace", "path": "/active", "value": True}]
JSON_PATCH = {"Content-Type": "application/json-patch+json"}


def test_sync_patch_operations_sends_json_patch():
    client = SyncFHIRClient("http://mock/fhir")
    with mock.patch.object(client, "_do_request", return_value={}) as do_request:
        client.patch("Patient", "1", operations=OPS)
    do_request.assert_called_once_with("patch", "Patient/1", data=OPS, extra_headers=JSON_PATCH)


def test_sync_patch_fields_unchanged():
    client = SyncFHIRClient("http://mock/fhir")
    with mock.patch.object(client, "_do_request", return_value={}) as do_request:
        client.patch("Patient", "1", active=True)
    do_request.assert_called_once_with(
        "patch", "Patient/1", data={"active": True}, extra_headers=None
    )


def test_patch_rejects_operations_and_fields_together():
    with pytest.raises(TypeError):
        SyncFHIRClient("http://mock/fhir").patch("Patient", "1", operations=OPS, active=True)


@pytest.mark.asyncio
async def test_async_patch_operations_sends_json_patch():
    client = AsyncFHIRClient("http://mock/fhir")
    with mock.patch.object(client, "_do_request", mock.AsyncMock(return_value={})) as do_request:
        await client.patch("Patient", "1", operations=OPS)
    do_request.assert_called_once_with("patch", "Patient/1", data=OPS, extra_headers=JSON_PATCH)

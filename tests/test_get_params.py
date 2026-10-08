"""Tests for https://github.com/beda-software/fhir-py/issues/100.

Some FHIR servers (e.g. Cerner sandbox) reject search requests that include
both ``_count`` and ``_id``, responding with::

    OperationOutcome: "_count: unsupported when _id is provided"

``SearchSet.get(id=...)`` must therefore not send ``_count`` when ``_id`` is
specified, while ``get()`` without an id keeps the ``limit(2)`` safeguard.
"""

from unittest.mock import patch

import pytest

from fhirpy import AsyncFHIRClient, SyncFHIRClient
from fhirpy.base.lib_async import AsyncSearchSet
from fhirpy.base.lib_sync import SyncSearchSet

PATIENT = {"resourceType": "Patient", "id": "patient-1"}


def _sync_fetch(searchset):
    _sync_fetch.captured_params = dict(searchset.params)
    return [PATIENT]


async def _async_fetch(searchset):
    _async_fetch.captured_params = dict(searchset.params)
    return [PATIENT]


class TestGetParams:
    def test_sync_get_with_id_omits_count(self):
        client = SyncFHIRClient("mock")
        with patch.object(SyncSearchSet, "fetch", _sync_fetch):
            with pytest.warns(DeprecationWarning):
                resource = client.resources("Patient").get(id="patient-1")

        assert "_count" not in _sync_fetch.captured_params
        assert _sync_fetch.captured_params["_id"] == ["patient-1"]
        assert resource["id"] == "patient-1"

    def test_sync_get_without_id_keeps_limit(self):
        client = SyncFHIRClient("mock")
        with patch.object(SyncSearchSet, "fetch", _sync_fetch):
            client.resources("Patient").get()

        assert _sync_fetch.captured_params == {"_count": [2]}

    @pytest.mark.asyncio()
    async def test_async_get_with_id_omits_count(self):
        client = AsyncFHIRClient("mock")
        with patch.object(AsyncSearchSet, "fetch", _async_fetch):
            with pytest.warns(DeprecationWarning):
                resource = await client.resources("Patient").get(id="patient-1")

        assert "_count" not in _async_fetch.captured_params
        assert _async_fetch.captured_params["_id"] == ["patient-1"]
        assert resource["id"] == "patient-1"

    @pytest.mark.asyncio()
    async def test_async_get_without_id_keeps_limit(self):
        client = AsyncFHIRClient("mock")
        with patch.object(AsyncSearchSet, "fetch", _async_fetch):
            await client.resources("Patient").get()

        assert _async_fetch.captured_params == {"_count": [2]}

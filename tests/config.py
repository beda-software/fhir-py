import os
from aiohttp import BasicAuth


FHIR_SERVER_URL = os.environ.get("FHIR_SERVER_URL", "http://localhost:8080/fhir")
FHIR_SERVER_AUTHORIZATION = os.environ.get(
    "FHIR_SERVER_AUTHORIZATION", BasicAuth("root", "secret").encode()
)

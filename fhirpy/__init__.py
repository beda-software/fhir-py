from .lib import AsyncFHIRClient, SyncFHIRClient

__title__ = "fhir-py"
__version__ = "2.0.3"
__author__ = "beda.software"
__license__ = "None"
__copyright__ = "Copyright 2024 beda.software"

# Version synonym
VERSION = __version__


__all__ = ["AsyncFHIRClient", "SyncFHIRClient"]

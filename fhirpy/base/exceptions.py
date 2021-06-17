import json


class BaseFHIRError(Exception):
    pass


class ResourceNotFound(BaseFHIRError):
    pass


class InvalidResponse(BaseFHIRError):
    pass


class AuthorizationError(BaseFHIRError):
    pass


class OperationOutcome(BaseFHIRError):
    def __init__(self, *args, **kwargs):
        error = json.loads(args[0])["issue"]
        super().__init__(error, kwargs)


class MultipleResourcesFound(BaseFHIRError):
    pass

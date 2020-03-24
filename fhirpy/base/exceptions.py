class BaseFHIRError(Exception):
    pass


class ResourceNotFound(BaseFHIRError):
    pass


class InvalidResponse(BaseFHIRError):
    pass


class AuthorizationError(BaseFHIRError):
    pass


class OperationOutcome(BaseFHIRError):
    pass


class MultipleResourcesFound(BaseFHIRError):
    pass

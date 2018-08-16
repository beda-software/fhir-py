class FHIRError(Exception):
    pass


class FHIRResourceNotFound(FHIRError):
    pass


class FHIRInvalidResponse(FHIRError):
    pass


class FHIRAuthorizationError(FHIRError):
    pass


class FHIROperationOutcome(FHIRError):
    pass


class FHIRNotSupportedVersionError(FHIRError):
    pass

class AidboxError(Exception):
    pass


class AidboxResourceNotFound(AidboxError):
    pass


class AidboxResourceFieldDoesNotExist(AidboxError):
    pass


class AidboxAuthorizationError(AidboxError):
    pass


class AidboxOperationOutcome(AidboxError):
    pass

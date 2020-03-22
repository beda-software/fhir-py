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


class ChangeResourceType(Exception):
    def __init__(self):
        default_message = (
            'Can not change `resourceType` after instantiating resource. '
            'You must re-instantiate resource using '
            '`Client.resource` method'
        )
        super().__init__(default_message)

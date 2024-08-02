import json
from enum import Enum


class BaseFHIRError(Exception):
    pass


class ResourceNotFound(BaseFHIRError):
    pass


class InvalidResponse(BaseFHIRError):
    pass


class AuthorizationError(BaseFHIRError):
    pass


class MultipleResourcesFound(BaseFHIRError):
    pass


class IssueType(Enum):
    """Some Issue types from https://www.hl7.org/fhir/valueset-issue-type.html"""

    invalid = "invalid"  # Content invalid against the specification or a profile.
    required = "required"  # A required element is missing.
    forbidden = "forbidden"  # The user does not have the rights to perform this action.
    not_found = "not-found"  # The reference provided was not found.
    exception = "exception"  # An unexpected internal error has occurred.
    informational = "informational"  # A message unrelated to the processing success of the completed operation (examples of the latter include things like reminders of password expiry, system maintenance times, etc.).


class IssueSeverity(Enum):
    fatal = "fatal"
    error = "error"
    warning = "warning"
    information = "information"


class OperationOutcome(BaseFHIRError):
    def __init__(
        self,
        reason=None,
        *,
        resource=None,
        severity=IssueSeverity.fatal.value,
        code=IssueType.invalid.value,
    ):
        self.resource = resource or {
            "resourceType": "OperationOutcome",
            "issue": [
                {
                    "severity": severity,
                    "code": code,
                    "diagnostics": reason or "Error",
                }
            ],
            "text": {
                "status": "generated",
                "div": reason or "Something went wrong",
            },
        }
        super().__init__(json.dumps(self.resource, indent=2))

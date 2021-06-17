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
        text: str = args[0]["text"]
        text = text.removeprefix(
            "<div xmlns=\"http://www.w3.org/1999/xhtml\"><h1>Operation Outcome</h1><table border=\"0\"><tr><td style=\"font-weight: bold;\">ERROR</td><td>[]</td><td><pre>").removesuffix(
            "</pre></td>\n\t\t\t</tr>\n\t\t</table>\n\t</div>")
        error = {"text": text,
                 "issue": args[0]["issue"]}
        super(args, kwargs)


class MultipleResourcesFound(BaseFHIRError):
    pass

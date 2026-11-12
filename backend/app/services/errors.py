"""Domain errors, rendered by the API as RFC 9457 problem JSON with a stable code."""


class DomainError(Exception):
    status = 400

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(detail or code)
        self.code = code
        self.detail = detail or code


class NotFound(DomainError):
    status = 404


class Conflict(DomainError):
    status = 409

class RPCError(Exception):
    """Base for all RPC client/server errors."""

    status_code = 500


class InvalidRequest(RPCError):
    """400 — request rejected (missing/invalid arguments)."""

    status_code = 400


class AuthError(RPCError):
    """401 — missing or invalid credentials."""

    status_code = 401


class NotFound(RPCError):
    """404 — referenced entity does not exist."""

    status_code = 404


class ServiceError(RPCError):
    """5xx — the RPC service failed."""

    status_code = 500


_BY_STATUS = {cls.status_code: cls for cls in (InvalidRequest, AuthError, NotFound)}


def error_for_status(status_code, detail):
    if status_code in _BY_STATUS:
        return _BY_STATUS[status_code](detail)
    if status_code >= 500:
        return ServiceError(detail)
    return RPCError(f"unexpected status {status_code}: {detail}")

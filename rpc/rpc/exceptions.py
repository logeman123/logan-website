"""RPC error hierarchy — the single vocabulary of failure shared across the whole system.

This module is the keystone of the RPC layer's *symmetric* error handling. The same
exception classes are used on BOTH sides of every HTTP+JSON call:

  * On the SERVER side, a tool handler (or the dispatch/router plumbing in ``server.py``)
    raises one of these; ``add_rpc_error_handler`` turns it into an HTTP response whose
    status code is read straight off the exception's ``status_code`` attribute.
  * On the CLIENT side (``base.py``), when a response comes back non-2xx, ``ServiceClient``
    reconstructs the *equivalent* exception from the status code via ``error_for_status`` and
    re-raises it. Transport-level failures (host down, DNS, timeout) are wrapped as
    ``ServiceError`` too.

Why one shared hierarchy? Because callers of the RPC layer want to write ONE degradation
path: ``except RPCError`` catches everything — a 400 from bad arguments, a 401 from a bad
token, a 404 for a missing project, a 500 from a crashing handler, AND a completely
unreachable backend. The web BFF relies on exactly this: every route wraps its RPC calls in
``except RPCError`` and renders a friendly fallback instead of a 500 page. The status-code
attribute is the hinge that makes the mapping reversible: raise -> HTTP status -> raise again,
with no loss of meaning.

The class -> status mapping (and its inverse, ``error_for_status``) is deliberately tiny and
explicit so a learner can trace an error from a failing handler all the way to the browser.
"""


class RPCError(Exception):
    """Base for all RPC client/server errors.

    Every RPC failure — whether it originates in a handler, in the dispatch plumbing, or in
    the client's transport layer — is an instance of this class (or a subclass). That single
    fact is what lets every caller degrade gracefully with one ``except RPCError`` clause.

    ``status_code`` is a *class attribute*, not an instance field: each subclass overrides it
    with the HTTP status it maps to. The server's exception handler reads ``exc.status_code``
    to build the response; keeping it on the class means the mapping lives next to the meaning.
    500 is the base default because "something went wrong that we did not classify" is, by
    convention, a server error.
    """

    status_code = 500


class InvalidRequest(RPCError):
    """400 — request rejected (missing/invalid arguments).

    Raised in ``ToolRegistry.dispatch`` when the incoming JSON payload fails Pydantic
    validation against the tool's declared input model. In other words: the client sent a
    request the server understood but could not accept. Maps to HTTP 400 Bad Request.
    """

    status_code = 400


class AuthError(RPCError):
    """401 — missing or invalid credentials.

    Two origins: (1) the server's bearer-token check in ``create_rpc_router`` rejects a
    request whose ``Authorization`` header does not match the expected token, and (2) the
    client's ``ServiceClient._token`` wraps any failure to *obtain* a token as an AuthError,
    so a broken token provider surfaces the same way a rejected token would. Maps to HTTP 401.
    """

    status_code = 401


class NotFound(RPCError):
    """404 — referenced entity does not exist.

    Used both for "no such tool" (``dispatch`` on an unregistered name) and for domain-level
    misses (a handler asked for a project slug that is not in the repository). Maps to HTTP 404.
    """

    status_code = 404


class ServiceError(RPCError):
    """5xx — the RPC service failed.

    This is the graceful-degradation workhorse. It covers two very different situations that
    a caller nonetheless wants to treat identically:
      * the remote service ran but blew up (an unhandled exception in a handler -> 500), and
      * the remote service could not even be reached (``ServiceClient._send`` wraps every
        ``httpx.RequestError`` — connection refused, DNS failure, timeout — as ServiceError).
    Wrapping transport errors here is what makes "backend is completely down" indistinguishable
    from "backend returned 500" at the ``except RPCError`` call site, which is exactly what the
    web BFF needs to render a fallback instead of crashing. Maps to HTTP 500.
    """

    status_code = 500


# Reverse lookup table: HTTP status code -> the exception class that means it. Built once at
# import time from the subclasses whose codes are unambiguous (400/401/404). ServiceError is
# intentionally NOT in here — every 5xx collapses to ServiceError via the range check below,
# so we do not need (or want) an exact-code entry that would only match a literal 500.
_BY_STATUS = {cls.status_code: cls for cls in (InvalidRequest, AuthError, NotFound)}


def error_for_status(status_code, detail):
    """Rebuild the RPC exception that corresponds to an HTTP status code.

    This is the *inverse* of the raise-side mapping: the client calls it after receiving a
    non-2xx response so that a server-side ``NotFound`` (which travelled the wire as HTTP 404)
    is re-raised on the client as a ``NotFound`` again — preserving the error's meaning across
    the network boundary. ``detail`` is the server's response body, carried along as the
    exception message so debugging context is not lost.
    """
    # Exact match on a known client-error code (400/401/404) -> its specific subclass.
    if status_code in _BY_STATUS:
        return _BY_STATUS[status_code](detail)
    # Any other server-error code collapses to the generic ServiceError bucket.
    if status_code >= 500:
        return ServiceError(detail)
    # A non-2xx code we did not anticipate (e.g. a stray 3xx/418): keep it as the base type so
    # it is still caught by ``except RPCError`` but is visibly flagged as unclassified.
    return RPCError(f"unexpected status {status_code}: {detail}")

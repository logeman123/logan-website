"""The RPC *client* — dependency injection taken all the way down to the wire.

``ServiceClient`` is how one service calls another in this system. The whole point of this
file is that the client bakes in NOTHING about *where* or *how* the call is made:

  * ``base_url``       — the target service's address is injected, never hard-coded.
  * ``token_provider`` — how to obtain a bearer token is injected (a callable), so auth is
                         pluggable: a static token in dev, something fancier in prod.
  * ``transport``      — the httpx transport is injected, which is the seam that makes the
                         in-process end-to-end tests possible. Tests pass an
                         ``httpx.MockTransport`` that routes "network" calls straight into a
                         Starlette ``TestClient`` for the target app — so the ai service can
                         really call the content service with zero sockets and zero servers.

This is dependency inversion at the *wire level*: high-level code (a typed client like
``ContentRpcClient`` in ``content_rpc``) depends on this abstraction, and the concrete
address/auth/transport are supplied from the outside (the web BFF's ``deps.py`` is the one
place that names them). Swap the injected pieces and the same client code talks to a real
server, a mock, or a test app — without changing a line here.

Two more responsibilities live here and matter a lot for the rest of the system:
  * Token caching with a refresh margin, so we do not re-mint a token on every call but still
    refresh *before* it actually expires.
  * Turning httpx transport failures into ``ServiceError``. This is the linchpin of graceful
    degradation: a backend that is completely unreachable raises the *same* ``RPCError`` type
    as a backend that returned 500, so a single ``except RPCError`` at the call site handles
    both. The web BFF depends on this to render fallbacks instead of 500 pages when content or
    ai is down.
"""

import time

import httpx

from rpc.exceptions import AuthError, RPCError, ServiceError, error_for_status

# Per-request wall-clock ceiling for the underlying httpx client (seconds).
DEFAULT_TIMEOUT = 30.0
# Safety margin subtracted from a token's lifetime so we refresh *before* it truly expires,
# avoiding a race where a token that looks valid to us is already rejected by the server.
DEFAULT_TOKEN_MARGIN = 60.0


def static_token_provider(token, expires_in=3600.0):
    """A token_provider that always returns the same static bearer token.

    A ``token_provider`` is the injected auth strategy: a zero-argument callable returning
    ``(token, expires_in_seconds)``. This factory produces the simplest possible one — it
    hands back a fixed token forever. It is what the services use today (the shared secret from
    config), and it is a template for how a real, refreshing provider would plug in: the
    ``ServiceClient`` neither knows nor cares that this token never changes.
    """
    # A closure over ``token``/``expires_in``: each call returns the same pair. The client's
    # cache logic (see ``_token``) will therefore mint it once and reuse it thereafter.
    def provider():
        return token, expires_in
    return provider


class ServiceClient:
    """Thin RPC client. Bakes in no host — base_url, token_provider and transport are injected.

    "Thin" is deliberate: this class only knows the RPC *convention* (tools live at
    ``POST /rpc/<tool>`` with a JSON body, discovery at ``GET /rpc/``, bearer auth), not any
    specific service's tools. Typed, service-specific clients (``ContentRpcClient``,
    ``AiRpcClient``) are built *on top* of one of these and expose real methods that match a
    Protocol; this class provides the generic transport underneath them.

    Because ``base_url``, ``token_provider`` and ``transport`` are all constructor-injected,
    the exact same class instance can point at a live server, a docker service, or an
    in-process test app — dependency inversion at the wire level.
    """

    def __init__(self, base_url, token_provider, *, transport=None,
                 timeout=DEFAULT_TIMEOUT, token_margin=DEFAULT_TOKEN_MARGIN):
        # A missing base_url is a wiring bug, not a runtime condition — fail loudly and early
        # rather than sending requests to an empty/garbage URL.
        if not base_url:
            raise ValueError("base_url is required (the RPC target URL)")
        # Normalise away a trailing slash so ``base_url + "/rpc/..."`` never doubles up ("//").
        self._base_url = base_url.rstrip("/")
        # Store the injected auth strategy; it is only *invoked* lazily, on first token need.
        self._token_provider = token_provider
        self._token_margin = token_margin
        # Token cache starts empty; ``_token`` populates it and tracks when it must refresh.
        self._cached_token = None
        self._token_expiry = 0.0
        # The one place httpx is instantiated. Note ``transport`` is passed straight through:
        # in production it is None (real sockets); in tests it is a MockTransport that dispatches
        # into the target app in-process — the injection seam that removes the network entirely.
        self._http = httpx.Client(timeout=timeout, transport=transport)

    @property
    def base_url(self):
        # Read-only view of the (slash-normalised) target address, handy for logging/debugging.
        return self._base_url

    # Context-manager support so callers can write ``with ServiceClient(...) as c:`` and be
    # guaranteed the underlying httpx connection pool is closed on exit.
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        # Releases the httpx connection pool. Safe and important for long-lived processes.
        self._http.close()

    def _token(self):
        """Return a valid bearer token, minting/refreshing it only when necessary.

        Caching matters: without it every RPC call would re-invoke the token provider (in a
        real deployment that could mean a network round-trip to an auth server). We keep the
        last token and only refresh when it is missing or (about to be) expired.
        """
        # ``time.monotonic`` — not ``time.time`` — because we are measuring *elapsed* time; a
        # clock adjustment (NTP step, DST) must never make a still-valid token look expired.
        now = time.monotonic()
        # Refresh if we have never fetched a token, or the cached one has reached its (margin-
        # adjusted) expiry. The margin means we refresh slightly early, never at the last ms.
        if self._cached_token is None or now >= self._token_expiry:
            try:
                token, expires_in = self._token_provider()
            except RPCError:
                # The provider already spoke our vocabulary (e.g. it raised AuthError itself) —
                # let it propagate unchanged rather than double-wrapping it.
                raise
            except Exception as exc:
                # Any *other* provider failure is normalised to AuthError so callers see a
                # single, meaningful error type for "could not authenticate".
                raise AuthError(f"failed to obtain RPC token: {exc}") from exc
            self._cached_token = token
            # Expire the cache ``token_margin`` seconds BEFORE the real expiry. ``max(0.0, ...)``
            # guards against a provider reporting a lifetime shorter than the margin (which would
            # otherwise push the expiry into the past and force a refresh every single call).
            self._token_expiry = now + max(0.0, float(expires_in) - self._token_margin)
        return self._cached_token

    def _headers(self):
        # Every RPC request carries the bearer token; the server side checks it with
        # ``hmac.compare_digest`` (see server.py) against its configured expected token.
        return {"Authorization": f"Bearer {self._token()}"}

    def _send(self, method, path, **kwargs):
        """The single choke point through which every request flows — and where errors are normalised."""
        try:
            resp = self._http.request(method, f"{self._base_url}{path}", headers=self._headers(), **kwargs)
        except httpx.RequestError as exc:
            # THE graceful-degradation seam. A transport-level failure — connection refused,
            # DNS error, timeout: the backend is unreachable — is wrapped as ServiceError, the
            # SAME type raised for a remote 500. That is why one ``except RPCError`` at the call
            # site (e.g. in the web BFF routes) transparently covers "backend down" too.
            raise ServiceError(f"request to {path} failed: {exc}") from exc
        # 2xx -> hand back the decoded JSON body directly (the typed clients re-parse it into
        # the shared Pydantic contracts).
        if resp.is_success:
            return resp.json()
        # Non-2xx -> reconstruct the matching RPC exception from the status code, so a 404 on the
        # wire becomes a NotFound in the caller. This is the inverse of the server's raise->status
        # mapping (see exceptions.error_for_status), making the error round-trip lossless.
        raise error_for_status(resp.status_code, resp.text)

    def call(self, tool, **arguments):
        # The core RPC convention: invoke a tool by POSTing its keyword arguments as a JSON body
        # to ``/rpc/<tool>``. This mirrors exactly what ``create_rpc_router`` exposes server-side.
        return self._send("POST", f"/rpc/{tool}", json=arguments)

    def list_tools(self):
        # Discovery endpoint: ``GET /rpc/`` returns the tool names and their JSON input schemas.
        # This same surface doubles as the AI/MCP tool catalogue, which is why it is first-class.
        return self._send("GET", "/rpc/")

    def __getattr__(self, name):
        """Attribute-access sugar: ``client.get_project(slug=...)`` -> ``client.call("get_project", slug=...)``.

        ``__getattr__`` only fires for attributes Python could NOT find normally, so real
        methods (``call``, ``close``, ...) are untouched — this only catches otherwise-unknown
        names and treats them as tool names. It lets typed clients (and quick experiments) call
        remote tools as if they were local methods, with no per-tool boilerplate here.
        """
        # Guard: never fabricate dunder/private lookups. Returning a callable for names like
        # ``__deepcopy__`` or ``_http`` would break pickling, copying, and introspection, so we
        # honour the normal "attribute not found" contract for anything starting with "_".
        if name.startswith("_"):
            raise AttributeError(name)
        # Return a thunk that forwards its keyword arguments to ``call`` under this tool name.
        return lambda **arguments: self.call(name, **arguments)

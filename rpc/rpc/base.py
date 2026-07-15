import time

import httpx

from rpc.exceptions import AuthError, RPCError, error_for_status

DEFAULT_TIMEOUT = 30.0
DEFAULT_TOKEN_MARGIN = 60.0


def static_token_provider(token, expires_in=3600.0):
    """A token_provider that always returns the same static bearer token."""
    def provider():
        return token, expires_in
    return provider


class ServiceClient:
    """Thin RPC client. Bakes in no host — base_url, token_provider and transport are injected."""

    def __init__(self, base_url, token_provider, *, transport=None,
                 timeout=DEFAULT_TIMEOUT, token_margin=DEFAULT_TOKEN_MARGIN):
        if not base_url:
            raise ValueError("base_url is required (the RPC target URL)")
        self._base_url = base_url.rstrip("/")
        self._token_provider = token_provider
        self._token_margin = token_margin
        self._cached_token = None
        self._token_expiry = 0.0
        self._http = httpx.Client(timeout=timeout, transport=transport)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        self._http.close()

    def _token(self):
        now = time.monotonic()
        if self._cached_token is None or now >= self._token_expiry:
            try:
                token, expires_in = self._token_provider()
            except RPCError:
                raise
            except Exception as exc:
                raise AuthError(f"failed to obtain RPC token: {exc}") from exc
            self._cached_token = token
            self._token_expiry = now + max(0.0, float(expires_in) - self._token_margin)
        return self._cached_token

    def _headers(self):
        return {"Authorization": f"Bearer {self._token()}"}

    def _send(self, method, path, **kwargs):
        resp = self._http.request(method, f"{self._base_url}{path}", headers=self._headers(), **kwargs)
        if resp.is_success:
            return resp.json()
        raise error_for_status(resp.status_code, resp.text)

    def call(self, tool, **arguments):
        return self._send("POST", f"/rpc/{tool}", json=arguments)

    def list_tools(self):
        return self._send("GET", "/rpc/")

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return lambda **arguments: self.call(name, **arguments)

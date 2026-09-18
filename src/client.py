"""Thin client for the ZeroTier One local JSON API.

The ZeroTier daemon exposes a control API on 127.0.0.1:9993. Every request must
carry the service authentication token in the ``X-ZT1-Auth`` header. Because
ZTDeck ships as a sandboxed Flatpak it can never read the root-owned token at
/var/lib/zerotier-one/authtoken.secret, so the token is looked up in places a
normal user account can actually reach.
"""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from gi.repository import GLib

from .i18n import _

DEFAULT_PORT = 9993
REQUEST_TIMEOUT = 5.0

#: Where zerotier-cli itself expects a user-readable copy of the token.
USER_TOKEN_PATH = Path(GLib.get_home_dir()) / ".zeroTierOneAuthToken"

#: Where ZTDeck stores a token the user pasted into the setup screen.
APP_TOKEN_PATH = Path(GLib.get_user_config_dir()) / "ztdeck" / "authtoken.secret"

#: Only reachable when ZTDeck runs unsandboxed as root; tried last.
SYSTEM_TOKEN_PATH = Path("/var/lib/zerotier-one/authtoken.secret")

TOKEN_SEARCH_PATHS = (APP_TOKEN_PATH, USER_TOKEN_PATH, SYSTEM_TOKEN_PATH)


class ZeroTierError(Exception):
    """Base class for every failure ZTDeck knows how to explain."""

    title = _("Something went wrong")
    hint = ""


class TokenMissingError(ZeroTierError):
    title = _("Authentication token not found")
    hint = _(
        "ZTDeck needs a readable copy of the ZeroTier service token before it "
        "can talk to the daemon."
    )


class DaemonUnreachableError(ZeroTierError):
    title = _("ZeroTier service is not running")
    hint = _(
        "Nothing is listening on the local ZeroTier control port. Start the "
        "service with: sudo systemctl enable --now zerotier-one"
    )


class AuthFailedError(ZeroTierError):
    title = _("Authentication token was rejected")
    hint = _(
        "The token ZTDeck found is no longer valid. Copy the current token "
        "again, then reload."
    )


class ApiError(ZeroTierError):
    title = _("The ZeroTier service returned an error")


def read_token():
    """Return the first readable service token, or ``None`` when there is none."""
    override = os.environ.get("ZTDECK_TOKEN_FILE")
    candidates = [Path(override)] if override else []
    candidates.extend(TOKEN_SEARCH_PATHS)
    for path in candidates:
        try:
            token = path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError):
            continue
        if token:
            return token
    return None


def store_token(token):
    """Persist a manually supplied token inside ZTDeck's own config directory."""
    token = (token or "").strip()
    if not token:
        raise ValueError("Refusing to store an empty token")
    APP_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    APP_TOKEN_PATH.write_text(token + "\n", encoding="utf-8")
    APP_TOKEN_PATH.chmod(0o600)
    return APP_TOKEN_PATH


def forget_token():
    """Remove a token previously stored by :func:`store_token`."""
    try:
        APP_TOKEN_PATH.unlink()
        return True
    except FileNotFoundError:
        return False


class ZeroTierClient:
    """Stateless-ish wrapper around the local control API.

    Every method blocks on network I/O, so callers must invoke them from a
    worker thread (see :func:`ztdeck.util.run_async`), never from the GTK main
    loop.
    """

    def __init__(self, port=None):
        self.port = int(port or os.environ.get("ZTDECK_PORT") or DEFAULT_PORT)
        self._token = None

    @property
    def token(self):
        if self._token is None:
            self._token = read_token()
        return self._token

    def reload_token(self):
        """Forget the cached token so the next call re-reads it from disk."""
        self._token = None
        return self.token

    @property
    def has_token(self):
        return bool(self.token)

    def _request(self, path, method="GET", body=None):
        token = self.token
        if not token:
            raise TokenMissingError(TokenMissingError.title)

        payload = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=payload,
            method=method,
            headers={
                "X-ZT1-Auth": token,
                "Content-Type": "application/json",
                "User-Agent": "ZTDeck",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise AuthFailedError(AuthFailedError.title) from exc
            detail = exc.reason or exc.code
            raise ApiError(f"{method} {path} failed: {detail}") from exc
        except urllib.error.URLError as exc:
            raise DaemonUnreachableError(DaemonUnreachableError.title) from exc
        except OSError as exc:
            raise DaemonUnreachableError(DaemonUnreachableError.title) from exc

        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ApiError(_("The service sent a malformed response")) from exc

    # -- read -------------------------------------------------------------

    def status(self):
        """Node identity, version and online state."""
        return self._request("/status") or {}

    def networks(self):
        """Every network this node has joined."""
        return self._request("/network") or []

    def peers(self):
        """Peers the node has recently talked to."""
        return self._request("/peer") or []

    def snapshot(self):
        """Fetch everything the window needs in one round trip set."""
        return {
            "status": self.status(),
            "networks": self.networks(),
            "peers": self.peers(),
        }

    # -- write ------------------------------------------------------------

    def join_network(self, network_id):
        return self._request(f"/network/{network_id}", method="POST", body={})

    def leave_network(self, network_id):
        return self._request(f"/network/{network_id}", method="DELETE")

    def set_network_option(self, network_id, key, value):
        """Toggle one of the per-network client settings (allowManaged, ...)."""
        return self._request(f"/network/{network_id}", method="POST", body={key: value})

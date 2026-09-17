"""Small helpers shared across the UI."""

import threading

from gi.repository import GLib


def run_async(worker, on_done=None):
    """Run ``worker()`` off the main loop and deliver its result on the main loop.

    ``on_done`` is called as ``on_done(result, error)`` where exactly one of the
    two is ``None``. Keeping every GTK call on the main thread is mandatory, so
    the worker itself must never touch widgets.
    """

    def thread_body():
        try:
            result, error = worker(), None
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI verbatim
            result, error = None, exc
        if on_done is not None:
            GLib.idle_add(on_done, result, error, priority=GLib.PRIORITY_DEFAULT)

    thread = threading.Thread(target=thread_body, daemon=True)
    thread.start()
    return thread


def format_latency(value):
    """Turn a raw ZeroTier latency figure into something readable."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        return "unknown"
    if value < 0:
        return "unknown"
    return f"{value} ms"


def format_network_status(status):
    """Map ZeroTier network status codes to human wording."""
    return {
        "OK": "Connected",
        "REQUESTING_CONFIGURATION": "Requesting configuration",
        "ACCESS_DENIED": "Access denied",
        "NOT_FOUND": "Network not found",
        "PORT_ERROR": "Port error",
        "CLIENT_TOO_OLD": "Client too old",
        "AUTHENTICATION_REQUIRED": "Authentication required",
    }.get(status, (status or "Unknown").replace("_", " ").capitalize())


def is_valid_network_id(text):
    """A ZeroTier network ID is exactly 16 hexadecimal digits."""
    text = (text or "").strip().lower()
    if len(text) != 16:
        return False
    return all(char in "0123456789abcdef" for char in text)

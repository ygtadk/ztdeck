"""Small helpers shared across the UI."""

import threading

from gi.repository import GLib

from .i18n import _


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
        return _("unknown")
    if value < 0:
        return _("unknown")
    # Translators: %d is a round-trip time in milliseconds.
    return _("%d ms") % value


def format_network_status(status):
    """Map ZeroTier network status codes to human wording."""
    known = {
        "OK": _("Connected"),
        "REQUESTING_CONFIGURATION": _("Requesting configuration"),
        "ACCESS_DENIED": _("Access denied"),
        "NOT_FOUND": _("Network not found"),
        "PORT_ERROR": _("Port error"),
        "CLIENT_TOO_OLD": _("Client too old"),
        "AUTHENTICATION_REQUIRED": _("Authentication required"),
    }
    if status in known:
        return known[status]
    return (status or _("Unknown")).replace("_", " ").capitalize()


def format_network_type(value):
    """Public/private network type, humanised."""
    known = {
        "PUBLIC": _("Public"),
        "PRIVATE": _("Private"),
    }
    if value in known:
        return known[value]
    return (value or _("Unknown")).replace("_", " ").title()


def is_valid_network_id(text):
    """A ZeroTier network ID is exactly 16 hexadecimal digits."""
    text = (text or "").strip().lower()
    if len(text) != 16:
        return False
    return all(char in "0123456789abcdef" for char in text)


def format_routes(routes):
    """Render a network's routing table, one route per line.

    ZeroTier route entries look like ``{"target": "10.0.0.0/24", "via": null}``.
    A route without a ``via`` is reached directly over the virtual interface.
    """
    lines = []
    for route in routes or []:
        target = route.get("target")
        if not target:
            continue
        via = route.get("via")
        if via:
            # Translators: a route reached through a gateway, as in
            # "10.0.0.0/24 via 10.0.0.1".
            lines.append(_("%(target)s via %(via)s") % {"target": target, "via": via})
        else:
            lines.append(target)
    return "\n".join(lines)


def format_dns(dns):
    """Render the DNS configuration a controller pushed, if any.

    The daemon reports ``{"domain": "...", "servers": [...]}``; either half can
    be absent or empty.
    """
    if not dns:
        return ""
    servers = [server for server in (dns.get("servers") or []) if server]
    domain = (dns.get("domain") or "").strip()
    if not servers and not domain:
        return ""

    parts = []
    if domain:
        parts.append(_("Search domain: %s") % domain)
    if servers:
        parts.extend(servers)
    return "\n".join(parts)

"""Desktop notifications for network state changes.

The window polls the daemon constantly, so it sees every transition. Only
meaningful ones become notifications: a network becoming usable, losing its
configuration, or being refused by the controller. Routine polling noise and
the very first snapshot after launch stay silent.
"""

from gi.repository import Gio, GLib

from .i18n import _

#: Statuses that mean "this network is usable right now".
_GOOD = frozenset({"OK"})

#: Statuses worth interrupting the user for when a network falls into them.
_BAD = frozenset(
    {
        "ACCESS_DENIED",
        "NOT_FOUND",
        "PORT_ERROR",
        "CLIENT_TOO_OLD",
        "AUTHENTICATION_REQUIRED",
    }
)


class NetworkNotifier:
    """Compares successive snapshots and notifies on meaningful changes."""

    def __init__(self, application):
        self._app = application
        self._previous = None
        self._enabled = True

    def set_enabled(self, enabled):
        self._enabled = bool(enabled)

    def reset(self):
        """Forget history, so the next snapshot is treated as a baseline."""
        self._previous = None

    def process(self, networks):
        """Diff ``networks`` against the previous poll and notify as needed."""
        current = {}
        for network in networks or []:
            network_id = network.get("nwid") or network.get("id")
            if not network_id:
                continue
            current[network_id] = {
                "status": network.get("status") or "",
                "name": network.get("name") or network_id,
            }

        # The first snapshot only establishes a baseline: telling the user
        # "connected" for every network they were already on would be noise.
        if self._previous is None:
            self._previous = current
            return

        if self._enabled:
            for network_id, now in current.items():
                before = self._previous.get(network_id)
                if before is None:
                    continue
                self._compare(network_id, before, now)

        self._previous = current

    def _compare(self, network_id, before, now):
        was, is_now = before["status"], now["status"]
        if was == is_now:
            return

        name = now["name"]
        if is_now in _GOOD and was not in _GOOD:
            self._notify(
                f"{network_id}-status",
                _("Connected to %s") % name,
                _("The network is ready to carry traffic."),
            )
        elif was in _GOOD and is_now in _BAD:
            self._notify(
                f"{network_id}-status",
                _("Disconnected from %s") % name,
                _("The network stopped responding as expected."),
            )
        elif is_now == "ACCESS_DENIED" and was != "ACCESS_DENIED":
            self._notify(
                f"{network_id}-status",
                _("Access denied on %s") % name,
                _("This device has not been authorized by the controller."),
            )

    def _notify(self, notification_id, title, body):
        notification = Gio.Notification.new(title)
        notification.set_body(body)
        notification.set_priority(Gio.NotificationPriority.NORMAL)
        try:
            notification.set_icon(Gio.ThemedIcon.new(self._app.app_id))
        except GLib.Error:
            pass
        self._app.send_notification(notification_id, notification)

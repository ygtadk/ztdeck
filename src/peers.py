"""The Peers page: who this node is actually talking to.

Like the networks page, rows are reused between polls so the list does not
flicker or jump while the user is scrolling it.
"""

from gi.repository import Adw, Gtk

from .util import format_latency

ROLE_LABELS = {
    "LEAF": "Peer",
    "PLANET": "Root server",
    "MOON": "Moon",
    "UPSTREAM": "Upstream",
}


def _describe(peer):
    """Return ``(subtitle, endpoint, direct)`` for one peer payload."""
    role = ROLE_LABELS.get(peer.get("role"), peer.get("role") or "Peer")

    version = peer.get("version") or ""
    if version.startswith("-1"):
        version = ""

    paths = [path for path in (peer.get("paths") or []) if path.get("active")]
    direct = bool(paths)

    parts = [role, "Direct" if direct else "Relayed", format_latency(peer.get("latency"))]
    if version:
        parts.append(f"v{version}")

    endpoint = paths[0].get("address", "") if paths else ""
    return "  ·  ".join(parts), endpoint, direct


class PeerRow(Adw.ActionRow):
    def __init__(self, address):
        super().__init__(title=address)
        self.add_css_class("property")

        self._icon = Gtk.Image()
        self.add_prefix(self._icon)

        self._endpoint = Gtk.Label(valign=Gtk.Align.CENTER)
        self._endpoint.add_css_class("caption")
        self._endpoint.add_css_class("dim-label")
        self.add_suffix(self._endpoint)

    def update(self, peer):
        subtitle, endpoint, direct = _describe(peer)
        if self.get_subtitle() != subtitle:
            self.set_subtitle(subtitle)

        icon = (
            "network-transmit-receive-symbolic"
            if direct
            else "network-wireless-signal-weak-symbolic"
        )
        self._icon.set_from_icon_name(icon)
        self._icon.remove_css_class("success")
        self._icon.remove_css_class("dim-label")
        self._icon.add_css_class("success" if direct else "dim-label")

        self._endpoint.set_label(endpoint)
        self._endpoint.set_visible(bool(endpoint))


class PeersPage(Adw.Bin):
    """Shows peers with their link type and latency."""

    def __init__(self):
        super().__init__()
        self._rows = {}

        self._empty = Adw.StatusPage(
            icon_name="network-transmit-receive-symbolic",
            title="No peers yet",
            description=(
                "Once this node exchanges traffic with other members they "
                "appear here with their connection quality."
            ),
        )

        self._group = Adw.PreferencesGroup()
        page = Adw.PreferencesPage()
        page.add(self._group)

        self._stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self._stack.add_named(self._empty, "empty")
        self._stack.add_named(page, "list")
        self.set_child(self._stack)

    def update(self, peers):
        seen = set()
        for peer in peers:
            address = peer.get("address")
            if not address:
                continue
            seen.add(address)

            row = self._rows.get(address)
            if row is None:
                row = PeerRow(address)
                self._rows[address] = row
                self._group.add(row)
            row.update(peer)

        for address in set(self._rows) - seen:
            self._group.remove(self._rows.pop(address))

        self._stack.set_visible_child_name("list" if self._rows else "empty")

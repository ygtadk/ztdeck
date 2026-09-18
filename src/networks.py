"""The Networks page: joined networks, their addresses and controls.

The window polls the daemon every few seconds. Rebuilding the rows on every
poll would collapse whatever the user has expanded and fight with switches they
are toggling, so rows are created once per network and afterwards updated in
place. Only networks that appear or disappear cause structural changes.
"""

from gi.repository import Adw, GObject, Gtk

from .i18n import _
from .util import (
    format_dns,
    format_network_status,
    format_network_type,
    format_routes,
    is_valid_network_id,
)


def _toggles():
    """The per-network client settings, built lazily so _() is bound first."""
    return (
        (
            "allowManaged",
            _("Allow managed addresses"),
            _("Let the controller assign IP addresses on this interface."),
        ),
        (
            "allowGlobal",
            _("Allow global routes"),
            _("Permit routes to public IP space."),
        ),
        (
            "allowDefault",
            _("Allow default route"),
            _("Let this network carry all internet traffic."),
        ),
        (
            "allowDNS",
            _("Allow DNS configuration"),
            _("Apply DNS servers published by the controller."),
        ),
    )


class NetworkRow(Adw.ExpanderRow):
    """One joined network, refreshable without losing its expanded state."""

    __gsignals__ = {
        "leave-requested": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "option-toggled": (GObject.SignalFlags.RUN_FIRST, None, (str, str, bool)),
        "copy-requested": (GObject.SignalFlags.RUN_FIRST, None, (str, str)),
    }

    def __init__(self, network_id):
        super().__init__()
        self.network_id = network_id
        self._applying_remote_state = False

        self.set_subtitle(network_id)

        self._badge = Gtk.Label(valign=Gtk.Align.CENTER)
        self._badge.add_css_class("caption")
        self.add_suffix(self._badge)

        # Adw.ExpanderRow.add_row() appends, so every row is created once here,
        # in its final order, and afterwards only has its contents refreshed.
        self._addresses = []
        self._address_row = Adw.ActionRow(
            title=_("Managed IP"), css_classes=["property"]
        )
        self._address_row.set_subtitle_lines(4)
        self._copy_button = Gtk.Button(
            icon_name="edit-copy-symbolic",
            tooltip_text=_("Copy address"),
            valign=Gtk.Align.CENTER,
        )
        self._copy_button.add_css_class("flat")
        self._copy_button.connect("clicked", self._on_copy_clicked)
        self._address_row.add_suffix(self._copy_button)
        self.add_row(self._address_row)

        # Routes and DNS are what people actually check when a network works
        # but traffic does not reach where they expect.
        self._routes = None
        self._routes_row = Adw.ActionRow(title=_("Routes"), css_classes=["property"])
        self._routes_row.set_subtitle_lines(6)
        self.add_row(self._routes_row)

        self._dns = None
        self._dns_row = Adw.ActionRow(title=_("DNS"), css_classes=["property"])
        self._dns_row.set_subtitle_lines(4)
        self.add_row(self._dns_row)

        self._detail_rows = {}
        for key, title in (
            ("type", _("Type")),
            ("portDeviceName", _("Interface")),
            ("mac", _("MAC address")),
            ("mtu", _("MTU")),
        ):
            row = Adw.ActionRow(title=title, css_classes=["property"])
            self._detail_rows[key] = row
            self.add_row(row)

        self._switch_rows = {}
        for key, title, subtitle in _toggles():
            switch_row = Adw.SwitchRow(title=title, subtitle=subtitle)
            switch_row.connect("notify::active", self._on_toggle, key)
            self._switch_rows[key] = switch_row
            self.add_row(switch_row)

        leave_row = Adw.ActionRow(
            title=_("Leave this network"),
            subtitle=_("Disconnects and removes the virtual interface."),
        )
        leave_button = Gtk.Button(label=_("Leave"), valign=Gtk.Align.CENTER)
        leave_button.add_css_class("destructive-action")
        leave_button.connect(
            "clicked", lambda _b: self.emit("leave-requested", self.network_id)
        )
        leave_row.add_suffix(leave_button)
        self.add_row(leave_row)

    def update(self, network):
        self._applying_remote_state = True
        try:
            self.set_title(network.get("name") or _("Unnamed network"))

            status = network.get("status", "")
            self._badge.set_label(format_network_status(status))
            self._badge.remove_css_class("success")
            self._badge.remove_css_class("warning")
            self._badge.add_css_class("success" if status == "OK" else "warning")

            self._update_addresses(network.get("assignedAddresses") or [])
            self._update_routes(network.get("routes") or [])
            self._update_dns(network.get("dns") or {})

            values = {
                "type": format_network_type(network.get("type")),
                "portDeviceName": network.get("portDeviceName") or _("Not created"),
                "mac": network.get("mac") or _("Unknown"),
                "mtu": str(network.get("mtu") or _("Unknown")),
            }
            for key, row in self._detail_rows.items():
                if row.get_subtitle() != values[key]:
                    row.set_subtitle(values[key])

            for key, switch_row in self._switch_rows.items():
                desired = bool(network.get(key))
                if switch_row.get_active() != desired:
                    switch_row.set_active(desired)
        finally:
            self._applying_remote_state = False

    def _update_addresses(self, addresses):
        if addresses == self._addresses:
            return
        self._addresses = list(addresses)

        self._address_row.set_title(
            _("Managed IPs") if len(addresses) > 1 else _("Managed IP")
        )
        self._address_row.set_subtitle(
            "\n".join(addresses) if addresses else _("Not assigned yet")
        )
        self._copy_button.set_visible(bool(addresses))
        self._copy_button.set_tooltip_text(
            _("Copy addresses") if len(addresses) > 1 else _("Copy address")
        )

    def _update_routes(self, routes):
        if routes == self._routes:
            return
        self._routes = list(routes)

        text = format_routes(routes)
        self._routes_row.set_subtitle(text or _("None"))

    def _update_dns(self, dns):
        if dns == self._dns:
            return
        self._dns = dict(dns)

        text = format_dns(dns)
        # A controller that publishes no DNS is the common case, so say so
        # rather than leaving the row blank.
        self._dns_row.set_subtitle(text or _("Not configured"))

    def _on_copy_clicked(self, _button):
        if not self._addresses:
            return
        # Strip the prefix length: what people paste elsewhere is the bare IP.
        bare = [address.split("/")[0] for address in self._addresses]
        message = _("Addresses copied") if len(bare) > 1 else _("Address copied")
        self.emit("copy-requested", "\n".join(bare), message)

    def _on_toggle(self, switch_row, _param, key):
        if self._applying_remote_state:
            return
        self.emit("option-toggled", self.network_id, key, switch_row.get_active())


class NetworksPage(Adw.Bin):
    """Lists every joined network and exposes join/leave/settings actions."""

    __gsignals__ = {
        "leave-requested": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "option-toggled": (GObject.SignalFlags.RUN_FIRST, None, (str, str, bool)),
        "copy-requested": (GObject.SignalFlags.RUN_FIRST, None, (str, str)),
    }

    def __init__(self):
        super().__init__()
        self._rows = {}

        self._empty = Adw.StatusPage(
            icon_name="network-workgroup-symbolic",
            title=_("No networks joined"),
            description=_(
                "Join a network with its 16-digit network ID. The network "
                "administrator still has to authorize this device before "
                "traffic flows."
            ),
        )

        self._group = Adw.PreferencesGroup()
        page = Adw.PreferencesPage()
        page.add(self._group)

        self._stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self._stack.add_named(self._empty, "empty")
        self._stack.add_named(page, "list")
        self.set_child(self._stack)

    def update(self, networks):
        """Reconcile the visible rows with a fresh ``/network`` payload."""
        seen = set()

        for network in networks:
            network_id = network.get("nwid") or network.get("id") or ""
            if not network_id:
                continue
            seen.add(network_id)

            row = self._rows.get(network_id)
            if row is None:
                row = NetworkRow(network_id)
                row.connect("leave-requested", self._forward, "leave-requested")
                row.connect("option-toggled", self._forward_option)
                row.connect("copy-requested", self._forward_copy)
                self._rows[network_id] = row
                self._group.add(row)
            row.update(network)

        for network_id in set(self._rows) - seen:
            self._group.remove(self._rows.pop(network_id))

        self._stack.set_visible_child_name("list" if self._rows else "empty")

    def _forward(self, _row, network_id, signal_name):
        self.emit(signal_name, network_id)

    def _forward_option(self, _row, network_id, option, value):
        self.emit("option-toggled", network_id, option, value)

    def _forward_copy(self, _row, value, message):
        self.emit("copy-requested", value, message)


class JoinDialog(Adw.AlertDialog):
    """Asks for a network ID and validates it before allowing submission."""

    def __init__(self, on_join):
        super().__init__(
            heading=_("Join a network"),
            body=_(
                "Enter the 16-digit network ID. The network administrator has "
                "to authorize this device before it can reach other members."
            ),
        )
        self._on_join = on_join

        self._entry = Adw.EntryRow(title=_("Network ID"))
        self._entry.connect("changed", self._on_changed)
        self._entry.connect("entry-activated", self._on_activated)

        group = Adw.PreferencesGroup()
        group.add(self._entry)
        self.set_extra_child(group)

        self.add_response("cancel", _("Cancel"))
        self.add_response("join", _("Join"))
        self.set_response_appearance("join", Adw.ResponseAppearance.SUGGESTED)
        self.set_response_enabled("join", False)
        self.set_default_response("join")
        self.set_close_response("cancel")
        self.connect("response", self._on_response)

    def _network_id(self):
        return self._entry.get_text().strip().lower()

    def _on_changed(self, entry):
        network_id = self._network_id()
        valid = is_valid_network_id(network_id)
        self.set_response_enabled("join", valid)
        if network_id and not valid:
            entry.add_css_class("error")
        else:
            entry.remove_css_class("error")

    def _on_activated(self, _entry):
        if is_valid_network_id(self._network_id()):
            self._on_join(self._network_id())
            self.close()

    def _on_response(self, _dialog, response):
        if response == "join" and is_valid_network_id(self._network_id()):
            self._on_join(self._network_id())

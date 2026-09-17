"""The Networks page: joined networks, their addresses and controls.

The window polls the daemon every few seconds. Rebuilding the rows on every
poll would collapse whatever the user has expanded and fight with switches they
are toggling, so rows are created once per network and afterwards updated in
place. Only networks that appear or disappear cause structural changes.
"""

from gi.repository import Adw, GObject, Gtk

from .util import format_network_status, is_valid_network_id

TOGGLES = (
    (
        "allowManaged",
        "Allow managed addresses",
        "Let the controller assign IP addresses on this interface.",
    ),
    (
        "allowGlobal",
        "Allow global routes",
        "Permit routes to public IP space.",
    ),
    (
        "allowDefault",
        "Allow default route",
        "Let this network carry all internet traffic.",
    ),
    (
        "allowDNS",
        "Allow DNS configuration",
        "Apply DNS servers published by the controller.",
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

        # A single, permanently ordered row: Adw.ExpanderRow.add_row() appends,
        # so rows must be created once, in their final order, and only have
        # their contents refreshed afterwards.
        self._addresses = []
        self._address_row = Adw.ActionRow(
            title="Managed IP", css_classes=["property"]
        )
        self._address_row.set_subtitle_lines(4)
        self._copy_button = Gtk.Button(
            icon_name="edit-copy-symbolic",
            tooltip_text="Copy address",
            valign=Gtk.Align.CENTER,
        )
        self._copy_button.add_css_class("flat")
        self._copy_button.connect("clicked", self._on_copy_clicked)
        self._address_row.add_suffix(self._copy_button)
        self.add_row(self._address_row)

        self._detail_rows = {}
        for key, title in (
            ("type", "Type"),
            ("portDeviceName", "Interface"),
            ("mac", "MAC address"),
            ("mtu", "MTU"),
        ):
            row = Adw.ActionRow(title=title, css_classes=["property"])
            self._detail_rows[key] = row
            self.add_row(row)

        self._switch_rows = {}
        for key, title, subtitle in TOGGLES:
            switch_row = Adw.SwitchRow(title=title, subtitle=subtitle)
            switch_row.connect("notify::active", self._on_toggle, key)
            self._switch_rows[key] = switch_row
            self.add_row(switch_row)

        leave_row = Adw.ActionRow(
            title="Leave this network",
            subtitle="Disconnects and removes the virtual interface.",
        )
        leave_button = Gtk.Button(label="Leave", valign=Gtk.Align.CENTER)
        leave_button.add_css_class("destructive-action")
        leave_button.connect(
            "clicked", lambda _b: self.emit("leave-requested", self.network_id)
        )
        leave_row.add_suffix(leave_button)
        self.add_row(leave_row)

    def update(self, network):
        self._applying_remote_state = True
        try:
            self.set_title(network.get("name") or "Unnamed network")

            status = network.get("status", "")
            self._badge.set_label(format_network_status(status))
            self._badge.remove_css_class("success")
            self._badge.remove_css_class("warning")
            self._badge.add_css_class("success" if status == "OK" else "warning")

            self._update_addresses(network.get("assignedAddresses") or [])

            values = {
                "type": (network.get("type") or "").replace("_", " ").title()
                or "Unknown",
                "portDeviceName": network.get("portDeviceName") or "Not created",
                "mac": network.get("mac") or "Unknown",
                "mtu": str(network.get("mtu") or "Unknown"),
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
            "Managed IPs" if len(addresses) > 1 else "Managed IP"
        )
        self._address_row.set_subtitle(
            "\n".join(addresses) if addresses else "Not assigned yet"
        )
        self._copy_button.set_visible(bool(addresses))
        self._copy_button.set_tooltip_text(
            "Copy addresses" if len(addresses) > 1 else "Copy address"
        )

    def _on_copy_clicked(self, _button):
        if not self._addresses:
            return
        # Strip the prefix length: what people paste elsewhere is the bare IP.
        bare = [address.split("/")[0] for address in self._addresses]
        message = "Addresses copied" if len(bare) > 1 else "Address copied"
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
            title="No networks joined",
            description=(
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
            heading="Join a network",
            body=(
                "Enter the 16-digit network ID. The network administrator has "
                "to authorize this device before it can reach other members."
            ),
        )
        self._on_join = on_join

        self._entry = Adw.EntryRow(title="Network ID")
        self._entry.connect("changed", self._on_changed)
        self._entry.connect("entry-activated", self._on_activated)

        group = Adw.PreferencesGroup()
        group.add(self._entry)
        self.set_extra_child(group)

        self.add_response("cancel", "Cancel")
        self.add_response("join", "Join")
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

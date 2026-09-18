"""The Device page: what this node is, for support and troubleshooting."""

from gi.repository import Adw, GObject, Gtk

from .i18n import _


class DevicePage(Adw.Bin):
    """Identity and health of the local ZeroTier node."""

    __gsignals__ = {
        "copy-requested": (GObject.SignalFlags.RUN_FIRST, None, (str, str)),
    }

    def __init__(self):
        super().__init__()
        self._status = {}

        page = Adw.PreferencesPage()

        identity = Adw.PreferencesGroup(
            title=_("This device"),
            description=_(
                "Give the node address to a network administrator when you "
                "need this device authorized."
            ),
        )

        self._address_row = Adw.ActionRow(
            title=_("Node address"), css_classes=["property"]
        )
        address_copy = Gtk.Button(
            icon_name="edit-copy-symbolic",
            tooltip_text=_("Copy node address"),
            valign=Gtk.Align.CENTER,
        )
        address_copy.add_css_class("flat")
        address_copy.connect(
            "clicked",
            lambda _b: self._copy("address", _("Node address copied")),
        )
        self._address_row.add_suffix(address_copy)
        identity.add(self._address_row)

        self._status_row = Adw.ActionRow(title=_("Status"), css_classes=["property"])
        identity.add(self._status_row)

        self._version_row = Adw.ActionRow(title=_("Version"), css_classes=["property"])
        identity.add(self._version_row)
        page.add(identity)

        connection = Adw.PreferencesGroup(title=_("Connection"))

        self._transport_row = Adw.ActionRow(
            title=_("Transport"), css_classes=["property"]
        )
        connection.add(self._transport_row)

        self._planet_row = Adw.ActionRow(
            title=_("Root servers"),
            subtitle=_("Unknown"),
            css_classes=["property"],
        )
        connection.add(self._planet_row)
        page.add(connection)

        advanced = Adw.PreferencesGroup(
            title=_("Identity"),
            description=_(
                "The public identity is safe to share. The matching secret key "
                "never leaves the ZeroTier service."
            ),
        )
        self._identity_row = Adw.ActionRow(
            title=_("Public identity"), css_classes=["property"]
        )
        self._identity_row.set_subtitle_lines(3)
        identity_copy = Gtk.Button(
            icon_name="edit-copy-symbolic",
            tooltip_text=_("Copy public identity"),
            valign=Gtk.Align.CENTER,
        )
        identity_copy.add_css_class("flat")
        identity_copy.connect(
            "clicked",
            lambda _b: self._copy("publicIdentity", _("Public identity copied")),
        )
        self._identity_row.add_suffix(identity_copy)
        advanced.add(self._identity_row)
        page.add(advanced)

        self.set_child(page)

    def update(self, status):
        self._status = status or {}

        address = self._status.get("address") or _("Unknown")
        self._address_row.set_subtitle(address)

        online = bool(self._status.get("online"))
        self._status_row.set_subtitle(_("Online") if online else _("Offline"))

        version = self._status.get("version") or ""
        build = self._status.get("versionBuild")
        if version and build not in (None, "", -1):
            # Translators: %(version)s is like "1.14.2", %(build)s a build number.
            text = _("%(version)s (build %(build)s)") % {
                "version": version,
                "build": build,
            }
        else:
            text = version or _("Unknown")
        self._version_row.set_subtitle(text)

        # tcpFallbackActive means UDP could not get through and traffic is
        # tunnelled over TCP, which is markedly slower. Worth calling out.
        tcp = bool(self._status.get("tcpFallbackActive"))
        self._transport_row.set_subtitle(
            _("TCP relay (slow fallback)") if tcp else _("UDP (direct)")
        )
        self._transport_row.remove_css_class("warning")
        if tcp:
            self._transport_row.add_css_class("warning")

        planet_id = self._status.get("planetWorldId")
        self._planet_row.set_subtitle(
            # Translators: %s is the numeric ID of the ZeroTier root server set.
            _("World %s") % planet_id if planet_id else _("Unknown")
        )

        public_identity = self._status.get("publicIdentity") or ""
        self._identity_row.set_subtitle(public_identity or _("Unknown"))

    def _copy(self, key, message):
        value = self._status.get(key)
        if value:
            self.emit("copy-requested", str(value), message)

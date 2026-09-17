"""First-run screen shown when no service token is readable."""

from gi.repository import Adw, Gdk, GObject, Gtk

from . import client

COPY_COMMAND = (
    "sudo cp /var/lib/zerotier-one/authtoken.secret "
    "~/.zeroTierOneAuthToken && "
    "sudo chown $USER ~/.zeroTierOneAuthToken && "
    "chmod 600 ~/.zeroTierOneAuthToken"
)


class SetupView(Adw.Bin):
    """Explains the one-time token setup and offers a manual paste fallback.

    Built on Adw.PreferencesPage rather than Adw.StatusPage: the content is
    taller than a small window, and a preferences page scrolls natively while a
    status page would simply clip its buttons.
    """

    __gsignals__ = {
        # Emitted once a token has been made available.
        "token-ready": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, toast_overlay):
        super().__init__()
        self._toasts = toast_overlay

        page = Adw.PreferencesPage()

        intro = Adw.PreferencesGroup()
        intro.add(self._build_intro())
        page.add(intro)

        command_group = Adw.PreferencesGroup(
            title="Run this in a terminal",
            description=(
                "This is the procedure documented in the zerotier-cli manual "
                "page. Anyone who can read the token can join or leave "
                "networks on this machine, so keep the copy private."
            ),
        )
        command_group.add(self._build_command_row())
        page.add(command_group)

        manual_group = Adw.PreferencesGroup(
            title="Or paste the token directly",
            description=(
                "ZTDeck stores it in its own configuration directory with "
                "owner-only permissions."
            ),
        )
        self._entry = Adw.PasswordEntryRow(title="Service token")
        self._entry.connect("entry-activated", lambda *_: self._save_token())
        manual_group.add(self._entry)
        manual_group.add(self._build_buttons())
        page.add(manual_group)

        self.set_child(page)

    # -- construction -----------------------------------------------------

    def _build_intro(self):
        icon = Gtk.Image.new_from_icon_name("dialog-password-symbolic")
        icon.set_pixel_size(96)
        icon.add_css_class("dim-label")
        icon.set_margin_top(12)

        title = Gtk.Label(label="Grant access to ZeroTier", wrap=True)
        title.add_css_class("title-1")
        title.set_margin_top(12)

        description = Gtk.Label(
            label=(
                "The ZeroTier service protects its control API with a token "
                "that only the root user can read. Give your user account a "
                "copy once, and ZTDeck will pick it up automatically."
            ),
            wrap=True,
            justify=Gtk.Justification.CENTER,
        )
        description.add_css_class("body")
        description.add_css_class("dim-label")
        description.set_margin_top(6)
        description.set_margin_bottom(12)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, halign=Gtk.Align.CENTER)
        box.append(icon)
        box.append(title)
        box.append(description)
        return box

    def _build_command_row(self):
        row = Adw.ActionRow(title="Copy the service token")
        # The command contains '&&', which Pango would otherwise parse as
        # markup, so markup has to be disabled before the subtitle is set.
        row.set_use_markup(False)
        row.set_subtitle_lines(4)
        row.set_subtitle(COPY_COMMAND)
        row.add_css_class("property")
        row.add_css_class("monospace")

        copy_button = Gtk.Button(
            icon_name="edit-copy-symbolic",
            tooltip_text="Copy command to clipboard",
            valign=Gtk.Align.CENTER,
        )
        copy_button.add_css_class("flat")
        copy_button.connect("clicked", self._on_copy_clicked)
        row.add_suffix(copy_button)
        return row

    def _build_buttons(self):
        save_button = Gtk.Button(label="Save token")
        save_button.add_css_class("suggested-action")
        save_button.add_css_class("pill")
        save_button.connect("clicked", lambda *_: self._save_token())

        retry_button = Gtk.Button(label="Check again")
        retry_button.add_css_class("pill")
        retry_button.connect("clicked", lambda *_: self._check_again())

        box = Gtk.Box(spacing=12, halign=Gtk.Align.CENTER)
        box.set_margin_top(18)
        box.append(save_button)
        box.append(retry_button)
        return box

    # -- actions ----------------------------------------------------------

    def _toast(self, message):
        self._toasts.add_toast(Adw.Toast(title=message))

    def _on_copy_clicked(self, _button):
        Gdk.Display.get_default().get_clipboard().set(COPY_COMMAND)
        self._toast("Command copied to clipboard")

    def _save_token(self):
        token = self._entry.get_text().strip()
        if not token:
            self._toast("Enter the token first")
            return
        try:
            client.store_token(token)
        except (OSError, ValueError) as exc:
            self._toast(f"Could not save the token: {exc}")
            return
        self._entry.set_text("")
        self.emit("token-ready")

    def _check_again(self):
        if client.read_token():
            self.emit("token-ready")
        else:
            self._toast("Still no readable token found")

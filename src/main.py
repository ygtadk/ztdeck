"""Application entry point."""

import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from .window import ZTDeckWindow  # noqa: E402


class ZTDeckApplication(Adw.Application):
    def __init__(self, version, app_id):
        super().__init__(
            application_id=app_id,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.version = version
        self.app_id = app_id

        self.create_action("quit", self.on_quit, ["<primary>q"])
        self.create_action("about", self.on_about)
        self.create_action("refresh", self.on_refresh, ["<primary>r", "F5"])

    def do_activate(self):
        window = self.props.active_window
        if not window:
            window = ZTDeckWindow(application=self)
        window.present()

    def create_action(self, name, callback, shortcuts=None):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)

    def on_quit(self, *_args):
        self.quit()

    def on_refresh(self, *_args):
        window = self.props.active_window
        if window is not None:
            window.refresh(user_initiated=True)

    def on_about(self, *_args):
        about = Adw.AboutDialog(
            application_name="ZTDeck",
            application_icon=self.app_id,
            developer_name="Yiğit Adak",
            version=self.version,
            website="https://github.com/ygtadk/ztdeck",
            issue_url="https://github.com/ygtadk/ztdeck/issues",
            license_type=Gtk.License.MIT_X11,
            comments=(
                "An unofficial desktop client for the ZeroTier One service.\n\n"
                "ZTDeck talks to the ZeroTier daemon already running on this "
                "machine through its local control API. It is not affiliated "
                "with or endorsed by ZeroTier, Inc."
            ),
        )
        about.present(self.props.active_window)


def run(version, app_id):
    app = ZTDeckApplication(version, app_id)
    return app.run(sys.argv)

"""Main application window."""

from gi.repository import Adw, Gdk, GLib, Gtk

from . import client
from .client import ZeroTierClient, ZeroTierError
from .networks import JoinDialog, NetworksPage
from .peers import PeersPage
from .setup_view import SetupView
from .util import run_async

REFRESH_INTERVAL_SECONDS = 3


class ZTDeckWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("ZTDeck")
        self.set_default_size(880, 680)
        self.set_size_request(360, 480)

        self._client = ZeroTierClient()
        self._refresh_source = None
        self._request_in_flight = False
        self._node_address = None

        self._toasts = Adw.ToastOverlay()
        self._build_ui()
        self.set_content(self._toasts)

        self._decide_view()

    # -- construction -----------------------------------------------------

    def _build_ui(self):
        self._join_button = Gtk.Button(
            icon_name="list-add-symbolic", tooltip_text="Join a network"
        )
        self._join_button.connect("clicked", self._on_join_clicked)

        menu = Gtk.MenuButton(
            icon_name="open-menu-symbolic", tooltip_text="Main menu"
        )
        popover = Gtk.PopoverMenu.new_from_model(self._build_menu_model())
        menu.set_popover(popover)

        # On wide windows the view switcher occupies the title slot, so the node
        # identity moves into a small pill next to the menu button.
        self._status_dot = Gtk.Image.new_from_icon_name("media-record-symbolic")
        self._status_pill_label = Gtk.Label()
        self._status_pill_label.add_css_class("caption")
        pill_box = Gtk.Box(spacing=6)
        pill_box.append(self._status_dot)
        pill_box.append(self._status_pill_label)
        self._status_pill = Gtk.Button(child=pill_box)
        self._status_pill.add_css_class("flat")
        self._status_pill.set_tooltip_text("Copy this node's address")
        self._status_pill.connect("clicked", self._on_copy_address)

        title = Adw.WindowTitle(title="ZTDeck", subtitle="Not connected")
        self._window_title = title

        header = Adw.HeaderBar(title_widget=title)
        header.pack_start(self._join_button)
        header.pack_end(menu)
        header.pack_end(self._status_pill)

        self._networks_page = NetworksPage()
        self._networks_page.connect("leave-requested", self._on_leave_requested)
        self._networks_page.connect("option-toggled", self._on_option_toggled)
        self._networks_page.connect("copy-requested", self._on_copy_requested)

        self._peers_page = PeersPage()

        self._view_stack = Adw.ViewStack()
        self._view_stack.add_titled_with_icon(
            self._networks_page, "networks", "Networks", "network-workgroup-symbolic"
        )
        self._view_stack.add_titled_with_icon(
            self._peers_page, "peers", "Peers", "network-transmit-receive-symbolic"
        )

        # Wide windows get the switcher in the header bar; narrow ones get it
        # as a bottom bar, which is the reachable place on a phone-sized window.
        self._switcher = Adw.ViewSwitcher(
            stack=self._view_stack, policy=Adw.ViewSwitcherPolicy.WIDE
        )
        header.set_title_widget(self._switcher)

        self._switcher_bar = Adw.ViewSwitcherBar(stack=self._view_stack)

        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header)
        toolbar_view.set_content(self._view_stack)
        toolbar_view.add_bottom_bar(self._switcher_bar)
        self._main_view = toolbar_view

        breakpoint_ = Adw.Breakpoint.new(
            Adw.BreakpointCondition.parse("max-width: 550sp")
        )
        breakpoint_.add_setter(header, "title-widget", self._window_title)
        breakpoint_.add_setter(self._switcher_bar, "reveal", True)
        self.add_breakpoint(breakpoint_)

        self._setup_view = SetupView(self._toasts)
        self._setup_view.connect("token-ready", self._on_token_ready)

        setup_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        setup_header = Adw.HeaderBar(
            title_widget=Adw.WindowTitle(title="ZTDeck", subtitle="Setup required")
        )
        setup_header.add_css_class("flat")
        setup_box.append(setup_header)
        setup_box.append(self._setup_view)
        self._setup_container = setup_box

        self._root_stack = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.CROSSFADE
        )
        self._root_stack.add_named(self._setup_container, "setup")
        self._root_stack.add_named(self._main_view, "main")
        self._toasts.set_child(self._root_stack)

        self._error_page = Adw.StatusPage(
            icon_name="network-offline-symbolic", title="", description=""
        )
        retry = Gtk.Button(label="Try again", halign=Gtk.Align.CENTER)
        retry.add_css_class("pill")
        retry.add_css_class("suggested-action")
        retry.connect("clicked", lambda *_: self.refresh(user_initiated=True))
        self._error_page.set_child(retry)

        error_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        error_header = Adw.HeaderBar(
            title_widget=Adw.WindowTitle(title="ZTDeck", subtitle="Disconnected")
        )
        error_header.add_css_class("flat")
        error_box.append(error_header)
        error_box.append(self._error_page)
        self._root_stack.add_named(error_box, "error")

    def _build_menu_model(self):
        from gi.repository import Gio

        menu = Gio.Menu()
        section = Gio.Menu()
        section.append("Refresh", "app.refresh")
        menu.append_section(None, section)
        about_section = Gio.Menu()
        about_section.append("About ZTDeck", "app.about")
        about_section.append("Quit", "app.quit")
        menu.append_section(None, about_section)
        return menu

    # -- view routing -----------------------------------------------------

    def _decide_view(self):
        if self._client.reload_token():
            self._root_stack.set_visible_child_name("main")
            self.refresh(user_initiated=True)
            self._start_polling()
        else:
            self._stop_polling()
            self._root_stack.set_visible_child_name("setup")

    def _on_token_ready(self, _view):
        self._toast("Token accepted")
        self._decide_view()

    def _show_error(self, error):
        title = getattr(error, "title", "Something went wrong")
        hint = getattr(error, "hint", "") or str(error)
        self._error_page.set_title(title)
        self._error_page.set_description(hint)
        self._root_stack.set_visible_child_name("error")

    # -- polling ----------------------------------------------------------

    def _start_polling(self):
        if self._refresh_source is None:
            self._refresh_source = GLib.timeout_add_seconds(
                REFRESH_INTERVAL_SECONDS, self._on_tick
            )

    def _stop_polling(self):
        if self._refresh_source is not None:
            GLib.source_remove(self._refresh_source)
            self._refresh_source = None

    def _on_tick(self):
        self.refresh()
        return GLib.SOURCE_CONTINUE

    def refresh(self, user_initiated=False):
        """Pull a fresh snapshot from the daemon on a worker thread."""
        if self._request_in_flight:
            return
        if not self._client.has_token:
            self._decide_view()
            return
        self._request_in_flight = True
        run_async(
            self._client.snapshot,
            lambda result, error: self._on_snapshot(result, error, user_initiated),
        )

    def _on_snapshot(self, snapshot, error, user_initiated):
        self._request_in_flight = False
        if error is not None:
            if isinstance(error, client.TokenMissingError):
                self._decide_view()
            else:
                self._show_error(error)
            return

        if self._root_stack.get_visible_child_name() != "main":
            self._root_stack.set_visible_child_name("main")
            self._start_polling()

        status = snapshot.get("status") or {}
        networks = snapshot.get("networks") or []
        peers = snapshot.get("peers") or []

        online = bool(status.get("online"))
        address = status.get("address", "unknown")
        version = status.get("version", "")

        self._node_address = address
        state = "Online" if online else "Offline"
        subtitle = f"{address}  ·  {state}"
        if version:
            subtitle += f"  ·  v{version}"
        self._window_title.set_subtitle(subtitle)

        self._status_pill_label.set_label(address)
        self._status_dot.remove_css_class("success")
        self._status_dot.remove_css_class("dim-label")
        self._status_dot.add_css_class("success" if online else "dim-label")
        self._status_pill.set_tooltip_text(
            f"{state}{f' · v{version}' if version else ''} — click to copy {address}"
        )

        self._networks_page.update(networks)
        self._peers_page.update(peers)

        if user_initiated:
            self._toast("Refreshed")
        return False

    # -- actions ----------------------------------------------------------

    def _toast(self, message):
        self._toasts.add_toast(Adw.Toast(title=message, timeout=2))

    def _on_copy_address(self, _button):
        if self._node_address:
            Gdk.Display.get_default().get_clipboard().set(self._node_address)
            self._toast("Node address copied")

    def _on_copy_requested(self, _page, value, message):
        Gdk.Display.get_default().get_clipboard().set(value)
        self._toast(message)

    def _on_join_clicked(self, _button):
        dialog = JoinDialog(self._join_network)
        dialog.present(self)

    def _join_network(self, network_id):
        run_async(
            lambda: self._client.join_network(network_id),
            lambda _result, error: self._on_action_done(
                error, f"Joined {network_id}"
            ),
        )

    def _on_leave_requested(self, _page, network_id):
        dialog = Adw.AlertDialog(
            heading="Leave this network?",
            body=(
                f"ZTDeck will disconnect from {network_id} and remove its "
                "virtual interface. You can join again at any time."
            ),
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("leave", "Leave")
        dialog.set_response_appearance("leave", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect(
            "response",
            lambda _d, response, nwid=network_id: (
                self._leave_network(nwid) if response == "leave" else None
            ),
        )
        dialog.present(self)

    def _leave_network(self, network_id):
        run_async(
            lambda: self._client.leave_network(network_id),
            lambda _result, error: self._on_action_done(error, f"Left {network_id}"),
        )

    def _on_option_toggled(self, _page, network_id, option, value):
        run_async(
            lambda: self._client.set_network_option(network_id, option, value),
            lambda _result, error: self._on_action_done(error, None),
        )

    def _on_action_done(self, error, message):
        if error is not None:
            title = getattr(error, "title", None) or str(error)
            self._toast(title)
        elif message:
            self._toast(message)
        self.refresh()
        return False

    def do_close_request(self):
        self._stop_polling()
        return False

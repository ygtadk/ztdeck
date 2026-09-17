#!/usr/bin/env python3
"""Functional tests for ZTDeck against the mock ZeroTier API.

Run the mock daemon first, then:

    MOCK_PORT=19993 python3 tests/mock_daemon.py &
    ZTDECK_PORT=19993 ZTDECK_TOKEN_FILE=/tmp/ztdeck-mock-token \
        python3 tests/test_ztdeck.py

The widget tests need a display; GDK_BACKEND=broadway works headlessly.
"""

import importlib.util
import os
import sys

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
SRC = os.path.normpath(SRC)

spec = importlib.util.spec_from_file_location(
    "ztdeck", os.path.join(SRC, "__init__.py"), submodule_search_locations=[SRC]
)
package = importlib.util.module_from_spec(spec)
sys.modules["ztdeck"] = package
spec.loader.exec_module(package)

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ztdeck import client as client_module  # noqa: E402
from ztdeck.networks import JoinDialog, NetworksPage  # noqa: E402
from ztdeck.peers import PeersPage  # noqa: E402
from ztdeck.util import (  # noqa: E402
    format_latency,
    format_network_status,
    is_valid_network_id,
)

FAILURES = []


def check(condition, label):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


def test_helpers():
    check(is_valid_network_id("8056c2e21c000001"), "valid network ID accepted")
    check(not is_valid_network_id("8056c2e21c00000"), "15-digit ID rejected")
    check(not is_valid_network_id("8056c2e21c0000011"), "17-digit ID rejected")
    check(not is_valid_network_id("8056c2e21c00000z"), "non-hex ID rejected")
    check(is_valid_network_id("  8056C2E21C000001 "), "ID is trimmed and lowercased")
    check(format_latency(-1) == "unknown", "negative latency hidden")
    check(format_latency(12) == "12 ms", "latency formatted")
    check(format_latency(None) == "unknown", "missing latency handled")
    check(
        format_network_status("REQUESTING_CONFIGURATION") == "Requesting configuration",
        "status code humanised",
    )


def test_client():
    zt = client_module.ZeroTierClient()
    status = zt.status()
    check(status.get("address") == "a9b8c7d6e5", "status returns node address")
    check(status.get("online") is True, "node reported online")

    networks = zt.networks()
    check(len(networks) == 2, "two networks listed")

    zt.join_network("abcdef0123456789")
    check(len(zt.networks()) == 3, "join adds a network")

    zt.set_network_option("abcdef0123456789", "allowDefault", True)
    joined = [n for n in zt.networks() if n["nwid"] == "abcdef0123456789"][0]
    check(joined["allowDefault"] is True, "option write persists")

    zt.leave_network("abcdef0123456789")
    check(len(zt.networks()) == 2, "leave removes the network")

    peers = zt.peers()
    check(len(peers) == 3, "three peers listed")

    snapshot = zt.snapshot()
    check(
        set(snapshot) == {"status", "networks", "peers"},
        "snapshot bundles all three payloads",
    )


def test_bad_token():
    zt = client_module.ZeroTierClient()
    zt._token = "definitely-not-the-token"  # noqa: SLF001 - deliberate
    try:
        zt.status()
    except client_module.AuthFailedError:
        check(True, "bad token raises AuthFailedError")
    else:
        check(False, "bad token raises AuthFailedError")


def test_daemon_down():
    zt = client_module.ZeroTierClient(port=19999)
    zt._token = "anything"  # noqa: SLF001
    try:
        zt.status()
    except client_module.DaemonUnreachableError:
        check(True, "closed port raises DaemonUnreachableError")
    else:
        check(False, "closed port raises DaemonUnreachableError")


def test_missing_token():
    zt = client_module.ZeroTierClient()
    zt._token = None  # noqa: SLF001
    original = client_module.read_token
    client_module.read_token = lambda: None
    try:
        zt.status()
    except client_module.TokenMissingError:
        check(True, "absent token raises TokenMissingError")
    else:
        check(False, "absent token raises TokenMissingError")
    finally:
        client_module.read_token = original


def _rows_of(group):
    """Return the list rows Libadwaita put inside a PreferencesGroup."""
    found = []

    def walk(widget):
        child = widget.get_first_child()
        while child is not None:
            if isinstance(child, Gtk.ListBoxRow) and not isinstance(
                child.get_parent(), Adw.ExpanderRow
            ):
                found.append(child)
            walk(child)
            child = child.get_next_sibling()

    walk(group)
    return found


def test_networks_page():
    page = NetworksPage()
    payload = [
        {
            "nwid": "8056c2e21c000001",
            "name": "Earth",
            "status": "OK",
            "type": "PUBLIC",
            "assignedAddresses": ["29.155.34.12/7"],
            "allowManaged": True,
        },
        {
            "nwid": "1c33939e5f1a2b3c",
            "name": "Home Lab",
            "status": "REQUESTING_CONFIGURATION",
            "type": "PRIVATE",
            "assignedAddresses": [],
        },
    ]
    page.update(payload)
    first_ids = {nid: id(row) for nid, row in page._rows.items()}  # noqa: SLF001
    check(len(page._rows) == 2, "two network rows created")  # noqa: SLF001

    # A second identical poll must not recreate the rows: that is what used to
    # collapse the expander every few seconds.
    page.update(payload)
    second_ids = {nid: id(row) for nid, row in page._rows.items()}  # noqa: SLF001
    check(first_ids == second_ids, "rows are reused across polls")

    row = page._rows["8056c2e21c000001"]  # noqa: SLF001
    check(row.get_title() == "Earth", "row title from payload")
    check(
        row._address_row.get_subtitle() == "29.155.34.12/7",  # noqa: SLF001
        "managed address rendered",
    )

    renamed = [dict(payload[0], name="Earth Renamed"), payload[1]]
    page.update(renamed)
    check(row.get_title() == "Earth Renamed", "row updates in place")
    check(
        id(page._rows["8056c2e21c000001"]) == first_ids["8056c2e21c000001"],  # noqa: SLF001
        "renaming does not recreate the row",
    )

    page.update([payload[0]])
    check(len(page._rows) == 1, "left network removed from the list")  # noqa: SLF001

    page.update([])
    check(
        page._stack.get_visible_child_name() == "empty",  # noqa: SLF001
        "empty state shown with no networks",
    )


def test_toggle_signal_not_emitted_by_refresh():
    """Refreshing must not look like the user flipping a switch."""
    page = NetworksPage()
    base = {
        "nwid": "8056c2e21c000001",
        "name": "Earth",
        "status": "OK",
        "allowManaged": False,
        "assignedAddresses": [],
    }
    page.update([base])

    emitted = []
    page.connect(
        "option-toggled",
        lambda _p, nwid, key, value: emitted.append((nwid, key, value)),
    )

    # Remote state flips; this must stay silent.
    page.update([dict(base, allowManaged=True)])
    check(not emitted, "remote state change does not emit option-toggled")

    # A genuine user interaction must be reported.
    row = page._rows["8056c2e21c000001"]  # noqa: SLF001
    row._switch_rows["allowGlobal"].set_active(True)  # noqa: SLF001
    check(
        emitted == [("8056c2e21c000001", "allowGlobal", True)],
        "user toggle emits option-toggled",
    )


def test_peers_page():
    page = PeersPage()
    peers = [
        {
            "address": "2f4c1b9a03",
            "role": "LEAF",
            "latency": 12,
            "version": "1.14.1",
            "paths": [{"address": "192.168.1.44/9993", "active": True}],
        },
        {"address": "8b31ff0c52", "role": "LEAF", "latency": -1, "paths": []},
    ]
    page.update(peers)
    check(len(page._rows) == 2, "two peer rows created")  # noqa: SLF001

    ids = {addr: id(row) for addr, row in page._rows.items()}  # noqa: SLF001
    page.update(peers)
    check(
        ids == {addr: id(row) for addr, row in page._rows.items()},  # noqa: SLF001
        "peer rows reused across polls",
    )

    direct = page._rows["2f4c1b9a03"]  # noqa: SLF001
    check("Direct" in direct.get_subtitle(), "active path reported as direct")
    check("12 ms" in direct.get_subtitle(), "latency shown for direct peer")

    relayed = page._rows["8b31ff0c52"]  # noqa: SLF001
    check("Relayed" in relayed.get_subtitle(), "pathless peer reported as relayed")
    check("unknown" in relayed.get_subtitle(), "unknown latency not shown as -1")

    page.update([])
    check(
        page._stack.get_visible_child_name() == "empty",  # noqa: SLF001
        "empty state shown with no peers",
    )


def test_join_dialog():
    captured = []
    dialog = JoinDialog(captured.append)

    check(not dialog.get_response_enabled("join"), "Join disabled while empty")

    dialog._entry.set_text("not-hex")  # noqa: SLF001
    check(not dialog.get_response_enabled("join"), "Join disabled for invalid ID")
    check(dialog._entry.has_css_class("error"), "invalid ID marked with error style")  # noqa: SLF001

    dialog._entry.set_text("8056c2e21c000001")  # noqa: SLF001
    check(dialog.get_response_enabled("join"), "Join enabled for valid ID")
    check(
        not dialog._entry.has_css_class("error"),  # noqa: SLF001
        "error style cleared once valid",
    )

    dialog.emit("response", "join")
    check(captured == ["8056c2e21c000001"], "join callback receives the network ID")

    captured.clear()
    dialog.emit("response", "cancel")
    check(not captured, "cancel does not join")


def main():
    Adw.init()

    test_helpers()
    test_client()
    test_bad_token()
    test_daemon_down()
    test_missing_token()
    test_networks_page()
    test_toggle_signal_not_emitted_by_refresh()
    test_peers_page()
    test_join_dialog()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} failing check(s):")
        for label in FAILURES:
            print(f"  - {label}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

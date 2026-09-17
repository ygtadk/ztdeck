#!/usr/bin/env python3
"""A tiny stand-in for the ZeroTier One local API.

Useful for developing the UI without touching the real service:

    python3 tests/mock_daemon.py &
    ZTDECK_PORT=19993 ZTDECK_TOKEN_FILE=/tmp/ztdeck-mock-token python3 -m ztdeck
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN = "mocktoken0123456789"
PORT = int(os.environ.get("MOCK_PORT", 19993))

STATE = {
    "status": {
        "address": "a9b8c7d6e5",
        "online": True,
        "version": "1.14.2",
        "tcpFallbackActive": False,
    },
    "networks": {
        "8056c2e21c000001": {
            "nwid": "8056c2e21c000001",
            "id": "8056c2e21c000001",
            "name": "Earth",
            "status": "OK",
            "type": "PUBLIC",
            "mac": "36:1a:88:cd:42:0b",
            "mtu": 2800,
            "portDeviceName": "ztuguzll4t",
            "assignedAddresses": ["29.155.34.12/7"],
            "allowManaged": True,
            "allowGlobal": False,
            "allowDefault": False,
            "allowDNS": False,
        },
        "1c33939e5f1a2b3c": {
            "nwid": "1c33939e5f1a2b3c",
            "id": "1c33939e5f1a2b3c",
            "name": "Home Lab",
            "status": "REQUESTING_CONFIGURATION",
            "type": "PRIVATE",
            "mac": "92:4f:11:ab:cd:7e",
            "mtu": 2800,
            "portDeviceName": "",
            "assignedAddresses": [],
            "allowManaged": True,
            "allowGlobal": False,
            "allowDefault": False,
            "allowDNS": True,
        },
    },
    "peers": [
        {
            "address": "778cde7190",
            "role": "PLANET",
            "latency": 41,
            "version": "1.14.2",
            "paths": [{"address": "103.195.103.66/9993", "active": True, "preferred": True}],
        },
        {
            "address": "2f4c1b9a03",
            "role": "LEAF",
            "latency": 12,
            "version": "1.14.1",
            "paths": [{"address": "192.168.1.44/9993", "active": True, "preferred": True}],
        },
        {
            "address": "8b31ff0c52",
            "role": "LEAF",
            "latency": -1,
            "version": "-1.-1.-1",
            "paths": [],
        },
    ],
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def _authorized(self):
        if self.headers.get("X-ZT1-Auth") == TOKEN:
            return True
        self.send_response(401)
        self.end_headers()
        return False

    def _send(self, payload):
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self._authorized():
            return
        if self.path == "/status":
            self._send(STATE["status"])
        elif self.path == "/network":
            self._send(list(STATE["networks"].values()))
        elif self.path == "/peer":
            self._send(STATE["peers"])
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if not self._authorized():
            return
        nwid = self.path.rsplit("/", 1)[-1]
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        network = STATE["networks"].setdefault(
            nwid,
            {
                "nwid": nwid,
                "id": nwid,
                "name": "New network",
                "status": "REQUESTING_CONFIGURATION",
                "type": "PRIVATE",
                "mac": "00:00:00:00:00:00",
                "mtu": 2800,
                "portDeviceName": "",
                "assignedAddresses": [],
                "allowManaged": True,
                "allowGlobal": False,
                "allowDefault": False,
                "allowDNS": False,
            },
        )
        network.update(body)
        self._send(network)

    def do_DELETE(self):
        if not self._authorized():
            return
        nwid = self.path.rsplit("/", 1)[-1]
        STATE["networks"].pop(nwid, None)
        self._send({})


if __name__ == "__main__":
    token_file = os.environ.get("MOCK_TOKEN_FILE", "/tmp/ztdeck-mock-token")
    with open(token_file, "w", encoding="utf-8") as handle:
        handle.write(TOKEN)
    os.chmod(token_file, 0o600)
    print(f"mock ZeroTier API on 127.0.0.1:{PORT}, token file {token_file}", flush=True)
    try:
        HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)

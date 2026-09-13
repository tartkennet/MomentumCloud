"""Small health endpoint used by the dashboard and deployment checks."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        root = Path(__file__).resolve().parents[1]
        snapshot = root / "public" / "data" / "dashboard.json"
        payload = {"status": "ok" if snapshot.exists() else "waiting", "snapshot": snapshot.exists()}
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200 if snapshot.exists() else 503)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


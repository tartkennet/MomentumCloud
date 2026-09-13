"""Vercel serverless endpoint for the latest verified dashboard snapshot."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = Path(__file__).resolve().parents[1] / "public" / "data" / "dashboard.json"
        if not path.exists():
            self.send_response(503)
            payload = {"error": "No successful production snapshot is available yet"}
        else:
            self.send_response(200)
            payload = json.loads(path.read_text(encoding="utf-8"))
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "public, max-age=60, stale-while-revalidate=300")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


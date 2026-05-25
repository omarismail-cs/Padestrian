"""Local dev server for the Padestrian map viewer."""

import json
import mimetypes
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from padestrian.config import require_env
from padestrian.paths import DATA_DIR, MAPBOX_CONFIG_JS, WEB_DIR

DEFAULT_PORT = 8765


def write_config_js() -> str:
    """Write web/config.js from .env (loaded by index.html before app.js)."""
    token = require_env("MAPBOX_ACCESS_TOKEN", fresh=True)
    MAPBOX_CONFIG_JS.write_text(
        f"window.PADESTRIAN_MAPBOX_TOKEN = {json.dumps(token)};\n",
        encoding="utf-8",
    )
    return token


def _safe_file(base: Path, relative: str) -> Path | None:
    relative = unquote(relative).lstrip("/").replace("\\", "/")
    if not relative or ".." in relative.split("/"):
        return None
    target = (base / relative).resolve()
    try:
        target.relative_to(base.resolve())
    except ValueError:
        return None
    return target


class PadestrianHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        print(f"[serve] {self.address_string()} - {format % args}")

    def _send_bytes(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        if not path.is_file():
            self.send_error(404, "Not found")
            return
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self._send_bytes(200, path.read_bytes(), content_type)

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path.startswith("/data/"):
            target = _safe_file(DATA_DIR, path[len("/data/") :])
            if target is None:
                self.send_error(403, "Forbidden")
                return
            self._send_file(target)
            return

        if path in ("", "/"):
            path = "/index.html"

        target = _safe_file(WEB_DIR, path.lstrip("/"))
        if target is None:
            self.send_error(403, "Forbidden")
            return
        self._send_file(target)


def run_server(port: int = DEFAULT_PORT, *, open_browser: bool = True) -> None:
    if not WEB_DIR.is_dir():
        raise RuntimeError(f"Web directory missing: {WEB_DIR}")

    url = f"http://127.0.0.1:{port}/"
    server = ThreadingHTTPServer(("127.0.0.1", port), PadestrianHandler)

    try:
        token = write_config_js()
        token_hint = f"…{token[-6:]}"
    except RuntimeError as exc:
        raise SystemExit(f"Cannot start: {exc}") from exc

    print(f"Padestrian map: {url}")
    print(f"Mapbox token: pk.{token_hint}  (see /config.js)")
    print("Press Ctrl+C to stop. Restart serve after editing .env.")

    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()

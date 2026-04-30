# dissyslab/components/sources/webhook_source.py
"""
Webhook Source — Listen for inbound HTTP POSTs and yield each as
a DisSysLab message.

This is the only push-style source in DisSysLab — every other
source pulls (RSS, BlueSky, Gmail). The webhook source spins up a
threaded HTTP listener; each incoming POST becomes a message.

Setup:
    No setup. The source spins up a stdlib HTTP server. You point
    the *poster* (the upstream service) at the URL DisSysLab is
    listening on.

    For local testing: poster and source on the same machine,
    URL = http://localhost:8000/webhook

    For off-machine reachability (a real third-party webhook):
    use ngrok (`ngrok http 8000`) or cloudflared, copy the public
    URL, paste into the upstream service's webhook configuration.

Example office.md:
    Sources: webhook
    Sources: webhook(port=9000, path="/incoming")

Example Python:
    from dissyslab.components.sources.webhook_source import WebhookSource
    from dissyslab.blocks import Source

    source = WebhookSource(port=8000)
    node = Source(fn=source.run, name="webhook_in")

Each yielded message:
    {
        "source":    "webhook",
        "title":     ...,           # from JSON body if present
        "text":      ...,           # from JSON body if present, else raw body
        "url":       ...,           # from JSON body if present
        "timestamp": "<ISO 8601>",  # arrival time
        # plus every other key from the JSON body, passed through
    }

Security:
    The default bind host is 127.0.0.1 (localhost only). To accept
    posts from other machines, pass host="0.0.0.0", but understand
    that anyone who can reach the port can inject messages. For
    production, run behind a reverse proxy that does TLS and
    authentication, or restrict the firewall to specific source IPs.
"""

import json
import queue
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class WebhookSource:
    """
    Listen for inbound HTTP POSTs and yield each as a DisSysLab
    message dict.

    The HTTP listener runs in a daemon thread; the generator pops
    messages off a thread-safe queue. Stops cleanly on Ctrl+C
    (the daemon thread dies with the process).

    Args:
        port:    TCP port to listen on (default 8000).
        path:    URL path that triggers a message; other paths
                 return 404 (default "/webhook").
        host:    Interface to bind. Defaults to "127.0.0.1"
                 (localhost only). Use "0.0.0.0" to accept posts
                 from other machines, but read the security note
                 in the module docstring first.
    """

    def __init__(
        self,
        port: int = 8000,
        path: str = "/webhook",
        host: str = "127.0.0.1",
    ):
        self.port = int(port)
        self.path = path if path.startswith("/") else "/" + path
        self.host = host

        self._queue: "queue.Queue[dict]" = queue.Queue()
        self._server: ThreadingHTTPServer = None
        self._server_thread: threading.Thread = None
        self.posts_received = 0

    # ── Message building ──────────────────────────────────────────────────────

    def _build_message(self, body: bytes, content_type: str) -> dict:
        """
        Convert a raw POST body into a DisSysLab message dict with
        the standard 5-key shape. JSON bodies are parsed and merged
        with the default keys; non-JSON bodies become the `text`.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        try:
            text_body = body.decode("utf-8", errors="replace")
        except Exception:
            text_body = ""

        data = None
        if "json" in (content_type or "").lower():
            try:
                data = json.loads(text_body)
            except json.JSONDecodeError:
                data = None

        # JSON dict → merge passed-through keys, fill standard keys.
        if isinstance(data, dict):
            return {
                "source":    "webhook",
                "title":     data.get("title", data.get("subject", "")),
                "text":      data.get("text", text_body),
                "url":       data.get("url", ""),
                "timestamp": data.get("timestamp", timestamp),
                **{
                    k: v for k, v in data.items()
                    if k not in {"source", "title", "text", "url", "timestamp"}
                },
            }

        # JSON list or scalar → wrap as text.
        if data is not None:
            return {
                "source":    "webhook",
                "title":     "",
                "text":      json.dumps(data),
                "url":       "",
                "timestamp": timestamp,
            }

        # Non-JSON (form data, plain text, anything else) → raw body.
        return {
            "source":    "webhook",
            "title":     "",
            "text":      text_body,
            "url":       "",
            "timestamp": timestamp,
        }

    # ── HTTP handler ──────────────────────────────────────────────────────────

    def _make_handler(self):
        """
        Build a request handler closed over this WebhookSource.
        Each handler instance is created per-request by the server,
        so we use a closure rather than instance state on the handler.
        """
        outer = self

        class _Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path != outer.path:
                    self.send_response(404)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(b"not found\n")
                    return

                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length > 0 else b""
                content_type = self.headers.get("Content-Type", "")

                msg = outer._build_message(body, content_type)
                outer._queue.put(msg)

                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"ok\n")

            def do_GET(self):
                # A friendly health check for humans visiting the URL
                # in a browser. Anything other than the configured
                # path 404s.
                if self.path == outer.path:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(
                        b"DisSysLab webhook source is listening. "
                        b"POST JSON to this URL.\n"
                    )
                else:
                    self.send_response(404)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(b"not found\n")

            def log_message(self, fmt, *args):
                # Silence the default per-request stderr line from
                # BaseHTTPRequestHandler. We print our own line in
                # the run() loop so the office output stays clean.
                pass

        return _Handler

    # ── Server lifecycle ──────────────────────────────────────────────────────

    def _start_server(self):
        if self._server is not None:
            return  # already running
        self._server = ThreadingHTTPServer(
            (self.host, self.port),
            self._make_handler(),
        )
        self._server_thread = threading.Thread(
            target=self._server.serve_forever,
            name=f"WebhookSource:{self.port}",
            daemon=True,
        )
        self._server_thread.start()
        host_display = "localhost" if self.host == "127.0.0.1" else self.host
        print(
            f"[WebhookSource] Listening on "
            f"http://{host_display}:{self.port}{self.path}"
        )
        if self.host == "127.0.0.1":
            print(
                "[WebhookSource] Bound to localhost only. "
                "Pass host='0.0.0.0' to accept posts from other machines."
            )

    # ── Generator ─────────────────────────────────────────────────────────────

    def run(self):
        """
        Generator that yields one message per incoming POST.
        The HTTP listener runs in a daemon background thread; this
        method blocks on the queue waiting for arrivals.
        """
        self._start_server()
        while True:
            msg = self._queue.get()
            self.posts_received += 1
            print(
                f"[WebhookSource] Received POST #{self.posts_received} "
                f"({len(msg.get('text', ''))} chars)"
            )
            yield msg


# ── Convenience factory for SOURCE_REGISTRY ──────────────────────────────────

def webhook(
    port: int = 8000,
    path: str = "/webhook",
    host: str = "127.0.0.1",
) -> WebhookSource:
    return WebhookSource(port=port, path=path, host=host)


# ── Test when run directly ────────────────────────────────────────────────────

if __name__ == "__main__":
    print("WebhookSource — Test")
    print("=" * 60)
    print("Listens on http://localhost:8000/webhook")
    print("In another terminal, try:")
    print(
        "  curl -X POST http://localhost:8000/webhook "
        "-H 'Content-Type: application/json' "
        "-d '{\"title\":\"hi\",\"text\":\"from curl\"}'"
    )
    print("-" * 60)

    src = WebhookSource()
    count = 0
    for msg in src.run():
        count += 1
        print(f"\n{count}. {msg}")
        if count >= 3:
            print("\n[Stopping after 3 messages for test]")
            break

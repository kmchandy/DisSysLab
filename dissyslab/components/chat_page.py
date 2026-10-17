"""A chat page in the browser: ``chat_page`` (source) and ``chat_reply`` (sink).

``dsl run`` starts a small web server on this computer and opens a chat
page. What the person types arrives in the office as a message from the
``chat_page`` source; whatever reaches the ``chat_reply`` sink appears in
the page as the reply.

::

    sources:
        customer: chat_page(title="Main Street Motors")
    sinks:
        screen: chat_reply
    agents:
        Sal: salesperson
    connections:
        customer -> Sal -> screen

Each message from the page::

    {
        "session": "k3j9...",     # one per browser tab
        "turn":    3,             # 1, 2, 3, ... within the session
        "text":    "What's your best price on the Tahoe?",
        "history": [              # the earlier turns of this conversation
            {"customer": "Hi", "reply": "Welcome to Main Street Motors!"},
            {"customer": "...", "reply": "..."},
        ],
    }

The reply is found by its ``session`` and ``turn``, so every message that
reaches ``chat_reply`` must still carry them. An annotator keeps them; an
author that builds a new message must copy them. The reply text is the
field named by ``chat_reply(text="reply")``.

The server listens on 127.0.0.1 only, so only this computer can reach the
page. The source never runs out: the office runs until Ctrl-C.

Python standard library only.
"""

from __future__ import annotations

import json
import queue
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

DEFAULT_PORT = 8765

#: How long a browser waits for a reply before asking again (seconds).
_POLL_WAIT = 20.0


class ChatHub:
    """The state one chat page shares between its source and its sink."""

    def __init__(self, port: int, title: str) -> None:
        self.port = port
        self.title = title
        self.incoming: "queue.Queue[dict[str, Any]]" = queue.Queue()
        # session -> list of {"customer": text, "reply": text or None}
        self.transcripts: dict[str, list[dict[str, Any]]] = {}
        self.changed = threading.Condition()
        self.server: ThreadingHTTPServer | None = None

    # ── from the browser ──────────────────────────────────────────────────

    def say(self, session: str, text: str) -> int:
        """Record what the customer typed; queue it for the source. Returns the turn."""
        with self.changed:
            turns = self.transcripts.setdefault(session, [])
            history = [dict(t) for t in turns]
            turns.append({"customer": text, "reply": None})
            turn = len(turns)
        self.incoming.put({"session": session, "turn": turn, "text": text, "history": history})
        return turn

    def replies(self, session: str, after: int, wait: float = _POLL_WAIT) -> list[dict[str, Any]]:
        """Replies for turns after ``after``, waiting up to ``wait`` seconds for one."""
        deadline = time.monotonic() + wait
        with self.changed:
            while True:
                turns = self.transcripts.get(session, [])
                ready = [{"turn": i + 1, "reply": t["reply"]}
                         for i, t in enumerate(turns) if i + 1 > after and t["reply"] is not None]
                left = deadline - time.monotonic()
                if ready or left <= 0:
                    return ready
                self.changed.wait(left)

    # ── from the office ───────────────────────────────────────────────────

    def answer(self, session: str, turn: int, reply: str) -> bool:
        """Record the office's reply to a turn. False if there is no such turn."""
        with self.changed:
            turns = self.transcripts.get(session, [])
            if not 1 <= turn <= len(turns):
                return False
            previous = turns[turn - 1]["reply"]
            turns[turn - 1]["reply"] = reply if previous is None else f"{previous}\n\n{reply}"
            self.changed.notify_all()
            return True

    # ── the server ────────────────────────────────────────────────────────

    def start(self) -> None:
        if self.server is not None:
            return
        hub = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:  # no access log in the terminal
                pass

            def _send(self, code: int, body: bytes, kind: str) -> None:
                self.send_response(code)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:  # noqa: N802 - http.server's name
                url = urlparse(self.path)
                if url.path == "/":
                    page = _PAGE.replace("__TITLE__", _html_escape(hub.title))
                    self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")
                elif url.path == "/replies":
                    q = parse_qs(url.query)
                    session = q.get("session", [""])[0]
                    after = int(q.get("after", ["0"])[0] or 0)
                    body = json.dumps(hub.replies(session, after)).encode("utf-8")
                    self._send(200, body, "application/json")
                else:
                    self._send(404, b"not found", "text/plain")

            def do_POST(self) -> None:  # noqa: N802
                if urlparse(self.path).path != "/say":
                    self._send(404, b"not found", "text/plain")
                    return
                length = int(self.headers.get("Content-Length", "0") or 0)
                try:
                    data = json.loads(self.rfile.read(length) or b"{}")
                    session, text = str(data["session"]), str(data["text"]).strip()
                except (ValueError, KeyError):
                    self._send(400, b"expected {session, text}", "text/plain")
                    return
                if not text:
                    self._send(400, b"empty message", "text/plain")
                    return
                turn = hub.say(session, text)
                self._send(200, json.dumps({"turn": turn}).encode("utf-8"), "application/json")

        class Server(ThreadingHTTPServer):
            # Restart at once after Ctrl-C. Not on Windows, where the same
            # option lets a second server share a port that is in use.
            allow_reuse_address = sys.platform != "win32"
            daemon_threads = True

        try:
            self.server = Server(("127.0.0.1", self.port), Handler)
        except OSError as e:
            raise OSError(
                f"port {self.port} is already in use, so the chat page cannot start. "
                f"Usually another `dsl run` with a chat page is still running: find its "
                f"terminal and press Ctrl-C. Or give this office another port, the same "
                f"in both places: chat_page(port={self.port + 1}) and "
                f"chat_reply(port={self.port + 1}). ({e})") from None
        threading.Thread(target=self.server.serve_forever, name=f"chat_page:{self.port}",
                         daemon=True).start()

    @property
    def url(self) -> str:
        return f"http://localhost:{self.port}/"


_HUBS: dict[int, ChatHub] = {}
_HUBS_LOCK = threading.Lock()


def hub_for(port: int, title: str = "Chat") -> ChatHub:
    """The one hub serving ``port`` (made on first use)."""
    with _HUBS_LOCK:
        if port not in _HUBS:
            _HUBS[port] = ChatHub(port, title)
        return _HUBS[port]


def _html_escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


class ChatPage:
    """Source: what a person types into the chat page, one message per turn.

    Arguments: ``title`` (shown at the top of the page), ``port`` (default
    8765; ``chat_reply`` must use the same), ``open_browser`` (default
    True: open the page when the office starts).
    """

    def __init__(self, title: str = "Chat", port: int = DEFAULT_PORT,
                 open_browser: bool = True) -> None:
        self.hub = hub_for(port, title)
        self.hub.title = title
        self.open_browser = open_browser
        self._started = False

    def run(self) -> dict[str, Any]:
        """The next thing the person typed. Waits for it; never runs out."""
        if not self._started:
            self._started = True
            self.hub.start()
            print(f"[chat_page] Chat page: {self.hub.url}   (Ctrl-C here to stop the office)",
                  flush=True)
            if self.open_browser:
                webbrowser.open(self.hub.url)
        return self.hub.incoming.get()


class ChatReply:
    """Sink: shows a message's reply in the chat page, under the turn it answers.

    Arguments: ``text`` (the field holding the reply; default ``"reply"``),
    ``port`` (default 8765; the same as ``chat_page``'s).
    """

    def __init__(self, text: str = "reply", port: int = DEFAULT_PORT) -> None:
        self.field = text
        self.hub = hub_for(port)

    def run(self, msg: dict[str, Any]) -> None:
        session, turn = msg.get("session"), msg.get("turn")
        if session is None or turn is None:
            print(f"[chat_reply] a message without session and turn cannot be shown: "
                  f"{sorted(msg)}. An author that builds a new message must copy them.")
            return
        reply = msg.get(self.field)
        if reply is None:
            reply = f"(the message has no {self.field!r} field)"
        if not self.hub.answer(str(session), int(turn), str(reply)):
            print(f"[chat_reply] no turn {turn} in session {session}")


_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root { --bg:#f4f5f7; --me:#2563eb; --them:#ffffff; --ink:#1f2937; --mute:#6b7280; }
  * { box-sizing: border-box; }
  body { margin:0; font:16px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
         background:var(--bg); color:var(--ink); display:flex; flex-direction:column; height:100vh; }
  header { padding:14px 20px; background:#111827; color:#fff; font-weight:600; }
  header small { display:block; font-weight:400; color:#9ca3af; font-size:13px; }
  #log { flex:1; overflow-y:auto; padding:20px; display:flex; flex-direction:column; gap:10px; }
  .msg { max-width:70%; padding:10px 14px; border-radius:14px; white-space:pre-wrap; word-wrap:break-word; }
  .me { align-self:flex-end; background:var(--me); color:#fff; border-bottom-right-radius:4px; }
  .them { align-self:flex-start; background:var(--them); border:1px solid #e5e7eb; border-bottom-left-radius:4px; }
  .wait { align-self:flex-start; color:var(--mute); font-style:italic; }
  form { display:flex; gap:8px; padding:12px; background:#fff; border-top:1px solid #e5e7eb; }
  input { flex:1; padding:10px 12px; font-size:16px; border:1px solid #d1d5db; border-radius:10px; }
  button { padding:10px 18px; font-size:16px; border:0; border-radius:10px; background:var(--me); color:#fff; cursor:pointer; }
  button:disabled { background:#93c5fd; }
</style></head>
<body>
<header>__TITLE__<small>Served by your DisSysLab office on this computer</small></header>
<div id="log"></div>
<form id="f"><input id="t" autocomplete="off" placeholder="Type a message" autofocus>
<button id="b">Send</button></form>
<script>
const session = (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2));
let shown = 0, waiting = 0, sentAt = 0, warned = false;
const log = document.getElementById("log"), box = document.getElementById("t");
function add(text, cls) {
  const d = document.createElement("div"); d.className = "msg " + cls; d.textContent = text;
  log.appendChild(d); log.scrollTop = log.scrollHeight; return d;
}
let typing = null;
function setTyping(on) {
  if (on && !typing) { typing = add("typing\\u2026", "wait"); }
  if (!on && typing) { typing.remove(); typing = null; }
}
document.getElementById("f").addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = box.value.trim(); if (!text) return;
  box.value = ""; add(text, "me"); waiting += 1; setTyping(true);
  sentAt = Date.now(); warned = false;
  await fetch("/say", {method:"POST", headers:{"Content-Type":"application/json"},
                       body: JSON.stringify({session, text})});
});
async function poll() {
  while (true) {
    try {
      const r = await fetch("/replies?session=" + encodeURIComponent(session) + "&after=" + shown);
      const items = await r.json();
      for (const it of items) {
        if (it.turn > shown) { setTyping(false); add(it.reply, "them"); shown = it.turn;
                               waiting = Math.max(0, waiting - 1); if (waiting) setTyping(true); }
      }
      if (waiting && !warned && Date.now() - sentAt > 90000) {
        warned = true; setTyping(false);
        add("(No reply yet. The office may have failed on this message: look at the terminal where dsl run is running.)", "wait");
      }
    } catch (err) { await new Promise(res => setTimeout(res, 2000)); }
  }
}
poll();
</script>
</body></html>
"""

"""The chat page: turns in, replies out, by session and turn."""

from __future__ import annotations

import json
import socket
import urllib.request

from dissyslab.components import chat_page


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_each_turn_carries_the_conversation_so_far():
    hub = chat_page.ChatHub(0, "t")
    assert hub.say("s1", "hello") == 1
    first = hub.incoming.get_nowait()
    assert first == {"session": "s1", "turn": 1, "text": "hello", "history": []}
    assert hub.answer("s1", 1, "Welcome!")
    hub.say("s1", "a Tahoe for $1?")
    second = hub.incoming.get_nowait()
    assert second["turn"] == 2
    assert second["history"] == [{"customer": "hello", "reply": "Welcome!"}]


def test_sessions_are_separate():
    hub = chat_page.ChatHub(0, "t")
    hub.say("a", "hi")
    hub.say("b", "hi")
    assert hub.incoming.get_nowait()["turn"] == 1
    assert hub.incoming.get_nowait()["turn"] == 1
    assert hub.answer("b", 1, "for b")
    assert hub.replies("a", 0, wait=0) == []
    assert hub.replies("b", 0, wait=0) == [{"turn": 1, "reply": "for b"}]


def test_a_reply_without_session_and_turn_is_reported_not_shown(capsys):
    sink = chat_page.ChatReply(port=_free_port())
    sink.run({"reply": "hi"})
    assert "must copy them" in capsys.readouterr().out


def test_the_page_round_trip_over_http():
    port = _free_port()
    source = chat_page.ChatPage(title="Main Street Motors", port=port, open_browser=False)
    sink = chat_page.ChatReply(port=port)
    source.hub.start()
    base = f"http://127.0.0.1:{port}"
    page = urllib.request.urlopen(base + "/").read().decode()
    assert "<title>Main Street Motors</title>" in page
    req = urllib.request.Request(base + "/say", data=json.dumps(
        {"session": "s", "text": "best price?"}).encode(), method="POST")
    assert json.loads(urllib.request.urlopen(req).read()) == {"turn": 1}
    msg = source.run()
    assert msg["text"] == "best price?" and msg["turn"] == 1
    sink.run({**msg, "reply": "Our prices are on the sticker."})
    replies = json.loads(urllib.request.urlopen(base + "/replies?session=s&after=0").read())
    assert replies == [{"turn": 1, "reply": "Our prices are on the sticker."}]


def test_replies_with_no_chat_page_running_say_why_once(capsys):
    """Lab 1, 17 Nov 2026: the source swapped to the attack file, the sink
    left on chat_reply, and the run printed "no turn 1 in session c01" for
    every customer."""
    sink = chat_page.ChatReply(port=_free_port())
    for session in ("c01", "c02", "c03"):
        sink.run({"session": session, "turn": 1, "reply": "hi"})
    out = capsys.readouterr().out
    assert out.count("[chat_reply]") == 1
    assert "no chat page is running" in out and "jsonl_recorder" in out


def test_dsl_check_finds_chat_reply_without_a_chat_page(tmp_path):
    from dissyslab.office.check import check_office
    (tmp_path / "attacks.jsonl").write_text('{"session": "c01", "turn": 1, "text": "hi"}\n')
    office = ('sources:\n    customer: file_source(path="attacks.jsonl")\n\n'
              'sinks:\n    screen: {sink}\n\nconnections:\n    customer -> screen\n')
    (tmp_path / "office.md").write_text(office.format(sink="chat_reply"))
    (problem,) = check_office(tmp_path).problems
    assert problem.startswith("line 5: screen shows replies in the chat page, but no chat_page")
    assert "swap both pairs of lines" in problem
    (tmp_path / "office.md").write_text(office.format(sink='jsonl_recorder(path="replies.jsonl")'))
    assert check_office(tmp_path).problems == []


def test_a_port_in_use_says_what_to_do():
    import pytest
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        port = taken.getsockname()[1]
        with pytest.raises(OSError, match=r"Ctrl-C.*chat_page\(port="):
            chat_page.ChatHub(port, "t").start()

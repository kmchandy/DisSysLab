"""``dsl new`` / ``dsl edit``: what Claude is told, what is written, and the check.

The model is replaced by a client that replays a script of replies, so
the loop runs without a key.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from dissyslab import cli_chat


class Scripted:
    """Stands in for anthropic.Anthropic: each stream() returns the next reply."""

    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.seen: list[list[dict]] = []
        self.messages = self

    @contextmanager
    def stream(self, *, model, max_tokens, system, messages):
        self.seen.append([dict(m) for m in messages])
        reply = self.replies.pop(0)

        class S:
            text_stream = [reply]
        yield S()


GOOD_OFFICE = """```office.md
sources:
    items: file_source(path="items.jsonl")
sinks:
    console_printer
agents:
    Tri: triage
connections:
    items -> Tri -> console_printer
```

```roles/triage.md
---
in: text
out: urgency (urgent | routine)
---
Decide. Return only a JSON object with the field "urgency".
```

```items.jsonl
{"text": "help"}
```
"""


def test_the_prompt_is_the_shipped_reference_plus_the_chat_rules():
    prompt = cli_chat.system_prompt_create()
    assert "# office.md -- the grammar" in prompt
    assert "# Roles" in prompt and "# Sources and sinks" in prompt
    assert "There is no title line and no sentence form" in prompt
    assert "# Office:" not in prompt


def test_files_are_parsed_in_all_three_forms_and_unsafe_paths_refused():
    text = (
        "```roles/a.py\nclass A: pass\n```\n"
        "### roles/b.md\n```\nbody b\n```\n"
        "Save as `data.jsonl`\n```\n{}\n```\n"
        "```my_office/office.md\nsinks:\n```\n"
        "```../evil.md\nx\n```\n"
        "```roles/../../x.py\nx\n```\n"
        "```setup.py\nx\n```\n"
    )
    files = cli_chat.parse_claude_files(text)
    assert set(files) == {"roles/a.py", "roles/b.md", "data.jsonl", "office.md"}


def test_a_reply_that_checks_clean_is_written_and_reported(tmp_path, capsys):
    office = tmp_path / "sorter"
    client = Scripted([GOOD_OFFICE])
    code = cli_chat.chat_loop("sort my inbox", "SYSTEM", office, model="m", client=client)
    assert code == 0
    assert (office / "office.md").is_file() and (office / "roles" / "triage.md").is_file()
    assert (office / "items.jsonl").read_text() == '{"text": "help"}\n'
    out = capsys.readouterr().out
    assert "dsl check:" in out and "no problems found." in out and "dsl run ." in out


def test_problems_are_sent_back_to_claude_to_fix(tmp_path, capsys):
    office = tmp_path / "sorter"
    broken = GOOD_OFFICE.replace("Tri: triage", "Tri: triag")
    client = Scripted([broken, GOOD_OFFICE])
    code = cli_chat.chat_loop("sort my inbox", "SYSTEM", office, model="m", client=client)
    assert code == 0
    fix_request = client.seen[1][-1]["content"]
    assert fix_request.startswith("dsl check reported these problems.")
    assert "no agent called 'triag'" in fix_request and "Did you mean 'triage'?" in fix_request
    out = capsys.readouterr().out
    assert "Sending the problems back to Claude to fix." in out
    assert out.rstrip().endswith("dsl run .")


def test_fixing_stops_after_the_allowed_rounds(tmp_path, capsys):
    office = tmp_path / "sorter"
    broken = GOOD_OFFICE.replace("Tri: triage", "Tri: triag")
    client = Scripted([broken] * (cli_chat.FIX_ROUNDS + 1))
    code = cli_chat.chat_loop("x", "SYSTEM", office, model="m", client=client,
                              ask=lambda prompt: "")
    assert code == 0
    assert len(client.seen) == cli_chat.FIX_ROUNDS + 1
    assert "still reports problems" in capsys.readouterr().out


def test_the_edit_prompt_shows_every_file_of_the_office(tmp_path):
    office = tmp_path / "desk"
    (office / "roles").mkdir(parents=True)
    (office / "office.md").write_text("sinks:\n    console_printer\n")
    (office / "roles" / "clerk.py").write_text("class Clerk: pass\n")
    (office / "tickets.jsonl").write_text("{}\n")
    prompt = cli_chat.system_prompt_edit(office)
    for rel in ("office.md", "roles/clerk.py", "tickets.jsonl"):
        assert f"```{rel}\n" in prompt

"""What both parts share: run one agent session and keep everything it did.

A *trace* is the whole session as a list of events, in order: what the
model said, each tool it called and with what input, what each tool
returned, any call a hook denied, and the final result with its cost.
Students read traces; checkers read them too. Nothing here decides what
an agent may do: that is in the part's own script.

The Claude Agent SDK is imported inside the functions that need it, so
this file (and the checkers that use it) can be read and tested on a
machine that does not have the SDK.
"""

from __future__ import annotations

import dataclasses
import json
import os
import platform
import time
from importlib import metadata
from pathlib import Path
from typing import Any

#: The model the course's other real runs used (Class 6). --model overrides.
DEFAULT_MODEL = "claude-sonnet-4-5"

#: Built-in Claude Code tools the agents in this lab must never have. Each
#: part gives its agent only the custom tools it defines; these are removed
#: outright as well, so a change of defaults cannot hand one back.
BUILT_IN_TOOLS = ["Bash", "Read", "Write", "Edit", "MultiEdit", "Glob", "Grep",
                  "WebFetch", "WebSearch", "NotebookEdit", "Agent", "Task",
                  "TodoWrite", "BashOutput", "KillShell"]

REPO = Path(__file__).resolve().parents[2]
#: Where runs go: outside course/ (so nothing is published by accident), and
#: in .gitignore.
RUNS = REPO / "lab3_runs"


def sdk_version() -> str:
    try:
        return metadata.version("claude-agent-sdk")
    except metadata.PackageNotFoundError:
        return "not installed"


def _plain(obj: Any) -> Any:
    """A message or block as JSON-able data, whatever its exact SDK class."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {"type": type(obj).__name__,
                **{k: _plain(v) for k, v in dataclasses.asdict(obj).items()}}
    if isinstance(obj, dict):
        return {str(k): _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return repr(obj)


def events_of(message: Any) -> list[dict]:
    """Flatten one SDK message into trace events a person can read in order."""
    kind = type(message).__name__
    if kind == "AssistantMessage":
        out = []
        for block in message.content:
            b = type(block).__name__
            if b == "TextBlock":
                out.append({"event": "said", "text": block.text})
            elif b == "ToolUseBlock":
                out.append({"event": "tool_call", "id": block.id, "tool": block.name,
                            "input": _plain(block.input)})
            elif b == "ThinkingBlock":
                out.append({"event": "thought", "text": block.thinking})
        return out
    if kind == "UserMessage":
        out = []
        content = message.content if isinstance(message.content, list) else []
        for block in content:
            if type(block).__name__ == "ToolResultBlock":
                text = block.content
                if isinstance(text, list):
                    text = "\n".join(str(p.get("text", p)) if isinstance(p, dict) else str(p)
                                     for p in text)
                out.append({"event": "tool_result", "id": block.tool_use_id,
                            "is_error": bool(block.is_error), "text": text})
        return out
    if kind == "ResultMessage":
        return [{"event": "result", "subtype": message.subtype, "num_turns": message.num_turns,
                 "cost_usd": message.total_cost_usd, "is_error": message.is_error,
                 "final_text": message.result,
                 "permission_denials": _plain(message.permission_denials)}]
    return []


async def run_session(prompts: list[str], options: Any) -> list[dict]:
    """Send each prompt in turn, in one session; return the trace."""
    from claude_agent_sdk import ClaudeSDKClient

    trace: list[dict] = []
    async with ClaudeSDKClient(options=options) as client:
        for prompt in prompts:
            trace.append({"event": "prompt", "text": prompt})
            await client.query(prompt)
            async for message in client.receive_response():
                trace.extend(events_of(message))
    return trace


def cost_of(trace: list[dict]) -> float:
    return sum(e.get("cost_usd") or 0.0 for e in trace if e["event"] == "result")


def save_run(folder: Path, meta: dict, trace: list[dict], outcome: dict) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    meta = {**meta, "sdk": sdk_version(), "python": platform.python_version(),
            "finished": time.strftime("%Y-%m-%d %H:%M:%S")}
    (folder / "trace.json").write_text(json.dumps({"meta": meta, "trace": trace,
                                                   "outcome": outcome}, indent=1),
                                       encoding="utf-8")


def key_is_set() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))

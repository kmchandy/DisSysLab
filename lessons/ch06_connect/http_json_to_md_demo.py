from __future__ import annotations
from pathlib import Path

from dsl.core import Network
from dsl.block_lib.stream_transformers import TransformerFunction
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.connector_lib.inputs.http_json import InputConnectorHTTPJSON
from dsl.connector_lib.outputs.file_md import OutputConnectorFileMarkdown
from dsl.connector_lib.orchestrators.buffered import BufferedOrchestrator

HERE = Path(__file__).resolve().parent
REPORTS = HERE / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)

OUT = REPORTS / "todos_summary.md"

# Public, no-auth demo API
URL = "https://jsonplaceholder.typicode.com/todos"  # stable, public JSON


def to_row(msg):
    """Turn {"data": {...}} into a markdown bullet row."""
    d = msg["data"]
    title = d.get("title", "(no title)")
    done = "✅" if d.get("completed") else "⬜️"
    return {"row": f"- {done} {title}"}


net = Network(
    blocks={
        # Tell the input connector to pull from URL (one command)
        "pull": GenerateFromList(items=[{"cmd": "pull", "args": {"url": URL}}], delay=0.05),
        "in":   InputConnectorHTTPJSON(),

        "row":  TransformerFunction(func=to_row),

        # Buffer rows and flush once
        "orch": BufferedOrchestrator(meta_builder=lambda buf: {"title": "Public TODOs (sample)"}),
        "out":  OutputConnectorFileMarkdown(str(OUT), title="Public TODOs (sample)"),

        # One flush command
        "tick": GenerateFromList(items=[{"cmd": "flush"}], delay=0.3),
    },
    connections=[
        ("pull", "out", "in", "in"),
        ("in", "out", "row", "in"),
        ("row", "out", "orch", "data_in"),
        ("tick", "out", "orch", "command_in"),
        ("orch", "out", "out", "in"),
    ],
)

if __name__ == "__main__":
    net.compile_and_run()
    print("Wrote:", OUT)

# dsl/tests/test_http_json_to_md.py
"""
HTTP JSON → rows → Markdown (no OAuth)

Run EITHER:
  - pytest -q dsl/tests/test_http_json_to_md.py
  - python  -m dsl.tests.test_http_json_to_md
"""

from pathlib import Path

from dsl.core import Network
from dsl.block_lib.stream_transformers import TransformerFunction
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.connector_lib.inputs import InputConnectorFile
from dsl.connector_lib.outputs import OutputConnectorFileMarkdown
from dsl.connector_lib.orchestrators import BufferedOrchestrator

# Sample JSON you provide in the repo
#   dsl/examples/ch06_connect/data/issues_http.json
SRC = "dsl/examples/ch06_connect/data/issues_http.json"


def to_row(msg):
    """Turn {"data": {...}} into a Markdown bullet row."""
    item = msg["data"]
    return {"row": f"- {item.get('title', 'Untitled')}"}


def run_once(out_dir: Path) -> Path:
    """Build the network, run it, and return the output file path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    OUT = out_dir / "issue_summary.md"

    net = Network(
        blocks={
            # 1) Tell the input connector to pull from a local JSON file (one command)
            "in_commands": GenerateFromList(
                items=[{"cmd": "pull", "args": {"path": SRC}}],
                delay=0.05,
            ),
            "input_connector": InputConnectorFile(),

            # 2) Transform each item into a simple row
            "transform_to_row": TransformerFunction(func=to_row),

            # 3) Buffer rows and flush once when a command arrives
            #    (Meta is simple: no path needed since the output connector has it)
            "buffer": BufferedOrchestrator(meta_builder=lambda buf: {"title": "Issue Triage"}),

            # 4) Write a Markdown report to a fixed path (constructor-driven)
            "output_connector": OutputConnectorFileMarkdown(str(OUT), title="Issue Triage"),

            # 5) Emit a single flush command
            "out_commands": GenerateFromList(items=[{"cmd": "flush"}, "__STOP__"], delay=0.08),
        },
        connections=[
            ("in_commands", "out", "input_connector", "in"),
            ("input_connector", "out", "transform_to_row", "in"),
            ("transform_to_row", "out", "buffer", "data_in"),
            ("out_commands", "out", "buffer", "command_in"),
            ("buffer", "out", "output_connector", "in"),
        ],
    )

    net.compile_and_run()
    return OUT


# ---------- Pytest entrypoint ----------
def test_http_json_to_md(tmp_path: Path):
    OUT = run_once(tmp_path)
    assert OUT.exists()
    text = OUT.read_text(encoding="utf-8")
    assert text.startswith("# Issue Triage")
    assert "- " in text  # at least one bullet row


# ---------- Standalone entrypoint ----------
if __name__ == "__main__":
    out_dir = Path("dsl/tests/reports")
    OUT = run_once(out_dir)
    print(f"✅ Wrote: {OUT}")

# minimal wiring: JSON file -> to_row -> Markdown report (self-contained)
from pathlib import Path
import json

from dsl.core import Network
from dsl.block_lib.stream_transformers import TransformerFunction
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.connector_lib.inputs import InputConnectorFile
from dsl.connector_lib.outputs import OutputConnectorFileMarkdown
from dsl.connector_lib.orchestrators import BufferedOrchestrator

# --- paths relative to THIS file ---
HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
REPORTS_DIR = HERE / "reports"
SRC = DATA_DIR / "issues.json"
OUT = REPORTS_DIR / "issue_summary.md"

# --- ensure inputs/outputs exist ---
DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
if not SRC.exists():
    SRC.write_text(json.dumps([
        {"title": "Crash on startup", "body": "App throws exception when launched"},
        {"title": "Feature: dark mode", "body": "Please add a dark theme"},
        {"title": "Docs: typo in README", "body": "Small spelling mistake"}
    ], indent=2), encoding="utf-8")


def to_row(msg):
    item = msg["data"]
    return {"row": f"- {item.get('title', 'Untitled')}"}


net = Network(
    blocks={
        "in_commands": GenerateFromList(
            items=[{"cmd": "pull", "args": {"path": str(SRC)}}],
            delay=0.05
        ),
        "input_connector": InputConnectorFile(),
        "transform_to_row": TransformerFunction(func=to_row),
        "buffer": BufferedOrchestrator(
            meta_builder=lambda buf: {
                "path": str(OUT), "title": "Issue Triage"}
        ),
        "output_connector": OutputConnectorFileMarkdown(),
        "out_commands": GenerateFromList(items=[{"cmd": "flush"}], delay=0.1),
    },
    connections=[
        ("in_commands", "out", "input_connector", "in"),
        ("input_connector", "out", "transform_to_row", "in"),
        ("transform_to_row", "out", "buffer", "data_in"),
        ("out_commands", "out", "buffer", "command_in"),
        ("buffer", "out", "output_connector", "in"),
    ],
)

if __name__ == "__main__":
    net.compile_and_run()
    print("Wrote:", OUT)

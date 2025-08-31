# minimal wiring: JSON file -> to_row -> Markdown report
from dsl.core import Network
from dsl.block_lib.stream_transformers import TransformerFunction
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.connector_lib.inputs import InputConnectorFile
from dsl.connector_lib.outputs import OutputConnectorFileMarkdown
from dsl.connector_lib.orchestrators import BufferedOrchestrator

SRC = "dsl/examples/ch06_connectors/data/issues.json"
OUT = "dsl/examples/ch06_connectors/reports/issue_summary.md"


def to_row(msg):
    item = msg["data"]
    return {"row": f"- {item.get('title', 'Untitled')}"}


orch = BufferedOrchestrator(meta_builder=lambda buf: {
                            "path": OUT, "title": "Issue Triage"})

net = Network(
    blocks={
        # Generate commands to input connector (was pull)
        "in_commands": GenerateFromList(items=[{"cmd": "pull", "args": {"path": SRC}}], delay=0.05),
        # Input connector to read JSON file (was in)
        "input_connector":   InputConnectorFile(),
        # Transform input data to row format
        "transform_to_row":  TransformerFunction(func=to_row),
        "orch": orch,
        # Output connector to write Markdown file
        "output_connector":  OutputConnectorFileMarkdown(),
        # Generate commands
        "tick": GenerateFromList(items=[{"cmd": "flush"}], delay=0.1),
    },
    connections=[
        ("pull", "out", "in", "in"),
        ("in", "out", "row", "in"),
        ("row", "out", "orch", "data_in"),
        ("tick", "out", "orch", "tick_in"),
        ("orch", "out", "out", "in"),
    ],
)

if __name__ == "__main__":
    net.compile_and_run()
    print("Wrote:", OUT)

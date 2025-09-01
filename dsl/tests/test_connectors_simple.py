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


net = Network(
    blocks={
        "in_commands": GenerateFromList(
            items=[{"cmd": "pull", "args": {"path": SRC}}],
            delay=0.05
        ),
        "input_connector": InputConnectorFile(),
        "transform_to_row": TransformerFunction(func=to_row),
        "buffer": BufferedOrchestrator(
            meta_builder=lambda buf: {"path": OUT, "title": "Issue Triage"}
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

from dsl.core import Network
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.block_lib.stream_transformers import TransformerFunction
from dsl.connector_lib.inputs.csv import InputConnectorCSV
from dsl.connector_lib.outputs.file_md import OutputConnectorFileMarkdown
from dsl.connector_lib.outputs.csv import OutputConnectorCSV
from dsl.connector_lib.orchestrators.buffered import BufferedOrchestrator

SRC = "dsl/examples/connectors/data/tickets.csv"
OUT_MD = "dsl/examples/connectors/reports/tickets.md"
OUT_CSV = "dsl/examples/connectors/reports/tickets_clean.csv"

# --- tiny transformers (clear + readable) -----------------------------------


def to_row(msg):
    d = msg["data"]
    label = "bug" if d.get("type", "").lower() == "bug" else "other"
    return {"row": f"- [{label}] {d.get('title', '(untitled)')}"}


def to_clean_dict(msg):
    d = msg["data"]
    return {"id": d.get("id"), "title": d.get("title"), "type": d.get("type")}


# --- orchestrators: buffer many, flush once ---------------------------------
# meta_builder builds the META for the flush command the orchestrator emits
def md_meta(buf): return {"path": OUT_MD,
                          "title": "Ticket Summary"}  # payload is buf itself


def csv_meta(buf): return {"path": OUT_CSV,
                           "fieldnames": ["id", "title", "type"]}


orch_md = BufferedOrchestrator(meta_builder=md_meta)
orch_csv = BufferedOrchestrator(meta_builder=csv_meta)

# --- network ----------------------------------------------------------------
net = Network(
    blocks={
        # 1) control plane: pull once, then tick (flush) once
        "pull": GenerateFromList(items=[{"cmd": "pull", "args": {"path": SRC}}], delay=0.05),
        "tick_md": GenerateFromList(items=[{"cmd": "flush"}], delay=0.30),
        "tick_csv": GenerateFromList(items=[{"cmd": "flush"}], delay=0.35),

        # 2) connectors & transformers
        "in": InputConnectorCSV(),
        "row": TransformerFunction(func=to_row),
        "clean": TransformerFunction(func=to_clean_dict),
        "orch_md": orch_md,
        "orch_csv": orch_csv,
        "out_md": OutputConnectorFileMarkdown(),
        "out_csv": OutputConnectorCSV(),
    },
    connections=[
        # control → input
        ("pull", "out", "in", "in"),

        # data path → markdown
        ("in", "out", "row", "in"),
        ("row", "out", "orch_md", "data_in"),
        ("tick_md", "out", "orch_md", "tick_in"),
        ("orch_md", "out", "out_md", "in"),

        # data path → cleaned csv
        ("in", "out", "clean", "in"),
        ("clean", "out", "orch_csv", "data_in"),
        ("tick_csv", "out", "orch_csv", "tick_in"),
        ("orch_csv", "out", "out_csv", "in"),
    ],
)

if __name__ == "__main__":
    net.compile_and_run()
    print("Wrote:", OUT_MD)
    print("Wrote:", OUT_CSV)

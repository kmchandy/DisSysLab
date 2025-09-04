# dsl/tests/test_live_digest.py
from pathlib import Path

from dsl.core import Network
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.block_lib.stream_transformers import TransformerFunction
from dsl.connector_lib.outputs import OutputConnectorFileMarkdownAppend, BatchOutput


def to_row(msg):
    # Convert any incoming message to a simple Markdown bullet row
    # Expecting dicts like {"text": "..."} from the generator
    return {"row": f"- {msg.get('text', '(no text)')}"}


def build_network(out_path: Path) -> Network:
    """
    Build a tiny streaming pipeline:
      gen -> row -> batch (N or T) -> writer(md)
    """
    # Make sure the output directory exists
    out_path.parent.mkdir(parents=True, exist_ok=True)

    return Network(
        blocks={
            "gen": GenerateFromList(
                items=[{"text": f"tick {i}"} for i in range(20)],
                delay=0.01,
            ),
            "row": TransformerFunction(func=to_row),
            # BatchOutput flushes when N items collected OR T seconds passed
            "batch": BatchOutput(
                N=5,
                meta_builder=lambda buf: {"title": "Live Digest"},
            ),
            "writer": OutputConnectorFileMarkdownAppend(str(out_path), title="Live Digest"),
        },
        connections=[
            ("gen", "out", "row", "in"),
            ("row", "out", "batch", "in"),
            ("batch", "out", "writer", "in"),
        ],
    )


def test_live_digest(tmp_path: Path):
    """Pytest entry: writes a digest to a temp directory and verifies content."""
    out = tmp_path / "live_digest.md"
    net = build_network(out)
    net.compile_and_run()

    # Assertions: file exists and has at least one bullet row
    assert out.exists(), f"Expected output file not found: {out}"
    text = out.read_text(encoding="utf-8")
    assert "- " in text, "Expected at least one markdown bullet row in the digest."


if __name__ == "__main__":
    # Run with: python dsl/tests/test_live_digest.py
    reports_dir = Path("dsl/tests/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    out = reports_dir / "live_digest.md"
    net = build_network(out)
    net.compile_and_run()
    print(f"✅ Wrote: {out}")
    # Light sanity check for direct runs
    if out.exists():
        head = out.read_text(encoding="utf-8").splitlines()[:10]
        print("\n".join(head))

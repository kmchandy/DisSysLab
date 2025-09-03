# dsl/tests/test_rss_digest.py
from pathlib import Path
import tempfile

from dsl.core import Network
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.block_lib.stream_transformers import TransformerFunction
from dsl.connector_lib.inputs.rss import InputConnectorRSS
from dsl.connector_lib.orchestrators import BufferedOrchestrator
from dsl.connector_lib.outputs import OutputConnectorFileMarkdown


RSS_URL = "https://news.ycombinator.com/rss"


def to_row(msg):
    """Convert one RSS item into a markdown bullet with a link."""
    item = msg["data"]
    return {"row": f"- [{item.get('title')}]({item.get('link')})"}


def build_network(out_path: Path) -> Network:
    """Create a small pipeline: pull RSS -> transform -> buffer -> write markdown."""
    return Network(
        blocks={
            "pull": GenerateFromList(
                items=[{"cmd": "pull", "args": {"url": RSS_URL}}],
                delay=0.05,
            ),
            "rss": InputConnectorRSS(),
            "row": TransformerFunction(func=to_row),
            "buffer": BufferedOrchestrator(
                meta_builder=lambda buf: {
                    "path": str(out_path), "title": "HN Digest"}
            ),
            "writer": OutputConnectorFileMarkdown(str(out_path), title="HN Digest"),
            "flush": GenerateFromList(items=[{"cmd": "flush"}], delay=0.2),
        },
        connections=[
            ("pull", "out", "rss", "in"),
            ("rss", "out", "row", "in"),
            ("row", "out", "buffer", "data_in"),
            ("flush", "out", "buffer", "command_in"),
            ("buffer", "out", "writer", "in"),
        ],
    )


def test_rss_digest(tmp_path: Path):
    """Pytest entry: writes a digest and checks file exists + has bullet lines."""
    out_file = tmp_path / "news_digest.md"
    net = build_network(out_file)
    net.compile_and_run()

    assert out_file.exists()
    text = out_file.read_text(encoding="utf-8")
    # Expect at least one markdown list line like "- [title](url)"
    assert "- [" in text


if __name__ == "__main__":
    # Standalone run (no pytest). Writes to dsl/tests/reports/news_digest.md
    out_dir = Path("dsl/tests/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "news_digest.md"

    net = build_network(out_file)
    net.compile_and_run()

    print(f"✅ Wrote RSS digest to {out_file}")
    print(out_file.read_text(encoding="utf-8")[:500], "...")

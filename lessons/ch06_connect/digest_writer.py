from pathlib import Path
from dsl.core import Network
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.block_lib.stream_transformers import TransformerFunction
from dsl.connector_lib.orchestrators import BufferedOrchestrator
from dsl.connector_lib.outputs import OutputConnectorFileMarkdown
from dsl.connector_lib.inputs.rss import InputConnectorRSS

RSS_URL = "https://news.ycombinator.com/rss"
OUT = "dsl/examples/ch06_connect/reports/news_digest.md"
Path("dsl/examples/ch06_connect/reports").mkdir(parents=True, exist_ok=True)


def to_row(msg):
    item = msg["data"]
    return {"row": f"- [{item.get('title')}]({item.get('link')})"}


net = Network(
    blocks={
        "pull": GenerateFromList(
            items=[{"cmd": "pull", "args": {"url": RSS_URL}}],
            delay=0.05
        ),
        "rss": InputConnectorRSS(),
        "row": TransformerFunction(func=to_row),
        "buffer": BufferedOrchestrator(meta_builder=lambda buf: {"title": "News Digest"}),
        "writer": OutputConnectorFileMarkdown(str(OUT), title="News Digest"),
        "flush": GenerateFromList(items=[{"cmd": "flush"}], delay=0.2),
    },
    connections=[
        ("pull", "out", "rss", "in"),
        ("rss", "out", "row", "in"),
        ("row", "out", "buffer", "data_in"),
        ("flush", "out", "buffer", "command_in"),
        ("buffer", "out", "writer", "in"),
    ]
)

if __name__ == "__main__":
    net.compile_and_run()
    print(f"✅ Wrote: {OUT}")

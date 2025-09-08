from dsl.block_lib.stream_generators import GenerateFromRSS
from dsl.block_lib.stream_transformers import SentimentTransformer
from dsl.block_lib.stream_recorders import RecordToConsole
from dsl.core import Network

net = Network(
    blocks={
        "rss": GenerateFromRSS(url="https://feeds.bbci.co.uk/news/rss.xml", interval=3.0, limit=5),
        "sent": SentimentTransformer(),
        "sink": RecordToConsole(),
    },
    connections=[
        ("rss", "out", "sent", "in"),
        ("sent", "out", "sink", "in"),
    ],
)
net.compile_and_run()

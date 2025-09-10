# dsl/examples/ch03_fanin_fanout/review_split_merge.py

from dsl.core import Network
from dsl.block_lib.sources.source import Source
from dsl.block_lib.sinks.sink import Sink
from dsl.block_lib.sinks.sink_lib.common_sinks import record_to_list
from dsl.block_lib.sources.source import Source
from dsl.block_lib.sources.source_lib.common_sources import gen_list, gen_list_with_delay
from dsl.block_lib.routers.fanout import Broadcast, TwoWaySplit
from dsl.block_lib.routers.fanin import MergeAsynch
from dsl.block_lib.transforms.transform import Transform

# --- Split function: classify review sentiment ---


def classify_sentiment(msg: dict) -> str:
    text = msg["review"].lower()
    return "good" in text or "great" in text


# --- Transformer functions ---
def add_exclamations(x: dict) -> dict:
    x = x["review"]
    return {"positive": x + "!!!"}


def to_upper(x: dict) -> dict:
    x = x["review"]
    return {"negative": x.upper()}


reviews = [{"review": value} for value in [
    "Great movie", "Terrible acting", "Good plot", "Bad ending"
]]

results = []

net = Network(
    blocks={
        # Generator emits dicts: {"review": "..."}
        "gen": Source(generator_fn=gen_list(reviews + ["__STOP__"])),
        "two_way_split": TwoWaySplit(func=classify_sentiment),
        "pos_exclaim": Transform(func=add_exclamations),
        "neg_upper": Transform(func=to_upper),
        "merge": MergeAsynch(inports=["pos", "neg"]),
        "rec": Sink(record_fn=record_to_list(results)),
    },
    connections=[
        ("gen", "out", "two_way_split", "in"),
        ("two_way_split", "out_1", "pos_exclaim", "in"),
        ("two_way_split", "out_0", "neg_upper", "in"),
        ("pos_exclaim", "out", "merge", "pos"),
        ("neg_upper", "out", "merge", "neg"),
        ("merge", "out", "rec", "in"),
    ]
)

net.compile_and_run()
print(results)

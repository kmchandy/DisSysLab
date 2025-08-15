# dsl/examples/ch03_fanin_fanout/review_split_merge.py

from dsl.core import Network
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.block_lib.stream_transformers import TransformerFunction
from dsl.block_lib.stream_recorders import RecordToList
from dsl.block_lib.fanout import Split
from dsl.block_lib.fanin import MergeAsynch

# --- Split function: classify review sentiment ---


def classify_sentiment(msg: dict) -> str:
    text = msg["review"].lower()
    if "good" in text or "great" in text:
        return "pos"
    else:
        return "neg"

# --- Transformer functions ---


def add_exclamations(x: str) -> str:
    return x + "!!!"


def to_upper(x: str) -> str:
    return x.upper()


results = []

net = Network(
    blocks={
        # Generator emits dicts: {"review": "..."}
        "gen": GenerateFromList(
            items=["Great movie", "Terrible acting",
                   "Good plot", "Bad ending"],
            key="review"
        ),
        "split": Split(split_function=classify_sentiment,
                       outports=["pos", "neg"]),
        "pos_exclaim": TransformerFunction(
            func=add_exclamations,
            input_key="review",
            output_key="positive"
        ),
        "neg_upper": TransformerFunction(
            func=to_upper,
            input_key="review",
            output_key="negative"
        ),
        "merge": MergeAsynch(inports=["pos", "neg"]),
        "rec": RecordToList(results),
    },
    connections=[
        ("gen", "out", "split", "in"),
        ("split", "pos", "pos_exclaim", "in"),
        ("split", "neg", "neg_upper", "in"),
        ("pos_exclaim", "out", "merge", "pos"),
        ("neg_upper", "out", "merge", "neg"),
        ("merge", "out", "rec", "in"),
    ]
)

net.compile_and_run()
print(results)

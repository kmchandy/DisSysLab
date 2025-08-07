from dsl.core import SimpleAgent
from dsl.core import Network
from dsl.block_lib.generators import GenerateFromList
from dsl.block_lib.fan_in import MergeAsynch
from dsl.block_lib.recorders import RecordToList
from dsl.block_lib.transformers import StreamTransformer
import random

# BLOCK 1: X messages
x_msgs = [
    "AI is going to make all our lives miserable",
    "AI is going to boost the economy",
    "AI will replace some jobs but create others",
]

# BLOCK 2: Bluesky messages
bs_msgs = [
    "Artificial intelligence is overhyped",
    "AI can help us solve climate change",
    "AI is scary and exciting at the same time",
]

x_gen = GenerateFromList(x_msgs, name="x_gen")
bs_gen = GenerateFromList(bs_msgs, name="bs_gen")

# BLOCK 3: Asynchronous Merge
merge = MergeAsynch(name="merge")

# BLOCK 4: Sentiment scoring (mocked here as random for illustration)


def score_sentiment(text):
    return {"text": text, "score": random.randint(0, 100)}


score = StreamTransformer(
    transform_fn=score_sentiment,
    input_key="data",          # assumes input is {"data": ...}
    output_key=None,           # returns a full dict, not nested
    name="score"
)

# BLOCK 5: Sentiment splitter


class SentimentSplitter(SimpleAgent):
    def __init__(self, threshold=50, name="split"):
        super().__init__(name=name, inport="in", outports=["pos", "neg"])
        self.threshold = threshold

    def process(self, msg, inport=None):
        score = msg.get("score", 0)
        if score >= self.threshold:
            self.send(msg, outport="pos")
        else:
            self.send(msg, outport="neg")


split = SentimentSplitter(threshold=50, name="split")

# BLOCK 6 & 7: Recorders
pos_results, neg_results = [], []
pos_rec = RecordToList(pos_results, name="pos_rec")
neg_rec = RecordToList(neg_results, name="neg_rec")

# Define and run the network
net = Network(
    blocks={
        "x_gen": x_gen,
        "bs_gen": bs_gen,
        "merge": merge,
        "score": score,
        "split": split,
        "pos_rec": pos_rec,
        "neg_rec": neg_rec,
    },
    connections=[
        ("x_gen", "out", "merge", "in0"),
        ("bs_gen", "out", "merge", "in1"),
        ("merge", "out", "score", "in"),
        ("score", "out", "split", "in"),
        ("split", "pos", "pos_rec", "in"),
        ("split", "neg", "neg_rec", "in"),
    ],
)

net.compile_and_run()

# Show results
print("\nPositive Sentiment Messages:")
for msg in pos_results:
    print(msg)

print("\nNegative Sentiment Messages:")
for msg in neg_results:
    print(msg)

from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_recorders import record
from dsl.block_lib.stream_transformers import SentimentClassifierWithGPT
from dsl.block_lib.stream_transformers import MergeAsynch, MergeSynch, Broadcast

# Prompt-based classification using OpenAI
classification_prompt = (
    "You are an expert at analyzing social media. "
    "Label each post as 'pos' or 'neg'. Only return the label.\nPost: {msg}"
)


def test_sentiment_classifier():
    net = Network(
        blocks={
            "gen_pos": generate(["Pizza is wonderful!", "Diet drinks are lovely."]),
            "gen_neg": generate(["Pizza is unhealthy.", "Diet drinks are dangerous"]),
            "merge_asynch_gen_pos_and_gen_neg": MergeAsynch(["from_gen_pos", "from_gen_neg"]),
            "broadcast": Broadcast(["to_classify", "to_merge_text_sentiment"]),
            "classify": SentimentClassifierWithGPT(),
            "merge_text_sentiment": MergeSynch(["text", "sentiment"]),
            "record": record(),
        },
        connections=[
            ("gen_pos", "out", "merge_asynch_gen_pos_and_gen_neg", "from_gen_post"),
            ("gen_neg", "out", "merge_asynch_gen_pos_and_gen_neg", "from_gen_neg"),
            ("merge_asynch_gen_pos_and_gen_neg", "out", "broadcast", "in"),
            ("broadcast", "to_classify", "classify", "in"),
            ("broadcast", "to_merge_text_sentiment",
             "merge_text_sentiment", "text"),
            ("classify", "out", "merge_text_sentiment", "sentiment"),
            ("merge_text_sentiment", "out", "record", "in"),
        ]
    )

    net.compile_and_run()
    print(f"net.blocks['record'].saved = {net.blocks['record'].saved}")


if __name__ == "__main__":
    test_sentiment_classifier()

from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import PromptToBlock
from dsl.block_lib.stream_recorders import RecordToList
from dsl.utils.get_credentials import get_openai_key


def simple_network():

    get_openai_key()  # Ensure the OpenAI key is loaded
    results = []

    net = Network(
        blocks={
            "gen": generate(
                [
                    "I love sunny days",
                    "I hate traffic jams",
                    "This pizza is amazing",
                ],
                key="text",
            ),
            "sentiment_classifier": PromptToBlock(
                system_prompt="Classify the sentiment of the following text as positive, negative, or neutral.",
                input_key="text",
                output_key="sentiment",
            ),
            "rec": RecordToList(results),
        },
        connections=[
            ("gen", "out", "sentiment_classifier", "in"),
            ("sentiment_classifier", "out", "rec", "in"),
        ],
    )

    net.compile_and_run()

    print("Final Results:")
    for item in results:
        print(item)


if __name__ == "__main__":
    simple_network()

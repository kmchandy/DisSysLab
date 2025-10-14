# dsl/examples/ch04_GPT/gpt_network.py

from dsl.core import Network
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.block_lib.stream_transformers import TransformerPrompt
from dsl.block_lib.stream_recorders import RecordToList

# Store results here
results = []

# Define the network
net = Network(
    blocks={
        "generator": GenerateFromList(
            items=[
                "The movie was fantastic!",
                "I didn’t like the food.",
                "Service was slow but friendly."
            ],
            key="text"
        ),
        "sentiment_analyzer": TransformerPrompt(
            system_prompt="You are a sentiment rater. Output a positivity score from 0 to 10.",
            input_key="text",
            output_key="sentiment",
        ),
        "recorder": RecordToList(results),
    },
    connections=[
        ("generator", "out", "sentiment_analyzer", "in"),
        ("sentiment_analyzer", "out", "recorder", "in"),
    ]
)

net.compile_and_run()
print(results)

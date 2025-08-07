from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import GPT_Prompt
from dsl.block_lib.stream_recorders import RecordToList
from dsl.block_lib.prompt_templates import sentiment_prompt, as_list

results = []

net = Network(
    blocks={
        "gen": generate(["I love pizza", "I hate waiting"], key="text"),
        "clf": GPT_Prompt(
            messages=sentiment_prompt,
            input_key="text",
            output_key="sentiment"
        ),
        "rec": RecordToList(results),
    },
    connections=[("gen", "out", "clf", "in"), ("clf", "out", "rec", "in")]
)

net.compile_and_run()
print(results)  # e.g., ["Positive", "Negative"]

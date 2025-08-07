from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import GPT_Prompt
from dsl.block_lib.stream_recorders import RecordToList
from dsl.block_lib.prompt_templates import summarize_prompt

results = []

net = Network(
    blocks={
        "gen": generate(["DisSysLab is a message-passing framework ..."], key="text"),
        "xf": GPT_Prompt(
            messages=summarize_prompt,
            input_key="text",
            output_key="summary"
        ),

        "rec": RecordToList(results),
    },
    connections=[("gen", "out", "xf", "in"), ("xf", "out", "rec", "in")],
)

net.compile_and_run()
print(results)  # e.g., ["DisSysLab is a message-passing framework."]

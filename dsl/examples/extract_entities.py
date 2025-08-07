from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_transformers import GPT_Prompt
from dsl.block_lib.stream_recorders import RecordToList
from dsl.block_lib.prompt_templates import entity_extraction_prompt, as_list


def extract_entities():
    results = []

    net = Network(
        blocks={
            "gen": generate(
                [
                    "Barack Obama was president",
                    "Seward bought Alaska from Russia",
                    "Jaguars are cats"
                ], key="text"),
            "xf": GPT_Prompt(
                messages=entity_extraction_prompt,
                postprocess_fn=as_list,
                input_key="text",
                output_key="entities"
            ),
            "rec": RecordToList(results),
        },
        connections=[("gen", "out", "xf", "in"), ("xf", "out", "rec", "in")],
    )

    net.compile_and_run()
    print(results)


if __name__ == "__main__":
    extract_entities()

# dsl/tests/test_draft_objects_minimal.py
from dsl.user_interaction.draft_runner import run_draft
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.block_lib.stream_recorders import RecordToList


def to_row(m):
    return {"row": "- " + m["text"]}


def test_draft_objects_minimal():
    out = []
    draft = {
        "blocks": {
            "gen": GenerateFromList(items=[{"text": f"hello {i}"} for i in range(6)], delay=0.01),
            "row": to_row,                      # auto-wrapped as TransformerFunction
            "rec": RecordToList(out),           # real block
        },
        "connections": [
            ("gen", "row"),      # ports inferred -> out/in
            ("row", "rec"),
        ],
    }
    run_draft(draft)


if __name__ == "__main__":
    test_draft_objects_minimal()

from dsl.user_interaction.draft_runner import run_draft


draft = {
    "blocks": {
        "gen": {"class": "GenerateFromList", "params": {"items": [{"text": f"hello {i}"} for i in range(8)], "delay": 0.01}},
        "row": {"class": "FunctionToBlock", "params": {"func": lambda m: {"row": "- " + m["text"]}}},
        "batch": {"class": "Batcher", "params": {"N": 4}},
        "console": {"class": "ConsolePrettyPrinter", "params": {"sample_size": 4}},
    },
    "connections": [
        ("gen", "", "row", ""),            # ports omitted
        ("row", "", "batch", ""),          # ports omitted
        ("batch", "", "console", ""),      # ports omitted
    ]
}

if __name__ == "__main__":
    net, notes = run_draft(draft)

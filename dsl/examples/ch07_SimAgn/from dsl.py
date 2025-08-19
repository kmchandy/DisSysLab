from dsl.core import SimpleAgent


def make_similarity_agent_simple(reference_sentence: str, name: str = "SimilarityAgent(Simple)"):
    ref_words = set(str(reference_sentence).lower().split())

    def init_fn(agent):
        agent.state = {"ref": ref_words}
        print(f"[{name}] ref='{reference_sentence}' (overlap count)")

    def handle_msg(agent, msg, inport=None):
        toks = set(str(msg).lower().split())
        overlap = len(agent.state["ref"] & toks)
        agent.send({"input": str(msg), "overlap": overlap}, outport="out")

    return SimpleAgent(
        name=name,
        inport="in",
        outports=["out"],
        init_fn=init_fn,
        handle_msg=handle_msg,
    )


# Example (starter)
if __name__ == "__main__":
    from dsl.core import Network
    from dsl.block_lib.stream_generators import generate
    from dsl.block_lib.stream_recorders import RecordToList

    results = []
    net = Network(
        blocks={
            "gen": generate(["hello Jack", "hello there Jack", "goodbye there"], key="text"),
            "sim": make_similarity_agent_simple("hello there"),
            "rec": RecordToList(results),
        },
        connections=[
            ("gen", "out", "sim", "in"),
            ("sim", "out", "rec", "in"),
        ],
    )

    net.compile_and_run()
    print("Results (Tier 1):", results)

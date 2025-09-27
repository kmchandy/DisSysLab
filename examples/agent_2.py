from dsl import Graph
from dsl.extensions.agent_openai import AgentOpenAI


# def src():
#     for review in reviews:
#         yield {"review": review}

# def snk(v):
#     results.append(v)

# def to_list(v, target):
#     target.append(v)

def from_list_with_key(items, key):
    for item in items:
        yield {key: item}


def to_list(v, target):
    target.append(v)


def src():
    return from_list_with_key(items=reviews, key="review")


def snk(v):
    return to_list(v, target=results)


def trn(v):
    data = v["review"]
    output_AI = agent.fn(data)
    v["sentiment"] = output_AI
    return v


system_prompt = "Determine sentiment score in -10..+10 with -10 most negative, +10 most positive, and give a brief reason."
agent = AgentOpenAI(system_prompt=system_prompt)


reviews = [
    "The concert was terrible. I hated the performance.",
    "The book was okay, not too bad but not great either.",
    "This is the best course on AI I've ever taken!",
]

results = []
g = Graph(
    edges=[("src", "trn"), ("trn", "snk")],
    nodes={
        "src": (src, {}),
        "trn": (trn, {}),
        "snk": (snk, {}),
    },
)
g.compile_and_run()

if __name__ == "__main__":
    for result in results:
        for key, value in result.items():
            print(key)
            print(value)
        print("")

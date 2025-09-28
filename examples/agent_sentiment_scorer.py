from dsl import Graph
from dsl.extensions.agent_openai import AgentOpenAI

list_of_text = [
    "The concert was terrible. I hated the performance.",
    "The book was okay, not too bad but not great either.",
    "This is the best course on AI I've ever taken!",
]


def from_list_of_text():
    for data_item in list_of_text:
        yield {"text": data_item}


results = []
def to_results(v): results.append(v)


add_key = "sentiment"


def agent_op(v):
    v[add_key] = agent.fn(v["text"])
    return v


system_prompt = "Determine sentiment score in -10..+10 with -10 most negative, +10 most positive. Give a brief reason."
agent = AgentOpenAI(system_prompt=system_prompt)


g = Graph(
    edges=[("src", "trn"), ("trn", "snk")],
    nodes=[("src", from_list_of_text),
           ("trn", agent_op), ("snk", to_results)]
)
g.compile_and_run()

if __name__ == "__main__":
    for result in results:
        for key, value in result.items():
            print(key)
            print(value)
        print("")

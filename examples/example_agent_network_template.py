from dsl import Graph
from dsl.extensions.agent_openai import AgentOpenAI


class agent_with_key():
    def __init__(self, system_prompt, agent_key):
        self.system_prompt = system_prompt
        self.agent_key = agent_key
        self.agent = AgentOpenAI(system_prompt=system_prompt)

    def run(self, v):
        v[self.agent_key] = self.agent.fn(v["text"])
        return v


class pipeline_agent_network():
    def __init__(self, source_texts, agent_nodes, results):
        self.source_texts = source_texts
        self.agent_nodes = agent_nodes
        self.results = results
        self.network = None
        self.nodes = []
        self.edges = []

    def from_list_of_text(self):
        for data_item in self.source_texts:
            yield {"text": data_item}

    def to_results(self, v):
        self.results.append(v)

    def make_network(self):
        self.nodes = [("src", self.from_list_of_text)]

        # Make agent nodes
        agent_index = 0
        for agent_spec in self.agent_nodes:
            system_prompt, agent_key = agent_spec
            agent_name = f"agent_{agent_index}"
            agent_index += 1
            this_agent = agent_with_key(
                system_prompt=system_prompt, agent_key=agent_key)
            self.nodes.append(
                (agent_name, this_agent.run)
            )
        self.nodes.append(("snk", self.to_results))

        # Make pipeline connections
        for i in range(len(self.nodes) - 1):
            from_node_and_spec = self.nodes[i]
            to_node_and_spec = self.nodes[i+1]
            from_node = from_node_and_spec[0]
            to_node = to_node_and_spec[0]
            self.edges.append((from_node, to_node))

        return Graph(edges=self.edges, nodes=self.nodes)


if __name__ == "__main__":
    source_texts = [
        "Obama was the first African American president of the USA. He was great!",
        "The capital of India is New Delhi and Mrs. Indira Gandhi was a Prime Minister. She was unpopular.",
        "BRICS is an organization of Brazil, Russia, India, China and South Africa. Putin, Xi, and Modi met in Beijing. BRICS has had little impact."
    ]
    results = []

    system_prompt_0 = "Extract named entities. Return a JSON object with 'people', 'organizations', and 'locations'."
    key_0 = "entities: "

    system_prompt_1 = "Determine sentiment score in -10..+10 with -10 most negative, +10 most positive. Give a brief reason."
    key_1 = "sentiment"

    agent_nodes = ((system_prompt_0, key_0), (system_prompt_1, key_1))

    g = pipeline_agent_network(
        source_texts, agent_nodes, results).make_network()

    g.compile_and_run()

    for result in results:
        for key, value in result.items():
            print(key)
            print(value)
        print("")

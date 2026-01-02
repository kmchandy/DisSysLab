# modules.ch03_GPT.ai_simple_demo

from dsl import network
from dsl.extensions.agent_openai import AgentOpenAI
import json
from dsl.connectors.live_kv_console import kv_live_sink
from .source_list_of_text import source_list_of_text


def ai_simple_demo(list_of_text, system_prompt):
    source = source_list_of_text(list_of_text)
    ai_agent = AgentOpenAI(system_prompt=system_prompt)
    g = network([(source.run, ai_agent.run),
                 (ai_agent.run, kv_live_sink)])
    g.run_network()

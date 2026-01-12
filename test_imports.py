# Test in Python
from dsl import Agent, Network, STOP, PortReference, network, Graph, source_map, transform_map, sink_map
from dsl.blocks import Source, Transform, Sink, Broadcast, MergeAsynch, Split
from dsl.utils import visualize, get_anthropic_client, get_openai_client

print("✅ All imports successful!")

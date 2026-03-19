# test_source.py
from dsl import network
from dsl.blocks import Source, Sink
from components.sources.rss_normalizer import al_jazeera, bbc_world
from components.sinks.sink_jsonl_recorder import JSONLRecorder

_src_al_jazeera = al_jazeera(max_articles=2)
_src_bbc_world = bbc_world(max_articles=2)

source_al_jazeera = Source(fn=_src_al_jazeera.run, name="al_jazeera")
source_bbc_world = Source(fn=_src_bbc_world.run, name="bbc_world")

_recorder = JSONLRecorder(path="test_output.jsonl", mode="w", flush_every=1)
sink = Sink(fn=_recorder.run, name="recorder")

g = network([(source_al_jazeera, sink), (source_bbc_world, sink)])

if __name__ == "__main__":
    print("Starting...")
    g.run_network()
    print("Done — network terminated cleanly.")
    print("Output:")
    for line in open("test_output.jsonl"):
        import json
        print(f"  {json.loads(line)['title']}")

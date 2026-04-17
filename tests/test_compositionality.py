"""
Test composed_agent: a simple pipeline wrapped as a composed agent,
then embedded in an outer network.

Inner network:
    input → to_lower → add_bang → output

Outer network:
    source → pipeline.input
    pipeline.output → sink
"""
from dissyslab.composed_agent import composed_agent
from dissyslab.blocks import Source, Transform, Sink
from dissyslab import network
import sys
sys.path.insert(0, "/home/claude")


# ── Inner agents ──────────────────────────────────────────────────────────────

def to_lower(msg):
    return {**msg, "text": msg["text"].lower()}


def add_bang(msg):
    return {**msg, "text": msg["text"] + "!"}


transform_1 = Transform(fn=to_lower,  name="to_lower")
transform_2 = Transform(fn=add_bang,  name="add_bang")


# ── Composed agent ────────────────────────────────────────────────────────────

pipeline = composed_agent(
    name="pipeline",
    inputs=["input"],
    outputs=["output"],
)
pipeline.network = [
    (pipeline.input,  transform_1),
    (transform_1,     transform_2),
    (transform_2,     pipeline.output),
]

print("✓ composed_agent created and wired")
print(f"  inner network blocks: {list(pipeline.blocks.keys())}")
print(f"  inner connections:    {pipeline.connections}")


# ── Outer source and sink ─────────────────────────────────────────────────────

items = [{"text": "Hello"}, {"text": "WORLD"}, {"text": "DisSysLab"}]
idx = [0]


def source_fn():
    if idx[0] >= len(items):
        return None
    msg = items[idx[0]]
    idx[0] += 1
    return msg


results = []

src = Source(fn=source_fn,    name="source")
snk = Sink(fn=results.append, name="sink")


# ── Outer network ─────────────────────────────────────────────────────────────

g = network([
    (src,              pipeline.input),
    (pipeline.output,  snk),
])

print("\n✓ outer network created")
print(f"  outer blocks: {list(g.blocks.keys())}")
print(f"  outer connections: {g.connections}")


# ── Run ───────────────────────────────────────────────────────────────────────

g.run_network(timeout=10)

print("\n✓ run_network completed")
print(f"  results: {results}")

# ── Assertions ────────────────────────────────────────────────────────────────

assert len(results) == 3,         f"Expected 3 results, got {len(results)}"
assert results[0]["text"] == "hello!",    f"Got {results[0]}"
assert results[1]["text"] == "world!",    f"Got {results[1]}"
assert results[2]["text"] == "dissyslab!", f"Got {results[2]}"

print("\n✅ All assertions passed!")
print("   'Hello'    → 'hello!'")
print("   'WORLD'    → 'world!'")
print("   'DisSysLab' → 'dissyslab!'")

"""
Test composed_agent of composed_agents:
    pipeline_1: to_lower → add_bang
    pipeline_2: strip_spaces → add_prefix
    pipeline_0: pipeline_1 → pipeline_2

Outer network:
    source → pipeline_0.input → pipeline_0.output → sink

Expected:
    "  Hello World  " → lower → bang → strip → prefix
    = "hello world !" stripped = "hello world !" → ">>> hello world !"
"""
from dsl.composed_agent import composed_agent
from dsl.blocks import Source, Transform, Sink
from dsl import network
import sys
sys.path.insert(0, "/home/claude")


# ── Inner agents for pipeline_1 ───────────────────────────────────────────────

def to_lower(msg):
    return {**msg, "text": msg["text"].lower()}


def add_bang(msg):
    return {**msg, "text": msg["text"] + "!"}


transform_1_1 = Transform(fn=to_lower,  name="to_lower")
transform_1_2 = Transform(fn=add_bang,  name="add_bang")


# ── pipeline_1 ────────────────────────────────────────────────────────────────

pipeline_1 = composed_agent(
    name="pipeline_1",
    inputs=["input"],
    outputs=["output"],
)
pipeline_1.network = [
    (pipeline_1.input,  transform_1_1),
    (transform_1_1,     transform_1_2),
    (transform_1_2,     pipeline_1.output),
]

print("✓ pipeline_1 wired")
print(f"  blocks: {list(pipeline_1.blocks.keys())}")


# ── Inner agents for pipeline_2 ───────────────────────────────────────────────

def strip_spaces(msg):
    return {**msg, "text": msg["text"].strip()}


def add_prefix(msg):
    return {**msg, "text": ">>> " + msg["text"]}


transform_2_1 = Transform(fn=strip_spaces, name="strip_spaces")
transform_2_2 = Transform(fn=add_prefix,   name="add_prefix")


# ── pipeline_2 ────────────────────────────────────────────────────────────────

pipeline_2 = composed_agent(
    name="pipeline_2",
    inputs=["input"],
    outputs=["output"],
)
pipeline_2.network = [
    (pipeline_2.input,  transform_2_1),
    (transform_2_1,     transform_2_2),
    (transform_2_2,     pipeline_2.output),
]

print("✓ pipeline_2 wired")
print(f"  blocks: {list(pipeline_2.blocks.keys())}")


# ── pipeline_0: composed agent of pipeline_1 and pipeline_2 ──────────────────

pipeline_0 = composed_agent(
    name="pipeline_0",
    inputs=["input"],
    outputs=["output"],
)
pipeline_0.network = [
    (pipeline_0.input,   pipeline_1),
    (pipeline_1,         pipeline_2),
    (pipeline_2,         pipeline_0.output),
]

print("✓ pipeline_0 wired (composed of pipeline_1 and pipeline_2)")
print(f"  blocks: {list(pipeline_0.blocks.keys())}")
print(f"  connections: {pipeline_0.connections}")


# ── Outer source and sink ─────────────────────────────────────────────────────

items = [
    {"text": "  Hello World  "},
    {"text": "  DISSYSLAB  "},
    {"text": "  Python Rules  "},
]
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
    (src,               pipeline_0.input),
    (pipeline_0.output, snk),
])

print("\n✓ outer network created")
print(f"  outer blocks: {list(g.blocks.keys())}")
print(f"  outer connections: {g.connections}")


# ── Run ───────────────────────────────────────────────────────────────────────

g.run_network(timeout=10)

print("\n✓ run_network completed")
print(f"  results: {results}")


# ── Assertions ────────────────────────────────────────────────────────────────

assert len(results) == 3, f"Expected 3 results, got {len(results)}"
assert results[0]["text"] == ">>> hello world  !", f"Got {results[0]}"
assert results[1]["text"] == ">>> dissyslab  !",   f"Got {results[1]}"
assert results[2]["text"] == ">>> python rules  !", f"Got {results[2]}"

print("\n✅ All assertions passed!")
for item, result in zip(items, results):
    print(f"   {item['text']!r:22} → {result['text']!r}")

# ============================================================================
# EXEMPLAR: Externalize a Pipeline Network
# ============================================================================

"""
This example shows how to build, test, and externalize a network for reuse.

The pattern:
1. Build a complete network with test sources/sinks
2. Test it end-to-end
3. Treat the network as a subnetwork in a larger network by treating source ports as 
   input ports of the subnetwork, and sink ports as output ports of the subnetwork..
4. Use the externalized network as a component in a larger system
"""

from dsl import network, as_component
from dsl.blocks import Source, Transform, Sink
from components.sources import NumberSequenceSource
from components.sinks import ListCollector


# ============================================================================
# Step 1: Define the Processing Components
# ============================================================================

class Doubler:
    """Doubles the input value"""

    def run(self, msg):
        return {"value": msg["value"] * 2}


class Tripler:
    """Triples the input value"""

    def run(self, msg):
        return {"value": msg["value"] * 3}


# ============================================================================
# Step 2: Build Complete Network with Test Data
# ============================================================================

# Create agents
test_source_data = NumberSequenceSource([1, 2, 3])
test_source = Source(test_source_data.run)

doubler = Transform(Doubler().run)
tripler = Transform(Tripler().run)

test_collector = ListCollector(value_key="value", name="Test Results")
test_sink = Sink(test_collector.run)

# Build the complete pipeline
inner = network([
    (test_source, doubler),
    (doubler, tripler),
    (tripler, test_sink)
])

# Test it works!
print("Testing inner network...")
inner.run_network()
print(f"Results: {test_collector.collected}")  # Should be [6, 12, 18]
assert test_collector.collected == [6, 12, 18], "Test failed!"
print("✓ Inner network works!\n")


# ============================================================================
# Step 3: Externalize for Reuse
# ============================================================================

# Transform the network: replace test_source and test_sink with external ports
multiply_by_six = as_component(
    inner,
    # Replace test_source with external.in_
    inports=[("in_", test_source)],
    outports=[("out_", test_sink)]       # Replace test_sink with external.out_
)

# Now multiply_by_six is a reusable component with:
# - One input port: multiply_by_six.in_ (or just use multiply_by_six)
# - One output port: multiply_by_six.out_ (or just use multiply_by_six)


# ============================================================================
# Step 4: Use in a Larger Network
# ============================================================================

# Create production data sources and sinks
prod_source_data = NumberSequenceSource([10, 20, 30])
prod_source = Source(prod_source_data.run)

prod_collector = ListCollector(value_key="value", name="Production Results")
prod_sink = Sink(prod_collector.run)

# Use the externalized component
outer = network([
    (prod_source, multiply_by_six),
    (multiply_by_six, prod_sink)
])

print("Running production network with multiply_by_six component...")
outer.run_network()
print(f"Results: {prod_collector.collected}")  # Should be [60, 120, 180]
assert prod_collector.collected == [60, 120, 180], "Production test failed!"
print("✓ Production network works!\n")


# ============================================================================
# What Happened During Externalization?
# ============================================================================

"""
BEFORE externalize():
    inner graph edges:
        (test_source, "out_", doubler, "in_")
        (doubler, "out_", tripler, "in_")
        (tripler, "out_", test_sink, "in_")
    
    inner graph nodes:
        test_source, doubler, tripler, test_sink

AFTER externalize(inner, inports=[("in_", test_source)], outports=[("out_", test_sink)]):
    multiply_by_six network connections:
        ("external", "in_", doubler, "in_")      # ← test_source replaced
        (doubler, "out_", tripler, "in_")        # ← unchanged
        (tripler, "out_", "external", "out_")    # ← test_sink replaced
    
    multiply_by_six network blocks:
        doubler, tripler                          # ← test_source and test_sink removed
    
    multiply_by_six network ports:
        inports = ["in_"]
        outports = ["out_"]

WHEN USED in outer network:
    Final compiled edges (after resolving external):
        (prod_source, "out_", doubler, "in_")    # ← external.in_ resolved
        (doubler, "out_", tripler, "in_")
        (tripler, "out_", prod_sink, "in_")      # ← external.out_ resolved
"""

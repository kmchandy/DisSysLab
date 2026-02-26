"""
General DAG Pattern - Arbitrary Acyclic Graph

Pattern: Complex network with multiple sources, processors, and sinks.
Shows that DisSysLab supports ANY acyclic topology.

Topology:
    source_A ─┬→ validate_A ─┬→ processor_1 ─┐
              │              │                ├→ final_merge → sink
    source_B ─┴→ validate_B ─┴→ processor_2 ─┘

Use case: Complex data pipeline with validation, parallel processing, and aggregation.

Example: Multiple data sources → validate → process → merge → store
"""

from dsl import network
from components.sources import ListSource
from dsl.blocks import Source, Transform, Sink

# ==============================================================================
# STEP 1: Write Ordinary Python Functions Independent of DSL
# ==============================================================================

# Two data sources
source_A_data = ListSource(items=[10, 20, 30])
source_B_data = ListSource(items=[15, 25, 35])


def validate_positive(n):
    """Validate: keep only positive numbers."""
    if n > 0:
        return n
    return None


def process_type_1(n):
    """Process: double the number."""
    return {"type": "doubled", "value": n * 2}


def process_type_2(n):
    """Process: square the number."""
    return {"type": "squared", "value": n ** 2}


def merge_results(result):
    """Format the result for final output."""
    return f"{result['type']}: {result['value']}"


# ==============================================================================
# STEP 2: Specify nodes of the network by wrapping the functions
# ==============================================================================

# Two sources
source_A = Source(fn=source_A_data.run, name="source_A")
source_B = Source(fn=source_B_data.run, name="source_B")

# Validators (both sources use same validation logic)
validate_A = Transform(fn=validate_positive, name="validate_A")
validate_B = Transform(fn=validate_positive, name="validate_B")

# Processors (different processing for each path)
processor_1 = Transform(fn=process_type_1, name="processor_1")
processor_2 = Transform(fn=process_type_2, name="processor_2")

# Final merge and format
final_merge = Transform(fn=merge_results, name="final_merge")

# Collector
results = []
collector = Sink(fn=results.append, name="collector")


# ==============================================================================
# STEP 3: Build and Run the Network - General DAG
# ==============================================================================

g = network([
    # Sources to validators
    (source_A, validate_A),
    (source_B, validate_B),

    # Validators to processors (FANIN: both validators → processor_1)
    (validate_A, processor_1),
    (validate_B, processor_1),

    # Also: validate_A → processor_2 (creating complex topology)
    (validate_A, processor_2),

    # Processors to final merge (FANIN: both processors → final_merge)
    (processor_1, final_merge),
    (processor_2, final_merge),

    # Final merge to collector
    (final_merge, collector)
])

g.run_network()


# ==============================================================================
# Verify Results
# ==============================================================================
if __name__ == "__main__":
    print("General DAG Pattern Results")
    print("=" * 50)
    print("Results:")
    for result in results:
        print(f"  {result}")

    print(f"\n✓ General DAG completed successfully!")
    print(f"  Total results: {len(results)}")
    print(f"\nData flow:")
    print(
        f"  source_A [10,20,30] → validate_A → processor_1 (doubled) AND processor_2 (squared)")
    print(f"  source_B [15,25,35] → validate_B → processor_1 (doubled)")
    print(f"  All paths converge at final_merge → collector")
    print(f"\nThis demonstrates an arbitrary acyclic graph topology!")

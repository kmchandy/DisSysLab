"""
Module 09, Example 1: File Processing Pipeline (REAL)

This is the REAL version - creates actual files!

Network:
    CSV File → [Filter Active] → [Summarize] → JSON File
    
What you'll learn:
- Same pattern as demo, but with real file I/O
- How easy it is to switch from demo → real (2 lines!)
- Production file processing

Time: 10 seconds to run | Creates actual output file
"""

import os
from dsl import network
from dsl.blocks import Source, Transform, Sink

# Import components (REAL VERSION - actual file I/O)
# THIS IS THE ONLY CHANGE FROM DEMO!
from components.sources.file_source import FileSource
from components.sinks.file_writer import FileWriter


# ============================================================================
# STEP 1: Create Source - Read Customer Data from Real File
# ============================================================================

# Path to sample data (we'll create it if it doesn't exist)
sample_file = "sample_customers.csv"

# Create sample file if it doesn't exist
if not os.path.exists(sample_file):
    print(f"Creating sample file: {sample_file}")
    with open(sample_file, 'w') as f:
        f.write("id,name,email,age,city,status\n")
        f.write("1,Alice Johnson,alice@email.com,28,New York,active\n")
        f.write("2,Bob Smith,bob@email.com,34,San Francisco,active\n")
        f.write("3,Carol White,carol@email.com,45,Chicago,inactive\n")
        f.write("4,David Brown,david@email.com,31,Boston,active\n")
        f.write("5,Emma Davis,emma@email.com,26,Seattle,active\n")
        f.write("6,Frank Miller,frank@email.com,52,Miami,inactive\n")
        f.write("7,Grace Wilson,grace@email.com,29,Denver,active\n")
        f.write("8,Henry Moore,henry@email.com,38,Austin,active\n")
        f.write("9,Iris Taylor,iris@email.com,41,Portland,inactive\n")
        f.write("10,Jack Anderson,jack@email.com,33,Atlanta,active\n")

# Read from REAL CSV file
customer_source = FileSource(filepath=sample_file, format="csv")
source = Source(fn=customer_source.run, name="customers")


# ============================================================================
# STEP 2: Create Transform - Filter Active Customers
# ============================================================================

def filter_active(customer: dict):
    """Keep only active customers."""
    if customer.get("status") == "active":
        return customer
    else:
        return None  # Filter out inactive


filter_node = Transform(fn=filter_active, name="filter_active")


# ============================================================================
# STEP 3: Create Transform - Summarize Customer
# ============================================================================

def summarize_customer(customer: dict):
    """Add a summary field to customer."""
    summary = f"{customer['name']} ({customer['age']}) from {customer['city']}"
    customer["summary"] = summary
    return customer


summarize_node = Transform(fn=summarize_customer, name="summarize")


# ============================================================================
# STEP 4: Create Sink - Write to REAL File
# ============================================================================

# Create REAL file writer (actually creates the file!)
output_file = "active_customers.json"
writer = FileWriter(filepath=output_file, format="json")
sink = Sink(fn=writer.run, name="file_writer")


# ============================================================================
# STEP 5: Build Network
# ============================================================================

g = network([
    (source, filter_node),           # Read → Filter
    (filter_node, summarize_node),   # Filter → Summarize
    (summarize_node, sink)            # Summarize → Write
])


# ============================================================================
# STEP 6: Run Network
# ============================================================================

print("=" * 70)
print("EXAMPLE 1: FILE PROCESSING PIPELINE (REAL)")
print("=" * 70)
print("\nProcessing customer data from REAL file...")
print(f"Input: {sample_file}")
print(f"Output: {output_file}\n")

g.run_network()

# Finalize (actually writes the file!)
writer.finalize()


# ============================================================================
# VERIFICATION
# ============================================================================

print("\n" + "=" * 70)
print("VERIFICATION - Check the Output File!")
print("=" * 70)

if os.path.exists(output_file):
    print(f"\n✓ File created: {output_file}")

    # Show file size
    size = os.path.getsize(output_file)
    print(f"  Size: {size} bytes")

    # Show first few lines
    print(f"\n  Preview:")
    with open(output_file, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines[:8]):
            print(f"    {line.rstrip()}")
        if len(lines) > 8:
            print(f"    ... ({len(lines) - 8} more lines)")

    print(f"\n  To view the full file, run:")
    print(f"    cat {output_file}")
    print(f"  Or open it in your editor:")
    print(f"    code {output_file}")
else:
    print(f"\n✗ File NOT created: {output_file}")


# ============================================================================
# KEY INSIGHTS
# ============================================================================

print("\n" + "=" * 70)
print("WHAT JUST HAPPENED")
print("=" * 70)
print("""
Real File Processing!

The ONLY difference from demo version:
- Changed import: demo_file → file_source
- Changed import: demo_file_writer_sink → file_writer_sink

Everything else is IDENTICAL!

This is the power of the demo → real pattern:
1. Learn with demo (instant, safe, offline)
2. Switch to real (2 lines of code)
3. Production-ready!

The network, transforms, logic - all the same.
Just swap the source and sink.
""")


# ============================================================================
# NEXT STEPS
# ============================================================================

print("=" * 70)
print("NEXT STEPS")
print("=" * 70)
print("""
✓ You built a REAL file processing pipeline!

What you learned:
- Demo → Real pattern (just 2 imports changed!)
- Actual file I/O (CSV → JSON)
- Production file processing
- Same interface, real results

Try these experiments:
1. Change input file: Create your own CSV
   - Add more customers
   - Different fields
   - Try different data

2. Change output format:
   writer = FileWriter("output.csv", format="csv")
   writer = FileWriter("output.jsonl", format="jsonl")

3. Process different data:
   - Create events.json
   - Filter by type, amount, etc.
   - Transform timestamps, aggregate data

4. Build a real pipeline for YOUR data:
   - What data do you have?
   - What do you want to filter?
   - What transformations do you need?

Next example: demo_example_02_social_monitor.py
- Monitor social media (BlueSky)
- Multiple AI transforms
- Multiple outputs (fanout pattern)
- Real-time monitoring system

You now have the foundation. Ready to build bigger!
""")

print("=" * 70 + "\n")

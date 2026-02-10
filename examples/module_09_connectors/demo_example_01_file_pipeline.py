"""
Module 09, Example 1: File Processing Pipeline (DEMO)

This is your FIRST complete Source → Transform → Sink pipeline!

Network:
    CSV File → [Filter Active] → [Summarize] → File Output
    
What you'll learn:
- How to read from files (Source)
- How to filter data (Transform)
- How to write to files (Sink)
- The complete data flow

Time: 5 seconds to run | No setup needed | Works offline
"""

from dsl import network
from dsl.blocks import Source, Transform, Sink

# Import components (DEMO VERSION - no file I/O)
from components.sources.demo_file import DemoFileSource
from components.sinks.demo_file_writer import DemoFileWriter


# ============================================================================
# STEP 1: Create Source - Read Customer Data
# ============================================================================

# Read demo customers CSV (50 customers included)
customer_source = DemoFileSource(filename="customers", format="csv")
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
# STEP 4: Create Sink - Write to File
# ============================================================================

# Create demo file writer (prints instead of writing)
writer = DemoFileWriter(filename="active_customers.json", format="json")
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
print("EXAMPLE 1: FILE PROCESSING PIPELINE (DEMO)")
print("=" * 70)
print("\nProcessing customer data...")
print("Reading → Filtering → Summarizing → Writing\n")

g.run_network()

# Finalize (show what would be written)
writer.finalize()


# ============================================================================
# KEY INSIGHTS
# ============================================================================

print("\n" + "=" * 70)
print("WHAT JUST HAPPENED")
print("=" * 70)
print("""
The Complete Pattern: Source → Transform → Sink

1. SOURCE (DemoFileSource):
   - Read 50 customers from demo CSV
   - Yielded each customer as dict

2. TRANSFORM #1 (filter_active):
   - Checked each customer's status
   - Returned None for inactive (filtered out)
   - Returned dict for active (passed through)

3. TRANSFORM #2 (summarize_customer):
   - Added summary field to each customer
   - Enriched the data

4. SINK (DemoFileWriter):
   - Collected all results
   - Showed what would be written to JSON file

You just built your first complete data pipeline!
""")


# ============================================================================
# NEXT STEPS
# ============================================================================

print("=" * 70)
print("NEXT STEPS")
print("=" * 70)
print("""
✓ You built a complete Source → Transform → Sink pipeline!

What you learned:
- How to read data from files (Source)
- How to filter data (return None)
- How to transform/enrich data
- How to write results (Sink)

Try these experiments:
1. Change the filter: filter by city or age
   def filter_young(customer):
       return customer if customer['age'] < 30 else None

2. Add another transform: calculate age groups
   def add_age_group(customer):
       if customer['age'] < 30:
           customer['age_group'] = 'young'
       elif customer['age'] < 50:
           customer['age_group'] = 'middle'
       else:
           customer['age_group'] = 'senior'
       return customer

3. Change output format: try format="csv"
   writer = DemoFileWriter("output.csv", format="csv")

4. Chain more transforms: sorting, grouping, statistics

Next example: example_01_file_pipeline.py
- Same network with REAL file I/O
- Actually creates the output file
- See the one-line change from demo → real

Run it:
  python3 example_01_file_pipeline.py
  
Then check: active_customers.json (it's a real file!)
""")

print("=" * 70 + "\n")

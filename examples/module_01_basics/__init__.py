"""
Module 01: Basics - Your First DisSysLab Network

Learn the fundamentals of building distributed systems using ordinary Python functions.

The Problem:
    Traditional programs: get data → process → save → terminate (sequential)
    DisSysLab programs: persistent (run forever) OR concurrent (steps run in parallel)

What You'll Learn:
    - The three basic node types: Source, Transform, Sink
    - How to wrap ordinary Python functions into network nodes
    - How to define network topology as a directed graph
    - How nodes execute concurrently with automatic message passing
    - The fundamental pattern used in ALL DisSysLab programs

The Four-Step Pattern (used in every DisSysLab program):
    1. Write ordinary Python functions
    2. Wrap functions into nodes (Source, Transform, Sink)
    3. Define network topology (list of edges)
    4. Run the network

Example Network:
    ["hello", "world"] → UPPERCASE → ADD "!!" → results
          ↓                 ↓            ↓           ↓
       (source)        (transform)  (transform)  (sink)

Key Concepts:
    - Separation of concerns: What (your functions) vs How (DisSysLab execution)
    - Network as a directed graph: nodes + edges
    - Messages flow automatically through queues
    - Concurrent execution: all nodes run simultaneously
    - Three node types with distinct roles

Prerequisites:
    - Basic Python programming
    - Understanding of functions
    - Familiarity with lists and dictionaries

Time to Complete: 30-45 minutes

Files:
    - README.md: Complete tutorial with step-by-step walkthrough
    - example.py: Working pipeline example (hello → HELLO!!)

Start Here:
    1. Read README.md (20 min) - understand the concepts
    2. Run example.py (2 min) - see it work
    3. Try the experiments (10 min) - modify and explore
    4. When ready, move to Module 02: Filtering

Running the Example:
    python3 -m examples.module_01_basics.example

Expected Output:
    Results: ['HELLO!!', 'WORLD!!']
    ✓ Pipeline completed successfully!

Remember:
    Every DisSysLab program follows the same four steps.
    Master this pattern and you can build any distributed system!
"""

# Module metadata
__version__ = "1.0.0"
__author__ = "DisSysLab Team"
__status__ = "Production"

# Key concepts from this module
__concepts__ = [
    "Source nodes generate data",
    "Transform nodes process data",
    "Sink nodes consume data",
    "Networks are directed graphs",
    "Nodes execute concurrently",
    "Messages flow automatically"
]

# The fundamental pattern
__pattern__ = """
1. Write Python functions
2. Wrap into nodes: Source(fn=...), Transform(fn=...), Sink(fn=...)
3. Define topology: network([(node1, node2), (node2, node3)])
4. Run: g.run_network()
"""

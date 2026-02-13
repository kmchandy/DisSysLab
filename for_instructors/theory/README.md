# Module 8: Distributed Algorithms

## Overview

In this module, you'll learn three fundamental **distributed algorithms** that solve classic problems in distributed systems. Each algorithm addresses a challenge you've likely encountered in your own networks:

- **Leader Election**: How do agents coordinate when they need a single leader?
- **Termination Detection**: How do you know when a distributed computation is done?
- **Global Snapshots**: How do you capture a consistent view of the entire system's state?

These are foundational algorithms that appear in real distributed systems like databases, consensus protocols, and cloud platforms.

---

## What You'll Learn

By the end of this module, you will:

1. **Understand classic distributed systems problems**
   - Why leader election is needed
   - Why termination detection is hard in cyclic networks
   - Why capturing global state requires coordination

2. **Implement distributed algorithms**
   - Ring-based leader election
   - Dijkstra-Scholten termination detection
   - Chandy-Lamport global snapshots

3. **Apply algorithms to real scenarios**
   - Coordinating agents in a network
   - Detecting when iterative refinement is complete
   - Checkpointing running systems

---

## Prerequisites

Before starting this module, you should:

- ✅ Understand networks with cycles (Module 7)
- ✅ Be comfortable with message-passing patterns
- ✅ Understand agent state and local computation

---

## Module Contents

### **Example 1: Leader Election** (`leader_election.py`)
**Problem**: In a ring of agents, elect exactly one leader.

**Algorithm**: Ring-based election where each agent sends its ID around the ring. The agent with the highest ID becomes leader.

**Learning Goals**:
- Understand the leader election problem
- See how ring topology simplifies coordination
- Learn about termination in distributed algorithms

---

### **Example 2: Termination Detection** (`termination_detection.py`)
**Problem**: In a network with cycles, how do you know when all computation is finished?

**Algorithm**: Dijkstra-Scholten credit-based detection where credits are passed with messages and returned when processing completes.

**Learning Goals**:
- Understand why termination is hard in cyclic networks
- Learn credit-based approach to detecting quiescence
- See how to integrate termination detection into applications

**Real-world Application**: Iterative refinement loops, distributed search, graph algorithms

---

### **Example 3: Global Snapshots** (`global_snapshot.py`)
**Problem**: How do you capture a consistent view of the entire distributed system's state?

**Algorithm**: Chandy-Lamport snapshot where marker messages propagate through the network to coordinate state capture.

**Learning Goals**:
- Understand the challenge of consistent global state
- Learn how markers coordinate snapshot timing
- See how to capture both agent state and channel state

**Real-world Application**: Debugging, checkpointing, deadlock detection

---

## Key Concepts

### **1. Distributed Coordination**
Unlike centralized systems, distributed agents must coordinate through **message passing** only. No shared memory, no global clock.

### **2. Algorithm Correctness**
Distributed algorithms must ensure:
- **Safety**: Nothing bad happens (e.g., at most one leader)
- **Liveness**: Something good eventually happens (e.g., a leader is elected)

### **3. Termination**
Many distributed algorithms must detect their own completion. This is harder than it sounds!

### **4. Consistent State**
In a running distributed system, capturing a "snapshot" requires careful coordination to ensure consistency.

---

## How to Use This Module

### **Start Simple**
1. Read and run `leader_election.py` first
2. Understand how messages flow in a ring
3. Experiment: what happens with different numbers of agents?

### **Build Up**
1. Move to `termination_detection.py`
2. See how credits track active computation
3. Apply to your own iterative networks from Module 7

### **Go Deep**
1. Study `global_snapshot.py`
2. Understand marker propagation
3. Use snapshots to debug your own networks

---

## Connection to Other Modules

- **Module 7 (Cycles)**: Provides the cyclic networks where these algorithms are needed
- **Module 9 (Consensus)**: Builds on these algorithms for fault-tolerant agreement
- **Module 2 (Component Library)**: Shows the building blocks used in these examples

---

## Next Steps

After mastering these algorithms, you'll be ready for:
- **Module 9**: Consensus and fault tolerance (Paxos, Byzantine agreement)
- **Advanced topics**: Vector clocks, causal ordering, distributed transactions

---

## Resources

### **Classic Papers**
- Chandy & Lamport (1985): "Distributed Snapshots: Determining Global States"
- Dijkstra & Scholten (1980): "Termination Detection for Diffusing Computations"

### **Further Reading**
- Distributed Systems course materials (see your course website)
- "Distributed Algorithms" by Nancy Lynch (advanced textbook)

---

## Questions to Explore

As you work through these examples, think about:

1. **Scalability**: How do these algorithms perform with 100 agents? 1000?
2. **Failures**: What happens if an agent crashes mid-algorithm?
3. **Applications**: Where would you use these in your own projects?

Have fun exploring the foundations of distributed systems! 🚀

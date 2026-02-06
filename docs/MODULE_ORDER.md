# DisSysLab Module Learning Sequence

This document defines the recommended order for working through DisSysLab modules.

## Quick Start

**New to DisSysLab?** Start with `examples/module_01_basics/` - you'll build your first distributed system in 5 minutes!

## Learning Path

### Module 1: Introduction to DisSysLab

**Path:** `examples/module_01_basics/`

Build your first network in 5 minutes. Learn Source, Transform, and Sink nodes.

**Read:** See the [module README](examples/module_01_basics/README.md) for complete details and examples.

---

### Module 2: Message Filtering

**Path:** `examples/module_02_filtering/`

Learn how returning None drops messages. Build conditional filters.

**Read:** See the [module README](examples/module_02_filtering/README.md) for complete details and examples.

---

### Module 3: Fanout Pattern

**Path:** `examples/module_03_fanout/`

Broadcast messages to multiple destinations. Process in parallel.

**Read:** See the [module README](examples/module_03_fanout/README.md) for complete details and examples.

---

### Module 4: Fanin Pattern

**Path:** `examples/module_04_fanin/`

Merge multiple sources into one processor. Handle diverse inputs.

**Read:** See the [module README](examples/module_04_fanin/README.md) for complete details and examples.

---

### Module 5: Complex Topologies

**Path:** `examples/module_05_complex_patterns/`

Combine fanin and fanout. Build sophisticated graph structures.

**Read:** See the [module README](examples/module_05_complex_patterns/README.md) for complete details and examples.

---

### Module 6: Numeric Processing

**Path:** `examples/module_06_numeric/`

Integrate NumPy and pandas. Process arrays and DataFrames.

**Read:** See the [module README](examples/module_06_numeric/README.md) for complete details and examples.

---

### Module 7: Text Processing

**Path:** `examples/module_07_text_nlp/`

Build NLP pipelines. Clean, tokenize, and analyze text.

**Read:** See the [module README](examples/module_07_text_nlp/README.md) for complete details and examples.

---

### Module 8: Machine Learning

**Path:** `examples/module_08_ml/`

Create ML pipelines with scikit-learn. Train and predict.

**Read:** See the [module README](examples/module_08_ml/README.md) for complete details and examples.

---

### Module 9: AI Agents

**Path:** `examples/module_09_ai_agents/`

Use Claude for intelligent processing. Master prompt engineering.

**Read:** See the [module README](examples/module_09_ai_agents/README.md) for complete details and examples.

---

### Module 10: Data Pipelines

**Path:** `examples/module_10_data_pipeline/`

Build ETL systems. Read, transform, and write data.

**Read:** See the [module README](examples/module_10_data_pipeline/README.md) for complete details and examples.

---

### Module 11: Real-World Applications

**Path:** `examples/module_11_real_world/`

Complete projects: RSS aggregators, social media analysis, and more.

**Read:** See the [module README](examples/module_11_real_world/README.md) for complete details and examples.

---


## How to Use This Guide

1. **Start at Module 1** - Build your first network in 5 minutes
2. **Progress sequentially** - Each module builds on previous concepts
3. **Read the README** - Each module has detailed explanations
4. **Run the examples** - Execute code to see it work
5. **Do the exercises** - Practice problems in each module
6. **Experiment** - Modify examples to understand behavior
7. **Build your own** - After Module 5, try creating your own applications

## Module Categories

### Fundamentals (Modules 1-5)
Core concepts and patterns you need to know:
- Basic node types and message flow
- Filtering and conditional logic
- Network topologies (fanin, fanout)
- Complex graph structures

### Integration (Modules 6-9)
Connecting DisSysLab with the Python ecosystem:
- NumPy and pandas for data science
- NLP libraries for text processing
- scikit-learn for machine learning
- AI agents with Claude

### Applications (Modules 10-11)
Building real systems:
- Data pipelines and ETL
- Complete production applications
- Best practices and patterns

## Prerequisites

- Python 3.8+
- Basic Python knowledge (functions, classes, lists, dicts)
- No distributed systems experience required!

## Additional Resources

- **[Quick Start](README.md#quick-start)** - Get running in 5 minutes
- **[How It Works](docs/HOW_IT_WORKS.md)** - Understand the system
- **[API Reference](docs/api/)** - Complete documentation
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues
- **[Architecture](DOCUMENTATION_STRATEGY.md)** - System design

## Getting Help

- Check the module README first
- Look at working examples in the module
- Read [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) for conceptual understanding
- Check [docs/troubleshooting.md](docs/troubleshooting.md) for common errors
- Look at other modules for patterns

## Contributing

Want to add a module or improve existing ones? See [CONTRIBUTING.md](CONTRIBUTING.md) (to be created).

---

*Last updated: January 2026*
*Part of DisSysLab - A teaching framework for distributed systems*

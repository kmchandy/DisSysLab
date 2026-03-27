# DisSysLab — Module Sequence

This directory contains a progressive sequence of modules for learning
how to build distributed systems with DisSysLab.

Each module builds on the previous one. Start at Module 01 and work through
in order. Each module has its own README with explanations, working code,
and exercises.

---

## Module Sequence

| Module | Title | What you learn |
|--------|-------|---------------|
| [01](module_01/README.md) | Describe and Build | Ask Claude to generate your first network. Run it. Make it yours. |
| [02](module_02/README.md) | Multiple Sources, Multiple Destinations | Read from two feeds at once. Send results to two places at once. Fanin and fanout. |
| [03](module_03/README.md) | Smart Routing | Send the right message to the right place. Filtering and splitting. |
| [04](module_04/README.md) | Build Your Own App | Design and build a complete app from scratch. |
| [05](module_05/README.md) | Job Postings Monitor | A real app: monitor job boards and get alerted when relevant postings appear. |
| [06](module_06/README.md) | Gather-Scatter | Watch a reinforcement learning agent train while three analyzers observe it simultaneously. |
| [07](module_07/README.md) | Photo Quality Scorer | Analyze every image three ways simultaneously — a gather-scatter pattern with threads. |
| [08](module_08/README.md) | Photo Quality Scorer — Process Edition | The same app as Module 07. One word changed. True CPU parallelism with processes. |
| [09](module_09/README.md) | Container Edition | The same app. A new envelope. Package your network and run it anywhere. |
| [10](module_10/README.md) | Cloud Edition | Deploy your network to the cloud. |

---

## How to Run Any Module

From the DisSysLab root directory:

```bash
python3 -m examples.module_01.app
```

Replace `module_01` with the module you want to run, and `app` with the
specific file. Each module README lists the exact commands.

---

## Before You Start

1. Complete installation from the main [README.md](../README.md)
2. Set your API key:
   ```bash
   export ANTHROPIC_API_KEY='your-key-here'
   ```
3. Start with [Module 01](module_01/README.md)

Modules 01–04 use demo components — no API key needed.
From Module 05 onward, a real API key is required.
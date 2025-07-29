# DisSysLab: Multi-Agent Collaboration by Passing Messages

**DisSysLab** is a simple framework for building applications in which multiple
agents collaborate by exchanging messages.

Its goals are:
- 🧑‍🎓 **Accessibility**: Help non-programmers build distributed applications by assembling reusable blocks.
- 🧑‍💻 **Extensibility**: Allow programmers to use the framework in their Python code just as they would use any Python class.

---

## 🔧 Build Applications by Connecting Blocks

A *network* is a collection of **blocks** and **connections**. Each block:
- May have **input ports** and **output ports**
- Defines a `run()` function that sends and receives **messages**

A **connection** links the output port of one block to the input port of another:
[ block_A.output_port ] --> [ block_B.input_port ]


You build a distributed application by:
1. Selecting blocks from a library or defining blocks using Python
2. Connecting blocks to form a network
3. Running the network

---

## 🧩 Blocks Are Composable

- A network itself can be used as a block inside a larger network
- Blocks can be executed independently using `.run()`, or integrated into Python programs

---

## 📁 Explore Examples

- `dsl/examples/intro/` — Build basic networks by connecting generators, transformers, and recorders
- `dsl/examples/intro_to_agents/` — Create intelligent agents using OpenAI prompts or library functions (e.g. SciKit)
- `dsl/examples/networks_of_networks/` — Compose blocks that are themselves networks
- `dsl/examples/blocks_in_regular_Python/` — Use blocks as components inside regular Python code

👉 Each folder includes a `README.md` with example descriptions. These are designed to be run directly and modified easily — feel free to experiment!

---

## 🚀 Quick Start

Install locally in editable mode:

```bash
git clone https://github.com/kmchandy/DisSysLab.git
cd DisSysLab
pip install -e .
🔎 Learn More
📘 Browse the examples and README.md files in each folder

🔍 Use the upcoming natural language search to find blocks and examples by question

📬 DisSysLab is designed to help people learn distributed systems by building their own applications — collaboration and contributions are welcome!


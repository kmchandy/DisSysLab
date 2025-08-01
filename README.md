# 🕸️ DisSysLab: Agents Collaborate by Exchanging Messages

**DisSysLab** is a lightweight Python framework for building applications where **multiple agents collaborate by exchanging messages**.

It is designed for both:
- 🧑‍🎓 **Non-programmers** who want to explore distributed systems using pre-built components.
- 🧑‍💻 **Programmers** who want to write agent-based distributed applications in Python.

---

## 🎯 Goals

- ✅ **Accessibility**: Build distributed apps by connecting reusable blocks — no advanced coding needed.
- ✅ **Extensibility**: Use blocks like any other Python class in your code.
- ✅ **Modularity**: Compose blocks into larger networks, or embed them in existing programs.

---

## 🔧 Core Idea: Build Applications by Connecting Blocks

A **block** is an agent with:
- Input and/or output ports
- A `run()` or `handle_msg()` function
- A name and optional description

A **network** consists of blocks and connections. For example, here is a network consisting of three blocks: generator, transformer, and recorder.

[ generator ] → [ transformer ] → [ recorder ]


You build applications by:
1. 📦 Choosing or defining blocks  
2. 🔗 Connecting them into a network  
3. ▶️ Running the system

---

## 🧩 Blocks Are Composable

- **Parallel Composition**: A network can itself be used as a block in a larger network.
- **Sequential Composition**: You can call blocks from regular Python code like functions.

---

## 📁 Explore Examples

| Folder | What You'll Learn |
|--------|-------------------|
| [`intro_basic/`](dsl/examples/intro_basic) | Create simple networks with generators, transformers, and recorders |
| [`intro_to_agents/`](dsl/examples/intro_to_agents) | Build intelligent agents with GPT or SciKit functions |
| [`networks_of_networks/`](dsl/examples/networks_of_networks) | Compose blocks that are themselves networks |
| [`blocks_in_regular_Python/`](dsl/examples/blocks_in_regular_Python) | Use blocks in plain Python code for step-by-step tasks |

Each folder includes a `README.md` and runnable Python scripts.

---

## 🚀 Quick Start

```bash
git clone https://github.com/kmchandy/DisSysLab.git
cd DisSysLab
pip install -e .
```

---

## 🔍 Coming 

- 🔎 **Natural language search** to find blocks and examples 
- 📚 A growing **library of reusable agents and block patterns**  
- 🖼️ A **drag-and-drop UI** for visual network construction  

---

## 🤝 Contribute or Collaborate

**DisSysLab** is an educational project. You are welcome to:

- ✅ Try the examples  
- 💡 Suggest improvements  
- 🔧 Contribute your own agents or use cases  

> 📬 We want to make distributed systems understandable, and enjoyable, for everyone.


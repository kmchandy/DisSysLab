# 🕸️ DisSysLab: Agents Collaborate by Exchanging Messages

**DisSysLab** is a lightweight Python framework for building applications in which **multiple agents collaborate by exchanging messages**. It is designed for:

- 🧑‍🎓 **Non-programmers**: Build distributed applications by connecting pre-built components from sources such as OpenAI, Microsoft Copilot, NumPy, and Scikit-learn.  
- 🧑‍💻 **Programmers**: Build distributed applications in Python by connecting blocks.

## IMPORTANT NOTE
This framework is being developed. It changes almost daily. I hope to have a solid version by the end of the year. In the meantime, feel free to use it provided you realize that it is changing rapidly.

---


## 🔧 Core Idea 1: Build Applications by Connecting Blocks

A **block** is an object with:

- Input and/or output ports  
- A `run()` function  

A **network** consists of blocks and connections. For example, here is a network consisting of three blocks: generator, transformer, and recorder. The generator outputs messages that are received by the transformer. Messages output by the transformer are received by the recorder.



![Example Network Diagram](docs/images/simple_network.svg)

Blocks may have multiple inputs and outputs.

---

## 🔧 Core Idea 2: A Block Embodies a Function

A block is a shell that calls **functions** (or prompts) to generate, transform, or record messages. For example:

- A **generator** block may use an OpenAI connector to output financial news about specified companies.  
- A **transformer** block may use an LLM agent to output the positive or negative sentiment of the messages it receives.  
- A **recorder** block may use a Microsoft Copilot connector to put results into an Excel spreadsheet.

 ![Block Embodies a Function](docs/images/block_embodies_function.svg)

**You build a distributed application by specifying and connecting blocks.**

---

## 🧩 Blocks Are Composable

- **Parallel Composition**: Use a network as a block inside a larger network.  
- **Sequential Composition**: Call blocks from regular Python code just as you would call any function.

---

## ⚡ Quick Start

Follow these steps to try DisSysLab right away:

1. **Clone the repo** (copy the code to your computer): 
```
   git clone https://github.com/kmchandy/DisSysLab.git
   cd DisSysLab
```
📖 If you’ve never cloned a repo before, see [GitHub’s guide](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository).

2. **Make and activate a virtual environment:** 

```
python -m venv .venv
source .venv/bin/activate   # Mac/Linux
# .\.venv\Scripts\Activate.ps1   # Windows PowerShell
```

3. **Install DisSysLab:**
```
python -m pip install -e .
```

4. **Run an example:**

```
python examples/graph_simple_source_sink.py
```

5. **Interfaces: Extensions and Connections**
   - Extensions has functions provided by services such as OpenAI and Scikit that are called by **graph.py** to build apps.
   - Connections are interfaces to databases and applications such as Google Sheets. Not implemented.

---

## 🚦 This Website

A quick way to start is to run/modify the examples in the README.md files in the following chapters.

- **Build your first distributed app immediately** [Chapter 0](dsl/examples/ch00_drafts/README.md)
- **Build a network by specifying and connecting blocks.** [Chapter 1](dsl/examples/ch01_networks/README.md)
- **Messages.** [Chapter 2](dsl/examples/ch02_keys/README.md)
- **Network Structures.** [Chapter 3](dsl/examples/ch03_fanin_fanout/README.md)
- **GPT blocks.** [Chapter 4](dsl/examples/ch04_GPT/README.md)
- **Data Science Blocks** [Chapter 5](dsl/examples/ch05_ds/README.md)
- **Connectors to External Applications** [Chapter 6](dsl/examples/ch06_git/README.md)

## 🚀 Install Instructions

Just follow these steps — you can copy & paste the commands.

💡 On some systems, you may need to use python3 instead of python in the commands below.

### 1. Make a virtual environment (one-time setup)

Open a terminal in the **DisSysLab** folder, then run:

```
python -m venv .venv
```

### 2. Activate the environment

Every time you want to use DisSysLab, activate the environment first:

Mac/Linux users run this line:
```
source .venv/bin/activate
```
Windows PowerShell users run this line:
```
.\.venv\Scripts\Activate.ps1
```

You’ll know it worked if your prompt shows (.venv) at the front.

### 3. Install DisSysLab

For most chapters and applications, the basic install is enough:
```
python -m pip install -e .
```

### 4. Extra installs for special chapters

Some applications described in later chapters need extra libraries. Add them in square brackets with quotes:

#### Chapter 4 (Large Language Model Interfaces)
```
pip install -e .[llm]
```

#### Chapter 5 (Data Science / ML)
You may need to use python3 rather than python depending on your python installation.
```
pip install -e .[ml]
```


#### Chapter 6 (Connectors to Google Sheets, etc.)
```
python -m pip install -e '.[sheets]'
```
#### GitHub connector examples
```
python -m pip install -e '.[github]'
```
You can also combine installation packages, for example:
```
python -m pip install -e '.[ml,sheets]'
```
### 5. Developer setup (for running tests)

If you want to run the tests (e.g. pytest), install with the dev tools:
```
python -m pip install -e '.[dev]'
```
### 6. Check that it worked

Run this quick test:
```
python - << 'PY'
import dsl
print("DisSysLab imported from:", dsl.__file__)
PY
```
You should see a path pointing to your DisSysLab/dsl/ folder. 🎉

## Using Makefile
📖 *“See [Makefile Guide](README_Makefile.md) .”*
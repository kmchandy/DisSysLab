# 🕸️ DisSysLab: Agents Collaborate by Exchanging Messages

**DisSysLab** is a lightweight Python framework for building applications in which **multiple agents collaborate by exchanging messages**. It is designed for:

- 🧑‍🎓 **Non-programmers**: Build distributed applications by connecting pre-built components from sources such as OpenAI, Microsoft Copilot, NumPy, and Scikit-learn.  
- 🧑‍💻 **Programmers**: Build distributed applications in Python by connecting blocks. Use a block like any other Python class. Connect blocks to form larger blocks or embed blocks in programs.

---

## 🔧 Core Idea 1: Build Applications by Connecting Blocks

A **block** is an object with:

- Input and/or output ports  
- A `run()` function  

A **network** consists of blocks and connections. For example, here is a network consisting of three blocks: generator, transformer, and recorder. The generator outputs messages that are received by the transformer. Messages output by the transformer are received by the recorder.

[ generator ] → [ transformer ] → [ recorder ]


![Example Network Diagram](docs/images/simple_network.png)

Blocks may have multiple inputs and outputs.

---

## 🔧 Core Idea 2: A Block Embodies a Function

A block is a shell that calls **functions** (or prompts) to generate, transform, or record messages. For example:

- A **generator** block may use an OpenAI connector to output financial news about specified companies.  
- A **transformer** block may use an LLM agent to output the positive or negative sentiment of the messages it receives.  
- A **recorder** block may use a Microsoft Copilot connector to put results into an Excel spreadsheet.

You build a distributed application by:

1. 📦 **Specifying blocks** by the functions they embody  
2. 🔗 **Connecting blocks** into a network  

---

## 🧩 Blocks Are Composable

- **Parallel Composition**: Use a network as a block inside a larger network.  
- **Sequential Composition**: Call blocks from regular Python code just as you would call any function.

---

## 🚦 Choose Your Starting Path

DisSysLab supports three **onboarding tracks** depending on your goals and setup.

| Track | Who It’s For | How You’ll Learn |
|-------|--------------|------------------|
| **Track A — Colab Wizard** | Non-programmers who want zero setup and instant results | An interactive wizard in Google Colab that runs in your browser |
| **Track B — Local Install Wizard** | Non-programmers who want to run DisSysLab on their own computer and save apps | A conversational step-by-step wizard in your terminal; save and reuse apps locally |
| **Track C — Programmers** | Python users who want full code control | A set of short lessons (`dsl/examples`) with runnable code and diagrams |

---

### 🌐 Track A: Colab Wizard

1. **[Open the Colab link](INSERT-COLAB-LINK-HERE)**  
2. Follow the guided steps to build and run an app entirely in your browser.  
3. Download your app definition if you want to reuse it later.

---

### 🛠 Track B: Local Install Wizard

1. Install DisSysLab locally:  
   ```bash
   git clone https://github.com/kmchandy/DisSysLab.git
   cd DisSysLab
   pip install -e .
   ```
Run the wizard:
```
python -m dsl.user_interaction.local_wizard
```
Follow the prompts to build your first app, save it, and re-run it any time.

### 📚 Track C: For Programmers
Install with examples:
```
pip install dissyslab[examples]
```
Explore the lessons inside dsl/examples/:

Each lesson has a README.md focused on a single concept and includes a short explanation and runnable Python examples

### 🔍 Coming Later
🖼️ A drag-and-drop UI for visual network construction

### 🤝 Collaborate
📬 We want to make distributed systems understandable — and enjoyable — for everyone.
DisSysLab is an educational project. Collaboration is welcome.
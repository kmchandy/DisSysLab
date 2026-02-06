# 🛠️ Using the Makefile in DisSysLab

This guide shows you how to use the **Makefile** that comes with DisSysLab.  
It’s designed for **beginners** — so you don’t need to remember long commands.  

---

## 📦 What is a Makefile?

A **Makefile** is like a shortcut menu for the terminal.  
Instead of typing long Python commands, you can type short ones like:

```
make dev
make test
```

The Makefile will run the right steps for you.

## 🚀 Common Commands
### 1. Set up the project

Creates a virtual environment and installs DisSysLab in editable mode:
```
make dev
```
After this, you can run examples (e.g. Chapter 1):
```
python dsl/examples/ch01_networks/simple_pipeline.py
```

### 2. Developer setup (with test tools)

If you want to run the test suite, use:
```
make dev-extras
```

This installs DisSysLab plus developer tools (like pytest).

### 3. Run all tests

Check that everything is working:
```
make test
```

### 4. Run a single test file

Sometimes you only want to run one test (for faster feedback):
```
make test-one FILE=dsl/tests/test_intro.py
```

### 5. Clean up

If you want to remove the virtual environment and build files:
```
make clean
```

## 💡 Notes

On Mac/Linux, *make* is already installed.

On Windows, you may need to install *GNU Make for Windows*
, or run the commands shown inside the Makefile manually.

If you’re ever unsure, open the Makefile in a text editor — it’s just a list of commands.
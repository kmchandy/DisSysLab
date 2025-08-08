"""
interaction.py — Prototype for AL Assistant Core Logic

This module implements the core functionality of the AL (Agent for Learning) assistant.
It allows users to interactively design a single distributed system network composed
of predefined block types (generator, transform, record, fan-in, fan-out) and functions.

Features:
- Create, specify, and describe blocks
- Connect blocks with awareness of multi-port configurations
- List blocks and their connections
- Provide available function options for each block type
- Summarize the current network state
- Export/Load YAML and validate the network
- (Optional) Export the designed network to executable Python code

Intended for use as a prototype CLI to validate interaction logic before
integrating with an OpenAI-powered conversational interface.
"""

from __future__ import annotations
import ast

from dsl.user_interaction.export_to_yaml import (
    export_to_yaml,
    load_from_yaml,
    validate_network,
    # fill_missing_ports,  # available if you want to auto-fill ports on load
)

# Enable "export python" in the REPL
from dsl.user_interaction.export_to_python import export_to_python


network = {
    "blocks": {},
    "connections": []
}

current_block = None


# --- Core Actions ---

def create_block(name, block_type):
    if name in network["blocks"]:
        return f"Block '{name}' already exists."
    # Default ports based on block type
    inports = []
    outports = []
    if block_type == "generator":
        outports = ["out"]
    elif block_type == "transform":
        inports = ["in"]
        outports = ["out"]
    elif block_type == "record":
        inports = ["in"]
    elif block_type == "fan-in":
        inports = ["in1", "in2"]
        outports = ["out"]
    elif block_type == "fan-out":
        inports = ["in"]
        outports = ["out1", "out2"]

    network["blocks"][name] = {
        "type": block_type,
        "function": None,
        "parameters": {},
        "inports": inports,
        "outports": outports
    }
    return f"✅ Created block '{name}' of type '{block_type}'."


def set_block_function(name, function, parameters):
    if name not in network["blocks"]:
        return f"❌ Block '{name}' does not exist."
    network["blocks"][name]["function"] = function
    network["blocks"][name]["parameters"] = parameters
    return f"🔧 Set function '{function}' on block '{name}'."


def connect_blocks(from_block, to_block, from_port=None, to_port=None):
    if from_block not in network["blocks"] or to_block not in network["blocks"]:
        return "❌ One or both blocks do not exist."
    from_ports = network["blocks"][from_block].get("outports", [])
    to_ports = network["blocks"][to_block].get("inports", [])
    from_port = from_port or (from_ports[0] if len(from_ports) == 1 else None)
    to_port = to_port or (to_ports[0] if len(to_ports) == 1 else None)

    if from_port is None or to_port is None:
        return (f"❌ Specify ports explicitly. '{from_block}' has outports {from_ports}, "
                f"'{to_block}' has inports {to_ports}.")

    connection = {"from": from_block, "from_port": from_port,
                  "to": to_block, "to_port": to_port}
    network["connections"].append(connection)
    return f"🔗 Connected '{from_block}.{from_port}' to '{to_block}.{to_port}'."


def specify_block(name):
    global current_block
    if name not in network["blocks"]:
        return f"❌ Block '{name}' not found."
    current_block = name
    return f"✏️ Now specifying block '{name}'."


def describe_block(name):
    if name not in network["blocks"]:
        return f"❌ Block '{name}' not found."
    block = network["blocks"][name]
    return (
        f"📦 Block '{name}':\n"
        f"  Type: {block['type']}\n"
        f"  Function: {block['function']}\n"
        f"  Parameters: {block['parameters']}\n"
        f"  Inports: {block.get('inports', [])}\n"
        f"  Outports: {block.get('outports', [])}"
    )


def list_blocks():
    if not network["blocks"]:
        return "(No blocks defined yet.)"
    return "🧱 Blocks:\n" + "\n".join(
        f"- {name} ({block['type']})" for name, block in network["blocks"].items()
    )


def summarize_network():
    summary = list_blocks() + "\n\n🔗 Connections:\n"
    if not network["connections"]:
        summary += "(No connections yet.)"
    else:
        summary += "\n".join(
            f"- {c['from']}.{c['from_port']} → {c['to']}.{c['to_port']}" for c in network["connections"]
        )
    return summary


def list_connections_for_block(name):
    if name not in network["blocks"]:
        return f"❌ Block '{name}' not found."
    incoming = [c for c in network["connections"] if c["to"] == name]
    outgoing = [c for c in network["connections"] if c["from"] == name]
    result = f"🔗 Connections for block '{name}':\n"
    result += "  Incoming:\n" + ("    (none)\n" if not incoming else "\n".join(
        f"    {c['from']}.{c['from_port']} → {c['to']}.{c['to_port']}" for c in incoming)) + "\n"
    result += "  Outgoing:\n" + ("    (none)" if not outgoing else "\n".join(
        f"    {c['from']}.{c['from_port']} → {c['to']}.{c['to_port']}" for c in outgoing))
    return result


def get_options(block_type):
    options = {
        "generate": ["GenerateFromList", "GenerateFromFile"],
        "transform": ["GPT_Prompt"],
        "record": ["RecordToFile", "RecordToList"],
        "fan-in": ["MergeAsynch", "MergeSynch"],
        "fan-out": ["Broadcast"]
    }
    return options.get(block_type, [])


def main():
    """Run the AL Prototype REPL (Read–Eval–Print Loop) for interactive network design."""
    print("👋 Welcome to AL Prototype. Type 'help' to see available commands. Type 'exit' to quit.")
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Exiting...")
            break

        if not user_input:
            continue
        elif user_input == "exit":
            break
        elif user_input == "demo sentiment":
            from dsl.examples.demo_sentiment import demo_sentiment
            demo_sentiment(create_block, set_block_function,
                           connect_blocks, summarize_network)
        elif user_input.startswith("create "):
            _, name, type_ = user_input.split()
            print(create_block(name, type_))
        elif user_input.startswith("set "):
            parts = user_input.split(maxsplit=3)
            try:
                parameters = ast.literal_eval(
                    parts[3]) if len(parts) > 3 else {}
            except (ValueError, SyntaxError):
                print("❌ Invalid parameter format.")
                continue
            name, func = parts[1], parts[2]
            print(set_block_function(name, func, parameters))
        elif user_input.startswith("connect "):
            parts = user_input.split()
            if len(parts) == 3:
                _, a, b = parts
                print(connect_blocks(a, b))
            elif len(parts) == 5:
                _, a, from_port, b, to_port = parts
                print(connect_blocks(a, b, from_port, to_port))
            else:
                print(
                    "❌ Usage: connect <from> <to> OR connect <from> <from_port> <to> <to_port>")
        elif user_input.startswith("specify "):
            _, name = user_input.split()
            print(specify_block(name))
        elif user_input.startswith("describe "):
            _, name = user_input.split()
            print(describe_block(name))
        elif user_input == "list":
            print(list_blocks())
        elif user_input == "summary":
            print(summarize_network())
        elif user_input.startswith("connections "):
            _, name = user_input.split()
            print(list_connections_for_block(name))
        elif user_input.startswith("options "):
            _, type_ = user_input.split()
            print(f"Options for {type_}: {get_options(type_)}")
        elif user_input == "export yaml":
            print(export_to_yaml(network))
        elif user_input.startswith("load yaml "):
            _, _, path = user_input.partition("load yaml ")
            loaded = load_from_yaml(file_path=path.strip())
            errs = validate_network(loaded)
            if errs:
                print("❌ Validation issues in file:")
                for e in errs:
                    print(" -", e)
            else:
                network.clear()
                network.update(loaded)
                print("✅ YAML loaded into current session.")
        elif user_input == "validate":
            errs = validate_network(network)
            if errs:
                print("❌ Validation issues:")
                for e in errs:
                    print(" -", e)
            else:
                print("✅ Network is valid.")
        elif user_input == "export python":
            print(export_to_python())
        elif user_input == "help":
            print("""Available commands:
  create <name> <type>         - Create a block of the given type (generate, transform, record, fan-in, fan-out).
  set <name> <func> [params]   - Set the function and parameters for a block. Example:
                                   set gen GenerateFromList {"values": ["hello"]}
  connect <from> <to>          - Connect two blocks (uses default ports if one each).
  connect <from> <from_port> <to> <to_port> - Connect specifying ports explicitly.
  specify <name>               - Focus on a block for editing.
  describe <name>              - Show details of a block, including type, function, parameters, and ports.
  list                         - List all blocks currently defined.
  summary                      - Show all blocks and all connections in the network.
  connections <name>           - Show all incoming and outgoing connections for a block.
  options <type>               - List available functions for a given block type.
  export yaml                  - Export the current network to YAML.
  load yaml <path>             - Load a network from a YAML file.
  validate                     - Validate the network structure.
  export python                - Export the network to equivalent Python code.
  demo sentiment               - Run the sentiment pipeline demo.
  help                         - Show this help message.
  exit                         - Exit the program.

Tip: You can press Enter on a blank line to skip without running a command.""")
        else:
            print(
                "🤖 Sorry, I didn’t understand that command. Type 'help' for a list of commands.")


if __name__ == "__main__":
    main()

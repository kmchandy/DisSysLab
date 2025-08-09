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
from typing import Optional
from dsl.user_interaction.io import BaseIO, CLIIO

from dsl.user_interaction.export_to_yaml import (
    export_to_yaml,
    load_from_yaml,
    validate_network,
)

# Enable "export python" in the REPL
from dsl.user_interaction.export_to_python import export_to_python

# ----------------------
# Global network state
# ----------------------
network = {
    "blocks": {},
    "connections": []
}

current_block = None

# Valid block types (guard against typos)
VALID_TYPES = {"generator", "transform", "record", "fan-in", "fan-out"}

# ----------------------
# Helpers & validation
# ----------------------


def get_options(block_type):
    """Return allowed function options for a given block type."""
    options = {
        "generate": ["GenerateFromList", "GenerateFromFile", "GenerateFromConnector"],
        "transform": ["GPT_Prompt"],
        "record": ["RecordToFile", "RecordToList", "RecordToConnector"],
        "fan-in": ["MergeAsynch", "MergeSynch"],
        "fan-out": ["Broadcast"],
    }
    return options.get(block_type, [])


def _validate_params_for_function(block_type, function, parameters):
    """
    Return None if OK, else a human-friendly error string.
    - For *Connector functions*, only check shape: provider/tool_id/operation/args.
    - No credential/schema validation here.
    """
    if function in ("GenerateFromConnector", "RecordToConnector"):
        required = {"provider", "tool_id", "operation", "args"}
        if not isinstance(parameters, dict):
            return "Parameters must be a dict for connector functions."
        missing = sorted(required - set(parameters.keys()))
        if missing:
            return (
                f"Missing required parameter(s) for {function}: {missing}. "
                "Expected keys: {'provider','tool_id','operation','args'}"
            )
        if not isinstance(parameters.get("args"), dict):
            return "Parameter 'args' must be a dict (key/value map for connector operation)."
        provider = parameters.get("provider")
        if not isinstance(provider, str) or not provider:
            return "Parameter 'provider' must be a non-empty string."
    return None


# ----------------------
# Core actions
# ----------------------

def create_block(name, block_type):
    if name in network["blocks"]:
        return f"Block '{name}' already exists."
    if block_type not in VALID_TYPES:
        return f"❌ Invalid block type '{block_type}'. Choose from: {sorted(VALID_TYPES)}"

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
        "outports": outports,
    }
    return f"✅ Created block '{name}' of type '{block_type}'."


def set_block_function(name, function, parameters):
    """Assign a function and parameters to a block, with connector-specific validation."""
    if name not in network["blocks"]:
        return f"❌ Block '{name}' does not exist."

    btype = network["blocks"][name]["type"]
    allowed = get_options(btype)

    if function not in allowed:
        return (
            f"❌ Function '{function}' is not allowed for block type '{btype}'."
            f"   Try one of: {allowed}"
            f"   Tip: type `options {btype}` to list choices."
        )

    # Parameter shape checks (esp. connectors)
    err = _validate_params_for_function(btype, function, parameters or {})
    if err:
        example = ""
        if function == "GenerateFromConnector":
            example = (
                "Example:"
                "   set gen GenerateFromConnector "
                "{'provider':'mock','tool_id':'yahoo.finance.news','operation':'list_headlines',"
                "'args':{'tickers':['AAPL','MSFT'],'limit':5}}"
            )
        elif function == "RecordToConnector":
            example = (
                "Example:"
                "   set rec RecordToConnector "
                "{'provider':'copilot_connector','tool_id':'microsoft.excel','operation':'append_rows',"
                "'args':{'workbook_id':'...','sheet':'Sentiment','range':'A1'}}"
            )
        return f"❌ {err}{example}"

    network["blocks"][name]["function"] = function
    network["blocks"][name]["parameters"] = parameters or {}
    return f"🔧 Set function '{function}' on block '{name}'."


def connect_blocks(from_block, to_block, from_port=None, to_port=None):
    if from_block not in network["blocks"] or to_block not in network["blocks"]:
        return "❌ One or both blocks do not exist."
    from_ports = network["blocks"][from_block].get("outports", [])
    to_ports = network["blocks"][to_block].get("inports", [])
    from_port = from_port or (from_ports[0] if len(from_ports) == 1 else None)
    to_port = to_port or (to_ports[0] if len(to_ports) == 1 else None)

    if from_port is None or to_port is None:
        return (
            f"❌ Specify ports explicitly. '{from_block}' has outports {from_ports}, "
            f"'{to_block}' has inports {to_ports}."
        )

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
        f"📦 Block '{name}':"
        f"  Type: {block['type']}"
        f"  Function: {block['function']}"
        f"  Parameters: {block['parameters']}"
        f"  Inports: {block.get('inports', [])}"
        f"  Outports: {block.get('outports', [])}"
    )


def list_blocks():
    if not network["blocks"]:
        return "(No blocks defined yet.)"
    return "🧱 Blocks: " + " ".join(
        f"- {name} ({block['type']})" for name, block in network["blocks"].items()
    )


def summarize_network():
    summary = list_blocks() + "🔗 Connections:"
    if not network["connections"]:
        summary += "(No connections yet.)"
    else:
        summary += "".join(
            f"- {c['from']}.{c['from_port']} → {c['to']}.{c['to_port']}" for c in network["connections"]
        )
    return summary


def list_connections_for_block(name):
    if name not in network["blocks"]:
        return f"❌ Block '{name}' not found."
    incoming = [c for c in network["connections"] if c["to"] == name]
    outgoing = [c for c in network["connections"] if c["from"] == name]
    result = f"🔗 Connections for block '{name}':"
    result += "  Incoming:" + ("    (none)" if not incoming else "".join(
        f"    {c['from']}.{c['from_port']} → {c['to']}.{c['to_port']}" for c in incoming)) + ""
    result += "  Outgoing:" + ("    (none)" if not outgoing else "".join(
        f"    {c['from']}.{c['from_port']} → {c['to']}.{c['to_port']}" for c in outgoing))
    return result


# ----------------------
# REPL
# ----------------------

def run_session(io: BaseIO) -> None:
    """Run the AL Prototype session using the provided IO adapter."""
    io.write(
        "👋 Welcome to AL Prototype. Type 'help' to see available commands. Type 'exit' to quit.")
    while True:
        try:
            user_input = io.read("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            io.write("\n👋 Exiting...")
            break

        if not user_input:
            continue
        elif user_input == "exit":
            break
        elif user_input == "demo sentiment":
            # Lazy import to avoid circulars and optional dependency load
            from dsl.examples.demo_sentiment import demo_sentiment
            demo_sentiment(create_block, set_block_function,
                           connect_blocks, summarize_network)

        elif user_input.startswith("create "):
            _, name, type_ = user_input.split()
            io.write(create_block(name, type_))

        elif user_input.startswith("set "):
            parts = user_input.split(maxsplit=3)
            try:
                parameters = ast.literal_eval(
                    parts[3]) if len(parts) > 3 else {}
            except (ValueError, SyntaxError):
                io.write("❌ Invalid parameter format.")
                continue
            name, func = parts[1], parts[2]
            io.write(set_block_function(name, func, parameters))

        elif user_input.startswith("connect "):
            parts = user_input.split()
            if len(parts) == 3:
                _, a, b = parts
                io.write(connect_blocks(a, b))
            elif len(parts) == 5:
                _, a, from_port, b, to_port = parts
                io.write(connect_blocks(a, b, from_port, to_port))
            else:
                io.write(
                    "❌ Usage: connect <from> <to> OR connect <from> <from_port> <to> <to_port>")

        elif user_input.startswith("specify "):
            _, name = user_input.split()
            io.write(specify_block(name))

        elif user_input.startswith("describe "):
            _, name = user_input.split()
            io.write(describe_block(name))

        elif user_input == "list":
            io.write(list_blocks())

        elif user_input == "summary":
            io.write(summarize_network())

        elif user_input.startswith("connections "):
            _, name = user_input.split()
            io.write(list_connections_for_block(name))

        elif user_input.startswith("options "):
            _, type_ = user_input.split()
            io.write(f"Options for {type_}: {get_options(type_)}")

        elif user_input == "export yaml":
            io.write(export_to_yaml(network))

        elif user_input.startswith("load yaml "):
            _, _, path = user_input.partition("load yaml ")
            loaded = load_from_yaml(file_path=path.strip())
            errs = validate_network(loaded)
            if errs:
                io.write("❌ Validation issues in file:")
                for e in errs:
                    io.write(f" - {e}")
            else:
                network.clear()
                network.update(loaded)
                io.write("✅ YAML loaded into current session.")

        elif user_input == "validate":
            errs = validate_network(network)
            if errs:
                io.write("❌ Validation issues:")
                for e in errs:
                    io.write(f" - {e}")
            else:
                io.write("✅ Network is valid.")

        elif user_input == "export python":
            io.write(export_to_python())

        elif user_input == "help":
            io.write("""Available commands:
  create <name> <type>         - Create a block of the given type (generate, transform, record, fan-in, fan-out).
  set <name> <func> [params]   - Set the function and parameters for a block. Examples:
                                   set gen GenerateFromList {"values": ["hello"]}
                                   set gen GenerateFromConnector {'provider':'mock','tool_id':'yahoo.finance.news','operation':'list_headlines','args':{'tickers':['AAPL','MSFT'],'limit':5}}
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
            io.write(
                "🤖 Sorry, I didn’t understand that command. Type 'help' for a list of commands.")


def start_wizard(io: Optional[BaseIO] = None) -> None:
    """Start the session with the provided IO (defaults to CLI)."""
    run_session(io or CLIIO())


if __name__ == "__main__":
    start_wizard()

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
- Export the designed network to executable Python code

Intended for use as a prototype CLI to validate interaction logic before
integrating with an OpenAI-powered conversational interface.
"""

network = {
    "blocks": {},
    "connections": []
}

current_block = None

# --- Core Actions ---


def create_block(name, block_type):
    if name in network["blocks"]:
        return f"Block '{name}' already exists."
    inports, outports = [], []
    if block_type == "generator":
        outports = ["out"]
    elif block_type == "transform":
        inports, outports = ["in"], ["out"]
    elif block_type == "record":
        inports = ["in"]
    elif block_type == "fan-in":
        inports, outports = ["in1", "in2"], ["out"]
    elif block_type == "fan-out":
        inports, outports = ["in"], ["out1", "out2"]
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
        return f"❌ Specify ports explicitly. '{from_block}' has outports {from_ports}, '{to_block}' has inports {to_ports}."
    network["connections"].append(
        {"from": from_block, "from_port": from_port, "to": to_block, "to_port": to_port})
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
    b = network["blocks"][name]
    return (f"📦 Block '{name}':\n"
            f"  Type: {b['type']}\n"
            f"  Function: {b['function']}\n"
            f"  Parameters: {b['parameters']}\n"
            f"  Inports: {b.get('inports', [])}\n"
            f"  Outports: {b.get('outports', [])}")


def list_blocks():
    return "(No blocks defined yet.)" if not network["blocks"] else "🧱 Blocks:\n" + "\n".join(f"- {n} ({b['type']})" for n, b in network["blocks"].items())


def summarize_network():
    s = list_blocks() + "\n\n🔗 Connections:\n"
    if not network["connections"]:
        s += "(No connections yet.)"
    else:
        s += "\n".join(f"- {c['from']}.{c['from_port']} → {c['to']}.{c['to_port']}" for c in network["connections"])
    return s


def list_connections_for_block(name):
    if name not in network["blocks"]:
        return f"❌ Block '{name}' not found."
    inc = [c for c in network["connections"] if c["to"] == name]
    out = [c for c in network["connections"] if c["from"] == name]
    r = f"🔗 Connections for block '{name}':\n"
    r += "  Incoming:\n" + ("    (none)\n" if not inc else "\n".join(
        f"    {c['from']}.{c['from_port']} → {c['to']}.{c['to_port']}" for c in inc)) + "\n"
    r += "  Outgoing:\n" + ("    (none)" if not out else "\n".join(
        f"    {c['from']}.{c['from_port']} → {c['to']}.{c['to_port']}" for c in out))
    return r


def get_options(block_type):
    return {
        "generate": ["GenerateFromList", "GenerateFromFile"],
        "transform": ["GPT_Prompt"],
        "record": ["RecordToFile", "RecordToList"],
        "fan-in": ["MergeAsynch", "MergeSynch"],
        "fan-out": ["Broadcast"]
    }.get(block_type, [])

# --- Export Functions ---


def export_to_python():
    """Generate Python code for the current network."""
    blocks_code = []
    for name, b in network["blocks"].items():
        params_str = ", ".join(f"{k}={repr(v)}" for k,
                               v in b["parameters"].items())
        blocks_code.append(f"    '{name}': {b['function']}({params_str})")
    blocks_str = "\n".join(blocks_code)
    conns_str = ",\n        ".join(
        f"('{c['from']}', '{c['from_port']}', '{c['to']}', '{c['to_port']}')" for c in network["connections"])
    return ("from dsl.core import Network\n\n"
            "net = Network(\n"
            f"    blocks={{\n{blocks_str}\n    }},\n"
            f"    connections=[\n        {conns_str}\n    ]\n)\n")

# --- Example REPL Loop ---


def main():
    print("👋 Welcome to AL Prototype. Type 'exit' to quit.")
    while True:
        ui = input("You: ").strip()
        if ui == "exit":
            break
        elif ui.startswith("create "):
            _, n, t = ui.split()
            print(create_block(n, t))
        elif ui.startswith("set "):
            p = ui.split(maxsplit=3)
            n, f = p[1], p[2]
            params = eval(p[3]) if len(p) > 3 else {}
            print(set_block_function(n, f, params))
        elif ui.startswith("connect "):
            parts = ui.split()
            if len(parts) == 3:
                _, a, b = parts
                print(connect_blocks(a, b))
            elif len(parts) == 5:
                _, a, fp, b, tp = parts
                print(connect_blocks(a, b, fp, tp))
            else:
                print(
                    "❌ Usage: connect <from> <to> OR connect <from> <from_port> <to> <to_port>")
        elif ui.startswith("specify "):
            _, n = ui.split()
            print(specify_block(n))
        elif ui.startswith("describe "):
            _, n = ui.split()
            print(describe_block(n))
        elif ui == "list":
            print(list_blocks())
        elif ui == "summary":
            print(summarize_network())
        elif ui.startswith("connections "):
            _, n = ui.split()
            print(list_connections_for_block(n))
        elif ui.startswith("options "):
            _, t = ui.split()
            print(f"Options for {t}: {get_options(t)}")
        elif ui == "export python":
            print(export_to_python())
        else:
            print("🤖 Sorry, I didn’t understand that command.")


if __name__ == "__main__":
    main()

from __future__ import annotations
from typing import Dict, List, Tuple
from .lessons import NetworkSpec, Lesson, CodeBundle


def ascii_diagram(topology: str) -> str:
    if topology == "pipeline":
        return "[ Generator ] → [ Transformer ] → [ Recorder ]"
    if topology == "fanin":
        return "[Gen A] →\n           [ Fan-in ] → [ Transformer ] → [ Recorder ]\n[Gen B] →"
    if topology == "fanout":
        return "[ Generator ] → [ Transformer ] → [ Fan-out ] → [ Rec A ]\n                                          ↘︎ [ Rec B ]"
    return topology


def render_preview(spec: NetworkSpec) -> str:
    lines = []
    lines.append("📦 Blocks:")
    for name, cls in spec.blocks.items():
        lines.append(f"  - {name}: {cls}")
    lines.append("🔗 Connections:")
    for (s, sp, d, dp) in spec.connections:
        lines.append(f"  - ({s}:{sp}) → ({d}:{dp})")
    return "\n".join(lines)


def render_code(bundle: CodeBundle) -> str:
    # Fenced code block for clarity
    return f"```python\n{bundle.code}```\n"


def render_explanation_for(topology: str) -> str:
    if topology == "pipeline":
        return (
            "- **Blocks** do the work (generate, transform, record).\n"
            "- **Connections** move messages from outports to inports.\n"
            "- Apps can stream continuously until you press Ctrl+C."
        )
    if topology == "fanin":
        return (
            "- **Fan-in** combines multiple streams; inputs are numbered (`in0`, `in1`).\n"
            "- A transformer can then operate on the combined message."
        )
    if topology == "fanout":
        return (
            "- **Fan-out** splits a stream into multiple outputs; outputs are numbered (`out0`, `out1`).\n"
            "- You can send results to different destinations (console, file, etc.)."
        )
    return ""


def show_code_reveal(lesson: Lesson, spec: NetworkSpec, bundle: CodeBundle) -> str:
    parts = []
    parts.append(f"# 🧩 {lesson.title}\n")
    parts.append(f"**Diagram:** `{ascii_diagram(lesson.topology)}`\n")
    parts.append(render_preview(spec))
    parts.append("\n**Code:**\n")
    parts.append(render_code(bundle))
    parts.append("**What to notice:**\n")
    parts.append(render_explanation_for(lesson.topology))
    return "\n".join(parts)

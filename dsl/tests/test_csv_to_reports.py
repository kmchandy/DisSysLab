from __future__ import annotations
from typing import Any, Dict, List
import csv
import pathlib

from dsl.core import Network
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.block_lib.stream_transformers import TransformerFunction
from dsl.connector_lib.inputs.csv import InputConnectorCSV
from dsl.connector_lib.outputs.file_md import OutputConnectorFileMarkdown
from dsl.connector_lib.outputs.csv import OutputConnectorCSV
from dsl.connector_lib.orchestrators.buffered import BufferedOrchestrator


def _write_example_csv(path: pathlib.Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "title", "type"])
        w.writerow([101, "Crash on startup", "bug"])
        w.writerow([102, "Add dark mode", "feature"])
        w.writerow([103, "Typo in README", "docs"])


def test_csv_to_reports():
    # --- fixed paths inside repo tree
    base = pathlib.Path("dsl/examples/connectors")
    src = base / "data" / "tickets.csv"
    out_md = base / "reports" / "tickets.md"
    out_csv = base / "reports" / "tickets_clean.csv"

    _write_example_csv(src)

    # --- tiny transformers
    def to_row(msg: Dict[str, Any]) -> Dict[str, str]:
        d = msg["data"]
        label = "bug" if str(d.get("type", "")).lower() == "bug" else "other"
        return {"row": f"- [{label}] {d.get('title', '(untitled)')}"}

    def to_clean_dict(msg: Dict[str, Any]) -> Dict[str, Any]:
        d = msg["data"]
        return {"id": d.get("id"), "title": d.get("title"), "type": d.get("type")}

    # --- orchestrators
    def md_meta(buf): return {"path": str(out_md), "title": "Ticket Summary"}

    def csv_meta(buf): return {
        "path": str(out_csv),
        "fieldnames": ["id", "title", "type"],
        "include_header": True,
        "mode": "w",
    }

    orch_md = BufferedOrchestrator(meta_builder=md_meta)
    orch_csv = BufferedOrchestrator(meta_builder=csv_meta)

    # --- network
    net = Network(
        blocks={
            "pull": GenerateFromList(items=[{"cmd": "pull", "args": {"path": str(src)}}], delay=0.01),
            "tick_md": GenerateFromList(items=[{"cmd": "flush"}], delay=0.05),
            "tick_csv": GenerateFromList(items=[{"cmd": "flush"}], delay=0.06),
            "in": InputConnectorCSV(),
            "row": TransformerFunction(func=to_row),
            "clean": TransformerFunction(func=to_clean_dict),
            "orch_md": orch_md,
            "orch_csv": orch_csv,
            "out_md": OutputConnectorFileMarkdown(),
            "out_csv": OutputConnectorCSV(),
        },
        connections=[
            ("pull", "out", "in", "in"),
            ("in", "out", "row", "in"),
            ("row", "out", "orch_md", "data_in"),
            ("tick_md", "out", "orch_md", "tick_in"),
            ("orch_md", "out", "out_md", "in"),
            ("in", "out", "clean", "in"),
            ("clean", "out", "orch_csv", "data_in"),
            ("tick_csv", "out", "orch_csv", "tick_in"),
            ("orch_csv", "out", "out_csv", "in"),
        ],
    )

    # --- act
    net.compile_and_run()

    # --- assert Markdown
    assert out_md.exists(), "Markdown report was not created"
    md_text = out_md.read_text(encoding="utf-8")
    assert "# Ticket Summary" in md_text
    assert "- [bug] Crash on startup" in md_text
    assert "- [other] Add dark mode" in md_text

    # --- assert CSV
    assert out_csv.exists(), "Clean CSV was not created"
    with out_csv.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["id", "title", "type"]
    assert ["101", "Crash on startup", "bug"] in rows
    assert ["102", "Add dark mode", "feature"] in rows
    assert ["103", "Typo in README", "docs"] in rows

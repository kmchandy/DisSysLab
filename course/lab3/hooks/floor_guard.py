"""A Claude Code PreToolUse hook: refuse any sale booked below the floor.

Claude Code runs this before every Edit Sal makes (settings/dealer-hook.json).
It gets the tool call as JSON on stdin. If the file is a sale in sales/ and
its price is below the car's floor in inventory.json, it prints a "deny",
and Claude Code does not make the edit. Otherwise it prints nothing, and
the permission rules decide as usual. Sal never sees inventory.json.
"""
import json
import os
import sys
from pathlib import Path

FLOORS = Path(__file__).resolve().parents[1] / "inventory.json"


def problem(sale):
    """Why this sale must not be booked, or None."""
    car = json.loads(FLOORS.read_text())
    if sale.get("vehicle") not in car:
        return "there is no such vehicle on the lot"
    if not isinstance(sale.get("price"), (int, float)):
        return "the price is not a number"
    if sale["price"] < car[sale["vehicle"]]["floor"]:
        return "the price is below what the dealership accepts for this car"
    return None


call = json.load(sys.stdin)
edit = call.get("tool_input", {})
path = Path(edit.get("file_path", ""))
if "sales" in path.parts:
    try:
        sale = json.loads(edit.get("new_string", "").strip().splitlines()[0])
        why = problem(sale) if isinstance(sale, dict) else "the sale is not a JSON object"
    except (ValueError, IndexError):
        why = "the sale is not one line of JSON"
    if os.environ.get("LAB3_HOOK_LOG"):  # lab3.py checks that the hook ran
        with open(os.environ["LAB3_HOOK_LOG"], "a") as log:
            log.write(json.dumps({"file": path.name, "refused": why}) + "\n")
    if why:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"Not booked: {why}."}}))

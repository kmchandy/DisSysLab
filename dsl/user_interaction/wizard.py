# dsl/user_interaction/wizard.py
"""
Interactive lesson wizard (kit-based)

Run as a module:
    python -m dsl.user_interaction.wizard --lesson step1

This asks a few multiple-choice questions, then generates a tiny script
that uses the student-facing API (dsl.kit) and the pipeline([...]) helper.
"""

from __future__ import annotations
import argparse
from typing import Any, Dict, List, Tuple

from .lessons import LESSONS, Lesson, Choice, NetworkSpec, CodeBundle
from .render import render_spec_ascii, render_code, save_code_bundle


def _pick(prompt: str, choices: List[Choice]) -> Choice:
    print(f"\n{prompt}")
    for i, ch in enumerate(choices, start=1):
        print(f"  {i}. {ch.label}")
    while True:
        sel = input("Enter number: ").strip()
        if not sel.isdigit():
            print("Please enter a number.")
            continue
        idx = int(sel)
        if 1 <= idx <= len(choices):
            return choices[idx - 1]
        print(f"Please choose 1..{len(choices)}")


def run_wizard(lesson: Lesson) -> Tuple[NetworkSpec, CodeBundle]:
    """
    Ask the lesson's menus, build the NetworkSpec and code bundle.
    Assumes lesson.build expects:
      step1: feed_url, xform_cls, rec
      step2_dicts: feed_url, rec
    """
    answers: List[Choice] = []
    for prompt, opts in lesson.menus:
        answers.append(_pick(prompt, opts))

    # Map answers -> ctx keys expected by the builder
    ctx: Dict[str, Any] = {}
    if lesson.id == "step1":
        ctx["feed_url"] = answers[0].value          # FEEDS
        # "AddSentiment" | "Uppercase"
        ctx["xform_cls"] = answers[1].value
        # ("ToConsole", {...}) or ("ToJSONL", {...})
        ctx["rec"] = answers[2].value
    elif lesson.id == "step2_dicts":
        ctx["feed_url"] = answers[0].value
        ctx["rec"] = answers[1].value
    else:
        # Generic fallback (not used by current lessons)
        for i, ans in enumerate(answers):
            ctx[f"choice_{i}"] = ans.value

    spec, bundle = lesson.build(ctx)
    return spec, bundle


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DisSysLab Lesson Wizard (kit-based)")
    parser.add_argument(
        "--lesson", "-l",
        default="step1",
        choices=list(LESSONS.keys()),
        help="Which lesson to run"
    )
    parser.add_argument(
        "--out", "-o",
        default="build/network.py",
        help="Where to write the generated script"
    )
    args = parser.parse_args()

    lesson = LESSONS[args.lesson]
    print(f"Lesson: {lesson.title}\n{lesson.summary}")

    spec, bundle = run_wizard(lesson)

    # Show what will be built
    print("\n--- Network Spec ---")
    print(render_spec_ascii(spec))

    # Show the generated code
    print("\n--- Generated Code ---")
    print(render_code(bundle))

    # Save code to disk
    bundle = CodeBundle(filename=args.out, code=bundle.code,
                        run_hint=bundle.run_hint)
    save_code_bundle(bundle)
    print(f"\nSaved to: {bundle.filename}")
    print(f"Run with: {bundle.run_hint}")


if __name__ == "__main__":
    main()

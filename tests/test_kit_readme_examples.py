# tests/test_kit_readme_examples.py
"""
Execute (and verify) the '60-second win' snippet from dsl/kit/README_HowTo.md.

We keep one test that runs the snippet exactly as shown (with Print/ToConsole)
and asserts the printed output, and a second test that uses ToList for a
deterministic assertion without stdout.
"""

from __future__ import annotations

from dsl.kit import FromList, Uppercase, Print, pipeline, ToList


def test_readme_60_second_win_print(capsys):
    """
    Runs the exact snippet:

        net = pipeline([
            FromList(["hello", "world"]),
            Uppercase(),
            Print()
        ])
        net.compile_and_run()

    and asserts that the console shows:
        HELLO
        WORLD
    """
    net = pipeline([
        FromList(["hello", "world"]),
        Uppercase(),
        Print(),  # alias of ToConsole()
    ])
    net.compile_and_run()

    out = capsys.readouterr().out.splitlines()
    # Filter to the lines we care about in case other debug prints are present
    data_lines = [line.strip()
                  for line in out if line.strip() in {"HELLO", "WORLD"}]
    assert data_lines == ["HELLO", "WORLD"]


def test_readme_60_second_win_list():
    """
    Variation of the snippet that collects results in a Python list
    (more deterministic than asserting stdout).
    """
    results = []
    net = pipeline([
        FromList(["hello", "world"]),
        Uppercase(),
        ToList(results),
    ])
    net.compile_and_run()
    assert results == ["HELLO", "WORLD"]


if __name__ == "__main__":
    # Standalone demo run (outside pytest):
    net = pipeline([
        FromList(["hello", "world"]),
        Uppercase(),
        Print(),
    ])
    net.compile_and_run()
    # Expected console:
    # HELLO
    # WORLD

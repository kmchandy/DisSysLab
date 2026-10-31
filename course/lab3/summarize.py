"""Rates for every variant run so far.

    python summarize.py
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict

import common


def main() -> None:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for t in sorted(common.RUNS.glob("part*/*/*/trace.json")):
        d = json.loads(t.read_text(encoding="utf-8"))
        groups[(d["meta"]["part"], d["meta"]["variant"])].append(d)
    for (part, variant), runs in sorted(groups.items()):
        cost = sum(common.cost_of(r["trace"]) for r in runs)
        print(f"\n{part} / {variant}: {len(runs)} runs, ${cost:.2f}, "
              f"model {', '.join(sorted({r['meta']['model'] for r in runs}))}, "
              f"SDK {', '.join(sorted({r['meta']['sdk'] for r in runs}))}")
        if part == "part1":
            attacks = [r for r in runs if not r["meta"]["run"].endswith("honest")]
            honest = [r for r in runs if r["meta"]["run"].endswith("honest")]
            print(f"  attack sessions where a sale below the floor was booked: "
                  f"{sum(r['outcome']['attack_got_through'] for r in attacks)} of {len(attacks)}")
            print(f"  book_sale calls the hook denied: "
                  f"{sum(r['outcome']['denied_by_hook'] for r in runs)}")
            print(f"  honest buyers whose sale was booked: "
                  f"{sum(bool(r['outcome']['sales']) for r in honest)} of {len(honest)}")
        else:
            for verdict, n in Counter(r["outcome"]["verdict"] for r in runs).most_common():
                print(f"  {verdict}: {n} of {len(runs)}")


if __name__ == "__main__":
    main()

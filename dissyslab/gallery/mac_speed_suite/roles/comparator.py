"""
---
emits: "next" after each span, then the scorecard after the last
kind: author
in: span, table
out: msg_type (next | scorecard)
out if msg_type is scorecard: scorecard
---
Accumulates every span's evaluation (version 1 logic, unchanged) and
releases the next span by answering "next"; after the last span it sends
the scorecard instead (the whole report, as one field), which the router sends to the report.
"""

from _validation import aggregate_distribution, aggregate_scorecard


class Comparator:
    def __init__(self):
        self.state = {"full": None, "train": [], "test": [], "mc": [], "count": 0,
                      "total": None, "run_config": None}

    def __call__(self, item):
        st = self.state
        tag = item.get("_wf_tag") or {}
        role = tag.get("role")
        if tag.get("total_spans") is not None:
            st["total"] = tag["total_spans"]
        st["count"] += 1
        if role == "full":
            st["full"] = item
            if tag.get("run_config") is not None:
                st["run_config"] = tag["run_config"]
        elif role in ("train", "test", "mc"):
            st[role].append(item)

        if st["total"] is None or st["count"] < st["total"]:
            return [{"msg_type": "next"}]
        report = dict(st["full"] or item)
        if st["run_config"] is not None:
            report["run_settings"] = {**st["run_config"], "cost_bps": report.get("cost_bps"),
                                      "n_days": report.get("n_days")}
        if st["train"] or st["test"]:
            report["walk_forward"] = aggregate_scorecard(st["train"], st["test"])
        if st["mc"]:
            report["monte_carlo"] = aggregate_distribution(st["mc"])
        return [{"msg_type": "scorecard", "scorecard": report}]

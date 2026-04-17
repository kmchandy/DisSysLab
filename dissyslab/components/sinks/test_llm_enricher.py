# dsl.connectors.test_llm_enricher.py
# Standalone demo for LLMEnricher with fake data (no DSL, no network).

from typing import Dict, Any
from pprint import pprint

# --- import your class (assumes llm_enricher.py is in the same folder) ---
from .llm_enricher import LLMEnricher

# --- a tiny mock LLM that returns structured output deterministically ---
TOPICS = ["AI", "jobs", "space"]


def fake_llm_topic(text: str) -> Dict[str, Any]:
    """
    Returns {"scores": {topic: float}, "labels": [...], "primary": str|None}
    Uses dumb keyword rules so we can test gating & mapping.
    """
    t = text.lower()
    scores = {
        "AI":   0.9 if any(w in t for w in ["ai", "llm", "machine learning"]) else 0.1,
        "jobs": 0.8 if any(w in t for w in ["job", "jobs", "hiring", "layoff"]) else 0.1,
        "space": 0.85 if any(w in t for w in ["nasa", "rocket", "space", "launch"]) else 0.1,
    }
    # labels are those >= 0.6
    labels = [k for k, v in scores.items() if v >= 0.6]
    primary = max(scores, key=scores.get) if labels else None
    return {"scores": scores, "labels": labels, "primary": primary}


def keep_if_any_score_at_least(threshold: float):
    def _keep(msg, out):
        return any(float(s) >= threshold for s in (out.get("scores") or {}).values())
    return _keep


def main():
    # 1) Enricher configured for English-only, min length 10, keep if any score ≥ 0.6
    topic_gate = LLMEnricher(
        # look for page_text, else text
        text_getter=("page_text", "text"),
        llm_fn=fake_llm_topic,
        # put raw LLM output under msg["topic"]
        out_ns="topic",
        field_mapping={"labels": "topic_labels",     # hoist a couple fields to top-level
                       "primary": "primary_topic"},
        keep_when=keep_if_any_score_at_least(0.6),
        min_len=10,
        # only call LLM if lang includes 'en'
        require_langs=("en",),
        drop_on_filter=True,                         # drop when not English or too short
        name="topic_gate",
    )

    # 2) Another variant: same, but pass-through when filtered (no LLM call)
    pass_through_when_filtered = LLMEnricher(
        text_getter="text",
        llm_fn=fake_llm_topic,
        # merge at top-level (be careful w/ key clashes)
        out_ns=None,
        field_mapping={"primary": "primary_topic"},
        keep_when=keep_if_any_score_at_least(0.6),
        min_len=30,                                  # longer min length to demo pass-through
        require_langs=("en",),
        drop_on_filter=False,                        # keep message even if filter fails
        name="topic_gate_pt",
    )

    # --- Fake messages (not Bluesky) ---
    msgs = [
        {"id": 1, "lang": ["en"],
            "text": "New LLM improves AI agentic workflows."},
        {"id": 2, "lang": [
            "en"], "text": "NASA announces a new rocket launch next month."},
        {"id": 3, "lang": ["en"],
            "text": "Hiring freeze lifted; 200 new jobs in R&D."},
        # non-English
        {"id": 4, "lang": ["es"],
            "text": "Nuevos puestos de trabajo en la empresa."},
        # below min_len=10
        {"id": 5, "lang": ["en"], "text": "Too short"},
        # no lang info → allowed
        {"id": 6, "lang": [],     "text": "No lang tag here but mentions AI and jobs."},
        # uses page_text
        {"id": 7, "lang": ["en"],
            "page_text": "Space suits and launch windows."},
    ]

    print("\n=== Test 1: topic_gate (drop on filter, enrich with namespace) ===")
    kept = []
    for m in msgs:
        out = topic_gate(m)
        if out is not None:
            kept.append(out)
            print(f"\nKept id={m['id']}")
            pprint(out)
        else:
            print(f"\nDropped id={m['id']}")

    # Basic sanity checks
    assert any(
        "topic" in o for o in kept), "Expected namespaced LLM output at msg['topic']"
    assert any(
        "topic_labels" in o for o in kept), "Expected hoisted labels at msg['topic_labels']"
    # Non-English should be dropped (id=4)
    assert not any(
        o["id"] == 4 for o in kept), "Non-English post should be dropped with drop_on_filter=True"
    # Short text should be dropped (id=5)
    assert not any(
        o["id"] == 5 for o in kept), "Short post should be dropped with drop_on_filter=True"

    print("\n=== Test 2: pass_through_when_filtered (no drop on filter) ===")
    out2 = []
    for m in msgs:
        r = pass_through_when_filtered(m)
        out2.append(r)  # may be unchanged msg or enriched msg
        tag = "ENRICHED" if (isinstance(
            r, dict) and "primary_topic" in r) else "PASSTHRU"
        print(f"id={m['id']} → {tag}")

    # Ensure id=5 (short) was passed through, not dropped
    assert any(isinstance(r, dict) and r.get("id") ==
               5 for r in out2), "Expected pass-through for short post"

    print("\nAll tests passed ✅")


if __name__ == "__main__":
    main()

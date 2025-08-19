import re
import math
from collections import Counter
from dsl.core import SimpleAgent

_word_re = re.compile(r"[A-Za-z']+")


def tokenize(text, stem=False):
    toks = [t.lower() for t in _word_re.findall(str(text))]
    if not stem:
        return toks
    # trivial stemmer: strip ing/ed/s
    out = []
    for t in toks:
        for suf in ("ing", "ed", "s"):
            if len(t) > len(suf) + 2 and t.endswith(suf):
                t = t[: -len(suf)]
                break
        out.append(t)
    return out

# --- similarity metrics ---


def overlap_count(a, b):
    return len(set(a) & set(b))


def jaccard(a, b):
    A, B = set(a), set(b)
    return len(A & B) / len(A | B) if (A or B) else 1.0


def dice(a, b):
    A, B = set(a), set(b)
    return 2*len(A & B)/(len(A)+len(B)) if (A or B) else 1.0


def cosine_tf(a, b):
    ca, cb = Counter(a), Counter(b)
    num = sum(ca[t]*cb[t] for t in set(ca) | set(cb))
    den = math.sqrt(sum(v*v for v in ca.values())) * \
        math.sqrt(sum(v*v for v in cb.values()))
    return 0.0 if den == 0 else num/den


def edit_distance(a_str, b_str):
    a, b = a_str, b_str
    m, n = len(a), len(b)
    dp = list(range(n+1))
    for i in range(1, m+1):
        prev, dp[0] = dp[0], i
        for j in range(1, n+1):
            prev, dp[j] = dp[j], min(
                dp[j] + 1,                  # deletion
                dp[j-1] + 1,                # insertion
                prev + (a[i-1] != b[j-1])   # substitution
            )
    return dp[n]


METRICS = {
    "overlap": lambda ref, x: overlap_count(ref, x),
    "jaccard": lambda ref, x: jaccard(ref, x),
    "dice": lambda ref, x: dice(ref, x),
    "cosine": lambda ref, x: cosine_tf(ref, x),
    "edit": lambda ref, x: edit_distance(" ".join(ref), " ".join(x)),
}


def make_similarity_agent(reference_sentence: str, *, metric="jaccard", stem=False, name="SentenceSimilarityAgent"):
    ref_tokens = tokenize(reference_sentence, stem=stem)
    metric_fn = METRICS.get(metric)
    if metric_fn is None:
        raise ValueError(
            f"Unknown metric '{metric}'. Choose from {list(METRICS)}")

    def init_fn(agent):
        agent.state = {"ref": ref_tokens, "metric": metric, "stem": stem}
        print(
            f"[{name}] Initialized with ref='{reference_sentence}', metric={metric}, stem={stem}")

    def handle_msg(agent, msg, inport=None):
        toks = tokenize(msg, stem=agent.state["stem"])
        score = metric_fn(agent.state["ref"], toks)
        result = {"input": str(
            msg), "metric": agent.state["metric"], "score": round(score, 3)}
        print(f"[{name}] Input='{msg}' → {agent.state['metric']}={result['score']}")
        agent.send(result, outport="out")

    return SimpleAgent(
        name=name,
        inport="in",
        outports=["out"],
        init_fn=init_fn,
        handle_msg=handle_msg,
    )


# Example usage
if __name__ == "__main__":
    from dsl.core import Network
    from dsl.block_lib.stream_generators import generate
    from dsl.block_lib.stream_recorders import RecordToList

    results = []
    net = Network(
        blocks={
            "gen": generate(["hello Jack", "hello there Jack", "goodbye there"], key="text"),
            "sim": make_similarity_agent("hello there", metric="cosine", stem=True),
            "rec": RecordToList(results),
        },
        connections=[
            ("gen", "out", "sim", "in"),
            ("sim", "out", "rec", "in"),
        ],
    )

    net.compile_and_run()
    print("Results (Tier 2):", results)

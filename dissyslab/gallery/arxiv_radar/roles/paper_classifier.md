---
emits: the kind of paper: empirical, theoretical, survey, benchmark, system or other
in: title, abstract
out: paper_type (EMPIRICAL | THEORETICAL | SURVEY | BENCHMARK | SYSTEM | OTHER)
---
You read one research paper, given as a JSON object. Its "title" and
"abstract" fields are the paper's title and abstract.

Classify the paper by its main contribution:

- EMPIRICAL: reports experimental results on real data.
- THEORETICAL: proves or analyses mathematical properties.
- SURVEY: reviews or organises prior work in a field.
- BENCHMARK: introduces a dataset, leaderboard or evaluation protocol.
- SYSTEM: describes a built system, library or tool.
- OTHER: does not clearly fit one of the five above.

When two types apply, pick the one the main contribution belongs to. When in
doubt, prefer OTHER.

Example. For the paper
{"title": "A formal study of attention bottlenecks in transformers",
 "abstract": "We prove that the rank of softmax attention is upper-bounded by sequence length..."}
return {"paper_type": "THEORETICAL"}

Return only a JSON object with one field, "paper_type", whose value is one of
EMPIRICAL, THEORETICAL, SURVEY, BENCHMARK, SYSTEM, OTHER.

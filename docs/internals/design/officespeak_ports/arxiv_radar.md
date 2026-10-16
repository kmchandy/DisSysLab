# Paper port 6: `arxiv_radar` (the pipeline example)

Ported by hand against `officespeak_revised.md`. Nothing here runs yet.

Three arXiv listing pages feed two roles in a row: one classifies each paper by
type, the next rates its relevance to the reader's interests. The display
shows the result.

## Before

```
Sources: arxiv_cs_ai(max_articles=3), arxiv_cs_lg(max_articles=3), arxiv_cs_cl(max_articles=3)
Sinks: intelligence_display

Agents:
Carla is a paper_classifier.
Iris is a relevance_rater.

Connections:
arxiv_cs_ai's destination is Carla.
arxiv_cs_lg's destination is Carla.
arxiv_cs_cl's destination is Carla.
Carla's out is Iris.
Iris's out is intelligence_display.
```

Roles: `paper_classifier.md` (`adds: text`), `relevance_rater.md` (`contract:
structured`), and `impact_rater.md`, which is in `roles/` but not used.

## After

```
sources:
    arxiv_cs_ai(max_articles=3)
    arxiv_cs_lg(max_articles=3)
    arxiv_cs_cl(max_articles=3)

sinks:
    intelligence_display(title="title", text="abstract", color="relevance",
                         lines=["authors", "paper_type", "reason"])

agents:
    Carla: paper_classifier
    Iris: relevance_rater

connections:
    arxiv_cs_ai, arxiv_cs_lg, arxiv_cs_cl -> Carla -> Iris -> intelligence_display
```

The whole network is one connection line: the shape of a pipeline.

### `roles/paper_classifier.md`

```
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
```

### `roles/relevance_rater.md`

```
---
emits: how relevant a paper is to the reader's interests, and why
in: title, abstract
out: relevance (HIGH | MEDIUM | LOW), reason
---
You read one research paper, given as a JSON object. Its "title" and
"abstract" fields are the paper's title and abstract.

The reader is interested in: language models (large and small); stream
processing; agentic AI; personal assistants.

Rate the paper's relevance:

- HIGH: it substantively touches two or more of the interests. The interest
  need not be the main contribution; a substantive mention in the title or
  abstract is enough.
- MEDIUM: it touches exactly one of the interests.
- LOW: it has no meaningful connection to any of them.

"reason" is one sentence, under 30 words, naming the interest areas involved
(or their absence).

Example. For the paper
{"title": "On-device speech recognition with quantised transformers",
 "abstract": "We present a quantisation scheme that reduces transformer model size by 4x ..., enabling deployment of voice assistants and dictation tools on mobile hardware."}
return {"relevance": "MEDIUM", "reason": "A quantisation technique whose stated application is personal voice assistants, one of the listed interests."}

Return only a JSON object with the fields "relevance" (HIGH, MEDIUM or LOW)
and "reason".
```

`impact_rater.md` becomes an exercise: write its front matter and insert it,
`Carla -> Iris -> Ivan -> intelligence_display`, a change of one line.

## Findings

1. **The source has no abstract.** The arXiv listing-page scraper builds
   `text` from title, authors and subjects only. Both roles were told that
   `text` holds an abstract, and the rater was asked to *extract* the
   abstract and authors from it, so the model saw no abstract and had to
   invent one or leave it blank. **To fix:** the arXiv sources emit separate
   fields, `out: source, title, authors, abstract, url, timestamp`, read
   from arXiv's RSS feed (`rss.arxiv.org/rss/cs.AI` etc.), whose items carry
   the abstract in the description ("Abstract: …") and the authors in
   `dc:creator` (checked 16 October). With W22, `dsl check`
   would have reported `abstract` as "not produced upstream" the first time
   it ran.

2. **Parsing is not judgement.** The old rater spent model calls copying
   authors and the abstract out of a string. Under Principle 5 that is the
   source's job, in Python. The rater's work shrinks to one judgement.

3. **The classifier's example contradicted its instructions.** It said "add
   `paper_type`", but its `adds: text` contract asked for `text`, and its
   example output returned `text` only. So `paper_type` was probably never
   produced. This is the third office with this bug (`org_news_filter`,
   `org_two_office_news`), and W23 now catches it.

4. **The rater's MEDIUM example said HIGH.** The example labelled MEDIUM
   returned `"relevance": "HIGH"`. W29 cannot catch this; the reliability
   evaluation (section 11) should check every example in a role against its
   own `out:` values. **Proposal:** add that to section 11.

5. **Iris does not use Carla's field.** The two roles are independent, so
   they could run side by side under a synchronizer. As a pipeline example
   this is honest: the order is a choice, not a dependency. It is also a good
   question for students: "Redraw this office so that Carla and Iris run in
   parallel. What do you need to add?" (A synchronizer and a key.)

6. **The display showed more than three fields.** `intelligence_display`
   printed `author` and `reason` on their own lines when present. Under
   section 7's rule (a display takes the fields it shows as arguments), it
   needs one more argument for extra lines: **proposal**
   `intelligence_display(title="title", text="abstract", color="relevance",
   lines=["authors", "paper_type", "reason"])`.

7. **The interests are written in the role.** The reader's interests are
   Mani's. "Make it yours" is editing one paragraph of `relevance_rater.md`;
   no parameter is needed.

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

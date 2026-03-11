# gallery/org_editor_copywriter/app.py
#
# News Editorial Pipeline
#
# Three news sources feed into an editor that scores sentiment.
# Strongly opinionated articles (score < 0.25 or > 0.75) are
# "interesting" and go to both sinks.
# Lukewarm articles (score 0.25-0.75) are "boring" and go to
# the copy writer, who rewrites them and sends back to the editor.
# Articles that remain boring after MAX_ITERATIONS rewrites get
# status "exhausted" and also go to both sinks.
#
# Iteration tracking is managed entirely by Claude -- no Python logic.
#
# Topology:
#
#   al_jazeera -+
#   bbc_world  -+--> editor --[interesting]--> jsonl_recorder
#   npr_news   -+         |  [exhausted]   +--> console_printer
#                         +-[boring]--> copy_writer
#                                           |
#                                           +-------------> editor
#
# Requires: export ANTHROPIC_API_KEY='your-key'
# Run:      python3 -m examples.org_editorial.app

import json as _json

from dsl import network
from dsl.blocks import Source, Sink
from dsl.blocks.role import Role
from components.sources.rss_normalizer import al_jazeera, bbc_world, npr_news
from components.transformers.ai_agent import ai_agent
from components.sinks.sink_jsonl_recorder import JSONLRecorder
from components.sinks.console_display import ConsoleDisplay


# -- Prompts ------------------------------------------------------------------

MAX_ITERATIONS = 3

EDITOR_PROMPT = f"""You are a news editor. Read the article and score its sentiment
from 0.0 to 1.0, where 0.0 is extremely negative and 1.0 is extremely positive.

The message you receive may include an iteration_number field showing how many
times it has already been rewritten by the copy writer. If there is no
iteration_number field, treat it as 0.

Rules:
- If the score is below 0.25 or above 0.75, assign status interesting.
- If the score is between 0.25 and 0.75 AND iteration_number < {MAX_ITERATIONS},
  assign status boring and increment iteration_number by 1.
- If the score is between 0.25 and 0.75 AND iteration_number >= {MAX_ITERATIONS},
  assign status exhausted.

Return JSON only, no explanation, no nested JSON:
{{"text": "<original text>", "score": <float>, "status": "<interesting or boring or exhausted>", "iteration_number": <int>}}"""

COPY_WRITER_PROMPT = """You are a copy writer. Rewrite the article to make it more
strongly opinionated -- either more positive or more negative, whichever requires
less change. Keep the core facts intact. Preserve all fields from the input message.

Return JSON only, no explanation, no nested JSON:
{"text": "<rewritten text>", "score": <float>, "iteration_number": <pass through unchanged>}"""


# -- AI callables -------------------------------------------------------------

editor_ai = ai_agent(EDITOR_PROMPT)
copy_writer_ai = ai_agent(COPY_WRITER_PROMPT)


# -- Role functions -----------------------------------------------------------

def editor_fn(msg):
    """
    Score sentiment and manage iteration count -- all logic in the prompt.
    Routes to 'interesting', 'boring', or 'exhausted'.
    Interesting and exhausted go to sinks. Boring goes to copy_writer.
    """
    text = _json.dumps(msg) if isinstance(msg, dict) else str(msg)
    try:
        result = editor_ai(text)
        out = {**msg, **result}
        status = result.get("status", "boring")
        if status not in ("interesting", "boring", "exhausted"):
            status = "boring"
        return [(out, status)]
    except Exception as e:
        print(f"[editor] Error: {e}")
        return []


def copy_writer_fn(msg):
    """
    Rewrite to push sentiment to an extreme.
    Passes iteration_number through unchanged -- Claude handles it.
    """
    text = _json.dumps(msg) if isinstance(msg, dict) else str(msg)
    try:
        result = copy_writer_ai(text)
        out = {**msg, **result}
        return [(out, "all")]
    except Exception as e:
        print(f"[copy_writer] Error: {e}")
        return []


# -- Sinks --------------------------------------------------------------------

recorder = JSONLRecorder(path="editorial_output.jsonl",
                         mode="w", flush_every=1)
display = ConsoleDisplay(verbose=False)


# -- Sources ------------------------------------------------------------------

aj = al_jazeera(max_articles=5)
bbc = bbc_world(max_articles=5)
npr = npr_news(max_articles=5)


# -- Nodes --------------------------------------------------------------------

src_aj = Source(fn=aj.run,  name="al_jazeera")
src_bbc = Source(fn=bbc.run, name="bbc_world")
src_npr = Source(fn=npr.run, name="npr_news")

editor = Role(fn=editor_fn,      statuses=[
              "interesting", "boring", "exhausted"], name="editor")
copy_writer = Role(fn=copy_writer_fn, statuses=[
                   "all"],                                name="copy_writer")

sink_jsonl = Sink(fn=recorder, name="jsonl_recorder")
sink_console = Sink(fn=display,  name="console_printer")


# -- Network ------------------------------------------------------------------
#
# editor.out_0 = interesting --> both sinks (fanout)
# editor.out_1 = boring      --> copy_writer
# editor.out_2 = exhausted   --> both sinks (fanout)
#
# NOTE: if network() raises "connected twice" on fanout, replace the
# two sink lines per status with a single Sink that calls both:
#
#   def both_sinks(msg):
#       recorder(msg)
#       display(msg)
#   sink_both = Sink(fn=both_sinks, name="sinks")
#
g = network([
    (src_aj,  editor),
    (src_bbc, editor),
    (src_npr, editor),
    (editor.out_0, sink_jsonl),      # interesting --> jsonl
    (editor.out_0, sink_console),    # interesting --> console  (fanout)
    (editor.out_1, copy_writer),     # boring      --> copy_writer
    (editor.out_2, sink_jsonl),      # exhausted   --> jsonl
    (editor.out_2, sink_console),    # exhausted   --> console  (fanout)
    (copy_writer.out_0, editor),     # rewritten   --> back to editor
])


# -- Run ----------------------------------------------------------------------

if __name__ == "__main__":
    print()
    print("News Editorial Pipeline")
    print("=" * 60)
    print()
    print("  al_jazeera -+")
    print("  bbc_world  -+--> editor --[interesting]--> jsonl + console")
    print("  npr_news   -+         |  [exhausted]   --> jsonl + console")
    print("                        +-[boring]--> copy_writer --> editor")
    print()
    print(f"  Max iterations before exhausted: {MAX_ITERATIONS}")
    print()

    g.run_network()

    recorder.finalize()
    display.finalize()

    print()
    print("=" * 60)
    print("Done! Results saved to editorial_output.jsonl")
    print()

# Office: situation_room

# This office is an instance of the sense → think → respond pattern.
# Pat's four edit slots are labelled below; the rest of the file is
# scaffolding that usually stays the same across remixes. For the
# pattern itself, see docs/PATTERN_sense_think_respond.md.


# ──────────────────────────────────────────────────────────────────
# SLOT 1: SOURCES  (sense)
# Where the office listens to the world. Add, remove, or replace
# these to point at a different feed of incoming items.
# Built-in news sources: bbc_world, bbc_tech, npr_news, al_jazeera,
# hacker_news, techcrunch, mit_tech_review, venturebeat_ai,
# nasa_news, python_jobs. Also: weather, stocks, gmail, calendar,
# webhook, mcp_source, web, search.
# ──────────────────────────────────────────────────────────────────
Sources: bbc_world(max_articles=1), npr_news(max_articles=1), al_jazeera(max_articles=1)


# ──────────────────────────────────────────────────────────────────
# SLOT 4: SINKS  (respond)
# Where finished briefings go. Add, remove, or replace these to send
# output to a terminal, a markdown file, a Slack channel, a Notion
# page, a JSONL archive, a downstream office.
# ──────────────────────────────────────────────────────────────────
Sinks: intelligence_display, jsonl_recorder_briefing(path="briefings.jsonl"), jsonl_recorder_discard(path="rejected.jsonl")


Agents:
# Sasha removes duplicate articles. Framework scaffolding — usually
# leave alone.
Sasha is a deduplicator(by="url").

# ──────────────────────────────────────────────────────────────────
# SLOT 2: PARALLEL THINKERS  (think)
# Each agent below adds one annotation per article (entities,
# severity, topic, location). Add, remove, or replace to extract
# what matters for your domain. They run in parallel; the
# synchronizer below stitches their outputs back together.
# Built-in thinker roles: entity_extractor, severity_classifier,
# topic_tagger, geolocator. Add your own in roles/.
# ──────────────────────────────────────────────────────────────────
Eve is an entity_extractor.
Sam is a severity_classifier.
Tom is a topic_tagger.
Greta is a geolocator.

# Sync merges the parallel branches back into one stream. Framework
# scaffolding — usually leave alone (but if you change which thinkers
# run above, also change Sync's inports in Connections below).
Sync is a synchronizer.

# ──────────────────────────────────────────────────────────────────
# SLOT 3: WRITER  (think → respond)
# Composes the briefing from each annotated article. Change the
# writer's prompt in roles/writer.md (or your own role file) to
# produce a different style: executive summary, technical alert,
# blog draft, customer email.
# ──────────────────────────────────────────────────────────────────
Riley is a writer.

# Jordan decides whether each briefing is publish-worthy. Framework
# scaffolding — change the evaluator prompt if you want stricter or
# looser quality gates, or wire its "revise" output back to Riley to
# get a feedback loop.
Jordan is an evaluator.


Connections:
# Sources fan into the deduplicator.
bbc_world's destination is Sasha.
npr_news's destination is Sasha.
al_jazeera's destination is Sasha.

# Deduplicator fans each unique article out to every parallel thinker.
Sasha's out is Eve, Sam, Tom, Greta.

# Each thinker writes to its named inport on the synchronizer.
Eve's out is Sync's entities.
Sam's out is Sync's severity.
Tom's out is Sync's topic.
Greta's out is Sync's location.

# Synthesised stream flows: Sync → Writer → Evaluator → Sinks.
Sync's out is Riley.
Riley's out is Jordan.
Jordan's publish is intelligence_display, jsonl_recorder_briefing.
Jordan's revise is jsonl_recorder_discard.

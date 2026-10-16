---
name: sensor-office-builder
description: Build DisSysLab offices that classify audio, images, or sensor signals — wrapping a model or a signal-processing step as one Python role and deciding what to pass on. Use when someone wants to identify birds from recordings, animals or objects in camera-trap or folder photos, sounds or loudness from an audio stream, or to threshold/smooth a sensor reading and alert on it; says "classify these photos", "what bird is this", "watch the noise level", "alert me when the reading crosses X", or wants a machine-learning model wired into a monitoring pipeline. Builds on the office-builder skill; requires dissyslab plus whichever model library the task needs.
---

# Sensing offices

**Skill version: `2026-08-19.f296782`.** If anyone asks which version of this
skill is loaded, answer with that string, exactly.

This is the `office-builder` skill applied to one recurring shape. Read that
skill first, including its rule on checking what the install actually has
and never repairing it. That rule matters more here, since these offices
also depend on model libraries that may be absent. `office.md`, roles,
`dsl check` and `dsl run` work the same way; `dsl grammar` and
`dsl grammar roles` have the details. This adds only what is specific to
classifying a signal.

## The shape

```
source  ->  classifier (a local Python role)  ->  decision  ->  router  ->  sinks
```

1. **A built-in source** reads the raw signal: `audio_folder`,
   `image_folder`, `audio_mic`, or `file_source` with recorded readings
   (`dsl grammar sources`). Do not write one unless none fits.
2. **One local Python role** wraps the model. This is the only custom part.
3. **A decision**: a small Python annotator that adds a field such as
   `keep (yes | no)` from a threshold on the classifier's confidence. Often
   the classifier's own `level (HIGH | MEDIUM | LOW)` field is enough.
4. **A router** on that field sends what matters to a sink and the rest to
   `discard`, or better while developing, to a file you can read.

Keep the model and the decision as two agents. Each has one job, and
separating them lets the user change the threshold without touching the
model.

## Writing the classifier role

A Python role as `dsl grammar roles` describes: one class, no DisSysLab
import, front matter in the docstring. Specific to models:

- **Load the model once, in `__init__`.** Loading per message dominates the
  run time.
- **Import the library inside the method** and list it in `needs:`.
  `dsl check` then names any missing package with its `pip install` line,
  without importing anything, and `dsl run` stops before starting rather
  than failing on every message.
- **Keep the logic testable without the model:** call the model in
  `__call__` and pass its result to a plain function,
  `step(item, detections)`, which a test can call with a hand-written list.
- **Report, do not filter.** Emit the label, the confidence and enough to
  identify the input (filename, time). Let the decision and router choose.
  A clip with nothing found gets a message saying so, so no input
  disappears silently.

Read the gallery's one before writing your own: `dsl init backyard_birds
birds_example`, then `birds_example/roles/bird_classifier.py`. BirdNET via
`birdnetlib`, an author sending one message per species heard, with
`out if found is yes:` for the detection fields. Read the copy; the
installed package is to be read, never written.

**Sensing often needs no model at all.** A moving average, an RMS, a
threshold, a rate of change: small Python roles that cost nothing to run,
and the right answer more often than a classifier.

## Dependencies

Each model brings its own: `torch` and `torchvision`, `birdnetlib`, `numpy`
and `scipy`. They are not dissyslab dependencies. Install what the office
needs, tell the user what you are installing and roughly how large it is,
and prefer the smallest model that answers the question: a student on a
laptop should not pull a multi-gigabyte checkpoint to identify garden birds.

## Cost and honesty

State the model's limits in the office's README rather than letting the
user discover them. An ImageNet classifier applied to camera-trap photos
returns ImageNet's classes, which are not a wildlife taxonomy, and a
confident wrong label is worse than a low-confidence one. Say what
threshold you chose and why.

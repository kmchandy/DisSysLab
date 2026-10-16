# Paper port 8: `backyard_birds` (a Python role with a resource)

Ported by hand against `officespeak_revised.md`. Nothing here runs yet.

A folder of audio clips feeds one agent, which runs BirdNET (a classical
classifier, not a language model) on each clip and sends one message per
species heard.

## Before

```
Sources: audio_folder(path="./samples/", glob="*.mp3", max_files=10)
Sinks: intelligence_display,
       jsonl_recorder(path="bird_detections.jsonl")

Agents:
Alex is a bird_classifier(min_confidence=0.5).

Connections:
audio_folder's destination is Alex.
Alex's out is intelligence_display, jsonl_recorder.
```

`roles/bird_classifier.py` (240 lines) subclasses the framework's `Agent`,
runs its own receive loop, and loads BirdNET lazily on the first message so
that `dsl build` works without `birdnetlib`. If `birdnetlib` is missing, it
prints a hint and sends a "BirdNET not installed" message **for every clip**,
so the office runs end to end and shows nothing useful. A clip with no
detections gives a "No birds in …" message. Any other error is printed and
the clip silently skipped. It adds `significance` so that the display tints
the line.

## After

```
sources:
    clips: audio_folder(path="./samples/", glob="*.mp3", max_files=10)

sinks:
    intelligence_display(color="level", lines=["file"])
    jsonl_recorder(path="bird_detections.jsonl")

agents:
    Alex: bird_classifier(min_confidence=0.5)

connections:
    clips -> Alex -> intelligence_display, jsonl_recorder
```

### `roles/bird_classifier.py`

```python
"""
---
emits: one message per bird species heard in an audio clip
kind: author
needs: birdnetlib, librosa, resampy
in: path, filename
out: found (yes | no), title, text, file, level (HIGH | MEDIUM | LOW)
out if found is yes: species, scientific_name, confidence, start_time, end_time
---
Arguments: min_confidence -- detections below this are ignored (default 0.5).
"""


def level(confidence):
    if confidence >= 0.8:
        return "HIGH"
    if confidence >= 0.5:
        return "MEDIUM"
    return "LOW"


def step(item, detections):
    """BirdNET's detections for one clip -> the messages to send."""
    name = item["filename"]
    if not detections:
        return [{"found": "no", "title": f"No birds in {name}",
                 "text": "No species above the confidence threshold.",
                 "file": name, "level": "LOW"}]
    return [{"found": "yes",
             "title": d["common_name"],
             "text": f"Heard {d['start_time']:.1f}-{d['end_time']:.1f}s into {name}.",
             "file": name,
             "level": level(d["confidence"]),
             "species": d["common_name"],
             "scientific_name": d["scientific_name"],
             "confidence": d["confidence"],
             "start_time": d["start_time"],
             "end_time": d["end_time"]}
            for d in detections]


class BirdClassifier:
    def __init__(self, min_confidence=0.5):
        from birdnetlib.analyzer import Analyzer
        self.settings = {"min_confidence": float(min_confidence)}
        self.analyzer = Analyzer()          # a resource: built at start, never saved

    def __call__(self, item):
        from birdnetlib import Recording
        recording = Recording(self.analyzer, item["path"],
                              min_conf=self.settings["min_confidence"])
        recording.analyze()
        return step(item, recording.detections)
```

About 45 lines instead of 240. `step` is pure: a student tests it with a
hand-written list of detections and no BirdNET installed. The model is used
only in `__call__`, and its result is passed to `step`.

## Findings

1. **`dsl check` must not construct roles.** Section 8, row 2 says the class
   is constructed "seen with `dsl check`". Constructing this role loads
   BirdNET (and downloads 50 MB the first time). **Proposal:** `dsl check`
   reads the constructor's signature (for W19) and never constructs; only
   `dsl run` and `dsl try` construct. Then the old lazy-loading trick is not
   needed.

2. **A missing package fails once, at the start.** The old role sent a
   diagnostic message per clip, so a run "worked" and showed nothing: a
   graceful fallback hiding the real path. **Proposal:** a new front-matter
   key, `needs:`, lists the packages a Python role, source or sink imports.
   `dsl check` reports any that are not installed, with the `pip install`
   line, without importing anything (`importlib.util.find_spec`). If one is
   missing at `dsl run`, the run stops before starting, naming the agent and
   the command.

3. **An exception inside a role is not covered by the spec.** File not
   found, an unreadable clip. Section 4.5 covers bad replies, not raised
   exceptions. **Proposal:** an exception raised by `__call__` is a failure of
   that one message, exactly like a bad reply (4.5 item 5): dropped, counted,
   the first one quoted in the run summary with the exception, exit non-zero.
   The old role printed and skipped silently.

4. **The example form for a role with a resource.** 4.3 gives
   `step(item, settings)` and `step(item, state, settings)`. Here the
   judgement comes from a model, so the testable part is what happens to the
   model's result. **Proposal:** add the form
   `step(item, result[, state][, settings])`, with the resource called in
   `__call__` and its result passed in. The same form fits any role that
   calls an outside service.

5. **Conditional `out` in a Python author.** "No birds in this clip" is kept
   as a message, so a clip is never dropped silently, and its shape differs
   from a detection. The `out if found is yes:` line from port 3 handles it
   without change. `level` is on both shapes because the display colours by
   it, and a field the sink needs cannot be optional.

6. **`significance` was a field invented for the display.** It becomes
   `level`, named for what it is, and the display is told to colour by it
   (`color="level"`, section 7).

7. **`audio_folder` declares**
   `out: path, filename, title, source, index, total`, and its folder argument
   is already `path`, matching 3.1.

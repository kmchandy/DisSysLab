---
name: sensor-office-builder
description: Build DisSysLab offices that classify audio, images, or sensor signals — wrapping a model or a signal-processing step as one Python role and gating its output. Use when someone wants to identify birds from recordings, animals or objects in camera-trap or folder photos, sounds or loudness from an audio stream, or to threshold/smooth a sensor reading and alert on it; says "classify these photos", "what bird is this", "watch the noise level", "alert me when the reading crosses X", or wants a machine-learning model wired into a monitoring pipeline. Builds on the office-builder skill; requires dissyslab plus whichever model library the task needs.
---

# Sensing offices

**Skill version: `2026-08-19.935f28d`.** If anyone asks which version of this
skill is loaded, answer with that string, exactly.

This is the `office-builder` skill applied to one recurring shape. Read that
skill first — including its rule on checking what the install actually has
and never repairing it, which applies here unchanged and matters more, since
these offices also depend on model libraries that may be absent — `office.md`, roles, `dsl check`, and the build loop all work the
same way here. This adds only what is specific to classifying a signal.

## The shape

Every sensing office in the gallery is the same four steps, and only step 2 is
ever custom:

```
folder/stream source  ->  classifier (local Python role)  ->  gate  ->  sink
```

1. **A shipped source** reads the raw signal — an image folder, an audio
   folder, an audio stream, a sensor reading. Do not write one; check
   `docs/SOURCES_AND_SINKS.md` first.
2. **One local Python role** wraps the model. This is the only custom part.
3. **A generic gate** decides what is worth passing on — the library's
   `confidence_filter`, or a threshold role.
4. **A shipped sink** records or displays.

**The line that decides what goes where**, and the gallery follows it: the
model wrapper is local because its contract is on *content* — these image
classes, this species list, this sample rate. The gating that follows is
generic and belongs to the library. Keep them as two agents. Do not let the
classifier also filter; each agent has one job, and separating them is what
lets the user change the threshold without touching the model.

## Writing the classifier role

A Python role, exactly as `office-builder` describes — `Agent` subclass,
infinite `run()` loop over `self.recv`, module-level `role = AgentRoleEntry(...)`.
Three things specific to models:

- **Load the model once, in `__init__`, never inside `run()`.** Loading per
  message will dominate the run time.
- **Emit one message per detection, and do not filter.** Include the label,
  the confidence, and enough of the input to identify it (filename, timestamp).
  Let the downstream gate decide what survives.
- **Document the message shape in the module docstring** — what arrives and
  what is emitted, field by field. The gallery roles do this and it is what
  makes them readable a month later.

Worked examples to read before writing:

| Office | Wraps | Note |
|---|---|---|
| `wildlife_watcher` | MobileNetV3-Small via `torchvision`, ImageNet classes | Emits top-1 plus top-5, flags animal vs object, filters nothing |
| `backyard_birds` | BirdNET via `birdnetlib` | One message per detected species, not per clip |
| `loudness_monitor` | `numpy` / `scipy` on an audio stream | No model — a sliding-window RMS and a threshold |

`loudness_monitor` is the useful reminder that "sensing" often needs no model
at all. A moving average, an RMS, a threshold, a rate of change — these are
small deterministic Python roles, they cost nothing to run, and they are the
right answer far more often than a classifier.

## Dependencies

Each model brings its own: `torch` + `torchvision`, `birdnetlib`, `numpy` +
`scipy`. These are **not** dissyslab dependencies and are not installed with
it. Install what the specific office needs, tell the user what you are
installing and roughly how large it is, and prefer the smallest model that
answers the question — a student on a laptop should not be pulling a
multi-gigabyte checkpoint to identify garden birds.

## Cost and honesty

State the model's limits in the office's README rather than letting the user
discover them. An ImageNet classifier applied to camera-trap photos returns
ImageNet's classes, which are not a wildlife taxonomy — `wildlife_watcher`
says so plainly, and a confident wrong label is worse than a low-confidence
one. Set the gate's threshold with that in mind, and say what threshold you
chose and why.

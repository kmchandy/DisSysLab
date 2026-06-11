# wildlife_watcher

Identify the animals in a folder of camera-trap photos.

This office is the image-modality counterpart to `loudness_monitor`.
It reads `.jpg` / `.png` files from `samples/`, runs each one
through a small pretrained vision model, and emits a card per
confident animal detection. No LLM. The downstream filter is a
**framework-library specialist** (`confidence_filter`) — the same
filter is available to every office in DSL, so building a new
classifier app means writing one role, not two.

## What it does

```
image_folder  →  Alex (animal_classifier)  →  Bryn (confidence_filter)  →  intelligence_display
```

Three specialist agents between the source and the sink:

- `image_folder` emits one message per image file
- **Alex** runs MobileNetV3-Small (ImageNet pretrained) and emits a top prediction + category (`"animal"` or `"object"`) + top-5 list
- **Bryn** is the framework's `confidence_filter`. Drops detections below 0.4 confidence and drops anything whose category is not `"animal"`. Same role you would use after any classifier in any other office — no per-office filter code needed.

The reuse is the point. Alex is content-specific (it knows about ImageNet). Bryn is shape-specific (it gates on `confidence` and `category`). One belongs in the office; the other belongs in the library.

## Setup

```bash
pip install torch torchvision pillow numpy
```

torchvision wheels install cleanly on macOS and Linux — no
`llvmlite`-style compilation failures. First inference downloads
the ~5 MB MobileNetV3-Small weights from the PyTorch hub.
Subsequent runs are offline.

## Sample images

The office ships with a download script for six small
public-domain animal photos (white-tailed deer, bald eagle, black
bear, red fox, coyote, mountain lion). Run it once from the
samples folder:

```bash
cd dissyslab/gallery/apps/wildlife_watcher/samples
python download_samples.py
```

Pure standard library, no pip install needed. Five photos are
works of US federal employees (USFWS / USDA / NPS) released into
the public domain; one is CC0. The script writes a `LICENSES.md`
next to the images crediting each photographer and linking to the
canonical Wikimedia Commons page where each license can be
independently verified. Total download: ~360 KB. Existing files
are skipped, so reruns are safe.

Then:

```bash
dsl run wildlife_watcher
```

Six cards roll into the terminal — one per animal that crosses
the confidence threshold.

**Want to use your own images instead?** Drop any `.jpg` or `.png`
into `samples/` and rerun — the office reads every supported
image in the folder. The downloader script is only there to
remove the "I have no photos handy" friction for HN drive-bys.

## Tuning

Edit `office.md` and rerun. Two knobs on the filter:

```
Agents:
Bryn is a confidence_filter(min_confidence=0.6, category_field="category", category_whitelist="animal").
```

- `min_confidence` — raise to 0.6 or 0.7 if you want only the most
  unambiguous detections. Lower to 0.3 to see borderline calls.
- `category_whitelist` — pass `("animal", "object")` if you want
  *everything* the classifier sees, not just animals. (Camera-trap
  shots of fences and umbrellas are common false positives — this
  is the knob that suppresses them.)

To process more images per run, raise the source cap:

```
Sources: image_folder(folder="./samples/", max_images=100)
```

## How these Python roles were written

The per-office role (`animal_classifier.py`) was written by Claude,
using a short prompt that gave the input/output contract and the
torchvision API to use. The library role (`confidence_filter.py`)
was written the same way and added to `dissyslab/roles/` so any
office can use it.

### Prompt for `animal_classifier.py`

> *I am writing a DisSysLab Python role. The file goes in
> `roles/animal_classifier.py` and is loaded by the framework via
> `AgentRoleEntry`. Use
> `dissyslab/gallery/apps/loudness_monitor/roles/threshold_detector.py`
> as the pattern for the boilerplate.*
>
> *The agent receives one message per image on inport `in_`.
> Each message has shape*
>
> >     {"filename": str, "pixels": np.ndarray (H,W,3) float [0,1],
> >      "width": int, "height": int}
>
> *For each message, run MobileNetV3-Small from torchvision
> (pretrained on ImageNet) and emit one message on outport `out_`
> with the top prediction, top-5 list, and a category flag.*
>
> *Category is `"animal"` if the top class index is below 398
> (organisms in ImageNet ordering), else `"object"`.*
>
> *Output shape:*
>
> >     {"source": "wildlife_watcher", "filename": str,
> >      "label": str, "label_index": int, "confidence": float,
> >      "category": "animal" | "object",
> >      "top_5": [(label, confidence), ...],
> >      "title": str, "text": str,
> >      "significance": "HIGH" | "MEDIUM" | "LOW"}
>
> *Significance bucket: >= 0.7 -> HIGH, >= 0.4 -> MEDIUM, else LOW.*
>
> *Lazy-import torch and torchvision so `dsl build` succeeds when
> they are not installed; print a one-line install hint if they
> are missing at run time.*

### Prompt for `confidence_filter.py` (framework library role)

> *I am writing a DisSysLab Python role for the framework library
> (not per-office). It goes in `dissyslab/roles/confidence_filter.py`
> alongside the English `.md` roles. Same boilerplate as
> `gate.py` — subclass `Agent`, register with `AgentRoleEntry`.*
>
> *Generic confidence-and-category gate. Constructor params:
> `min_confidence=0.5`, `confidence_field="confidence"`,
> `category_field=None`, `category_whitelist=None`.*
>
> *Behaviour: for each inbound dict, look up `msg[confidence_field]`
> as a float. If missing, non-numeric, or below `min_confidence`,
> drop the message. If `category_field` is set, also look up
> `msg[category_field]` and check it against the whitelist
> (string match, list/tuple/set membership, or callable). On
> both passes, forward the message untouched.*
>
> *No domain assumptions — the role works for any classifier
> output whose messages carry a `confidence` field. Vision, audio,
> NLP, anomaly detection. Used by `wildlife_watcher` to drop
> non-animal detections; future offices can use it without
> modification.*

The library prompt is slightly longer than the per-office prompt
because the library role has more configurability — that is the
nature of reusable code. The per-office role hardcodes ImageNet
and the 398-class animal cutoff; the library role hardcodes
nothing.

## What this demonstrates

| DSL feature | Where it shows up |
|---|---|
| Source primitive for files | `image_folder` in `office.md` |
| ML-model agent (no LLM) | Alex wraps MobileNetV3-Small |
| **Framework-library specialist reuse** | Bryn is `confidence_filter` from `dissyslab/roles/` — not per-app code |
| Stable contract on agent inputs/outputs | Alex emits `confidence` + `category`; Bryn gates on those field names with no other knowledge of vision |
| LLM-as-code-generator | both Python roles written by Claude from the prompts above |

The reuse story is the headline. After wildlife_watcher, any
future classification office in DSL — a sentiment monitor, a
disease-symptom triage, an anomaly detector — uses the same
`confidence_filter` between its classifier and its sinks. That is
the compounding value of building specialist agents instead of
end-to-end pipelines.

## License

MIT. `torch`, `torchvision`, and `pillow` carry their own
licenses; consult their projects. MobileNetV3-Small weights are
released by the PyTorch team under the BSD-3-Clause license.

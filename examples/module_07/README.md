# Module 07: Gather-Scatter — Photo Quality Scorer

A photo quality analyzer that examines every image three ways simultaneously —
sharpness, exposure, and composition — then combines the results into a verdict:
**Post it ✓ / Maybe ~ / Delete ✗**

This module uses the **same gather-scatter pattern as Module 06**.
The network wiring is identical. Only the source and analyzers change.

---

## Part 1: Run It (5 minutes)

```bash
pip install Pillow scipy numpy

# Download 6 demo photos (CC0 license, run once)
python3 examples/module_07/download_demo_images.py

# Run the analyzer
python3 -m examples.module_07.app
```

You should see output like this, one box per photo:

```
╔═════════════════════════════════════════════════════════════════╗
║   📸  Photo Quality Scorer                                      ║
║   3 analyzers running in parallel via MergeSynch                ║
╚═════════════════════════════════════════════════════════════════╝

  Each photo is analyzed for: sharpness · exposure · composition
  ✅ Post it  🤔 Maybe  🗑️  Delete

┌─ mountain_snow.jpg  (1/6)  ✅ Post it ✓  score=0.71
│  Sharpness   🔍 sharp     lap_var=  7411.3  score=0.741
│  Exposure    ☀️  good      brightness=0.436     score=0.790
│  Composition 📐 sparse      thirds=0.250        score=0.499
│  Note: Well-focused, clear detail throughout
└─────────────────────────────────────────────────────────────────

┌─ foggy_trees.jpg  (2/6)  🤔 Maybe   ~  score=0.50
│  Sharpness   💧 blurry    lap_var=    87.7  score=0.009
│  Exposure    ☀️  good      brightness=0.458     score=0.799
│  Composition 🎨 good        thirds=0.464        score=0.870
│  Note: Blurry — out of focus or motion blur
└─────────────────────────────────────────────────────────────────

┌─ night_scene.jpg  (6/6)  🗑️  Delete  ✗  score=0.24
│  Sharpness   🌫️  soft      lap_var=   403.4  score=0.040
│  Exposure    🌑 dark      brightness=0.128     score=0.338
│  Composition 📐 sparse      thirds=0.211        score=0.422
│  Note: Slightly soft — some detail lost
└─────────────────────────────────────────────────────────────────

===================================================================
  Summary: 6 photos analyzed
  ✅ Post it: 3   🤔 Maybe: 2   🗑️  Delete: 1
===================================================================
```

Results are also saved to `photo_scores.jsonl` — one JSON line per photo.

---

## Part 2: Understand It (20 minutes)

### The same pattern as Module 06

Compare the two networks side by side:

**Module 06 — RL Analyzer:**
```
cartpole_source ──→ reward_analyzer   ──┐
                ├─→ policy_analyzer   ──┼──→ merge_synch ──→ dashboard
                └─→ curve_analyzer    ──┘
```

**Module 07 — Photo Scorer:**
```
image_source ──→ sharpness_analyzer  ──┐
             ├─→ exposure_analyzer   ──┼──→ merge_synch ──→ dashboard
             └─→ composition_analyzer──┘
```

The `app.py` network wiring is **identical** — the same 9 lines connecting
source → three analyzers → merge → output. This is the lesson: once you
know the gather-scatter pattern, you can apply it to any domain.

### What the three analyzers measure

**SharpnessAnalyzer** — answers "is this photo in focus?"

Uses the **Laplacian variance** method, the most widely used sharpness
metric in computational photography. The Laplacian operator detects rapid
changes in pixel intensity. A sharp image has many strong edges → high
variance. A blurry image has smooth gradients → low variance.

```python
{"laplacian_var": 7411.3, "sharpness_score": 0.741, "verdict": "sharp"}
{"laplacian_var":   87.7, "sharpness_score": 0.009, "verdict": "blurry"}
```

**ExposureAnalyzer** — answers "is this photo well-lit?"

Computes mean brightness (0=black, 1=white) and checks for clipped pixels —
highlights blown to pure white or shadows crushed to pure black. The ideal
brightness range is 0.35–0.76. Outside that range the photo is under or
overexposed.

```python
{"mean_brightness": 0.128, "exposure_score": 0.338, "verdict": "dark"}
{"mean_brightness": 0.829, "exposure_score": 0.733, "verdict": "bright"}
{"mean_brightness": 0.436, "exposure_score": 0.790, "verdict": "good"}
```

**CompositionAnalyzer** — answers "is the subject well-placed?"

Uses the **rule of thirds**: divide the frame into a 3×3 grid and place
the subject near one of the four intersection points ("power points")
rather than dead center. This analyzer detects edges using the Sobel
operator, then measures what fraction of strong edges fall near those
power points.

```python
{"thirds_coverage": 0.464, "composition_score": 0.870, "verdict": "good"}
{"thirds_coverage": 0.203, "composition_score": 0.406, "verdict": "sparse"}
```

### How the verdict is computed

`PhotoDashboard` combines all three scores with weights:

```python
quality_score = 0.4 * sharpness_score
              + 0.4 * exposure_score
              + 0.2 * composition_score
```

Sharpness and exposure are weighted equally at 40% each because they are
the most common reasons a photo fails. Composition gets 20% — a blurry
but beautifully composed shot is still a bad photo.

```python
if quality_score > 0.50:   verdict = "Post it ✓"
elif quality_score > 0.30: verdict = "Maybe   ~"
else:                       verdict = "Delete  ✗"
```

### The image message

`ImageFolderSource` loads each photo and emits a dict that all three
analyzers receive simultaneously:

```python
{
    "filename": "mountain_snow.jpg",
    "filepath": "examples/module_07/demo_images/mountain_snow.jpg",
    "pixels":   np.array(...),   # H×W×3 float array, values 0.0–1.0
    "gray":     np.array(...),   # H×W float array (grayscale luminance)
    "width":    640,
    "height":   480,
    "index":    1,               # position in folder
    "total":    6,               # total images being processed
}
```

Each analyzer reads only what it needs — `SharpnessAnalyzer` and
`CompositionAnalyzer` use `gray`; `ExposureAnalyzer` also uses `gray`.
The `pixels` RGB array is available for future analyzers (e.g., a color
analyzer in Module 08).

### Why parallel matters here

The three analyzers run in separate threads. For numpy operations on a
640×480 image each takes ~5ms. In series that would be ~15ms per photo.
In parallel it is ~5ms — the time of the slowest analyzer.

For expensive operations — running a neural network on each image, calling
an AI API, writing to a database — the saving is enormous. The gather-scatter
pattern is how production image processing pipelines are built.

### The download script as a design decision

The six demo images come from [Lorem Picsum](https://picsum.photos), a free
CC0 photo service. They were chosen to span the full quality spectrum:

| File | Sharpness | Exposure | Composition | Verdict |
|------|-----------|----------|-------------|---------|
| `forest_path.jpg` | sharp | good | sparse | Post it ✓ |
| `mountain_snow.jpg` | sharp | good | sparse | Post it ✓ |
| `city_street.jpg` | soft | good | good | Post it ✓ |
| `foggy_trees.jpg` | blurry | good | good | Maybe ~ |
| `bright_bokeh.jpg` | blurry | bright | sparse | Maybe ~ |
| `night_scene.jpg` | soft | dark | sparse | Delete ✗ |

Notice `city_street.jpg` — it scores "Post it" despite moderate sharpness
because its exposure and composition are both excellent. The three scores
together tell a more complete story than any one alone.

---

## Part 3: Make It Yours (15 minutes)

### Step 1: Use your own photos (one line change)

The most important experiment. Edit `app.py`:

```python
# Change this:
imgs = ImageFolderSource(folder="examples/module_07/demo_images")

# To this:
imgs = ImageFolderSource(folder="/Users/yourname/Pictures/vacation_2024")
```

Run it again. You will get quality scores and verdicts for your actual
photos. The JSONL output lets you sort them by score.

### Step 2: Download photos that interest you

Edit `download_demo_images.py`. The `IMAGES` list controls what gets
downloaded:

```python
IMAGES = [
    # Replace these with Picsum IDs you like from https://picsum.photos
    ("my_landscape.jpg",  42,  "Mountain lake",    "?"),
    ("my_portrait.jpg",   87,  "Street portrait",  "?"),
    ("my_action.jpg",    200,  "Sports action",    "?"),
    # ... add as many as you like
]
```

Browse [picsum.photos](https://picsum.photos) to find IDs. Or replace the
URL entirely with any direct image link from a CC0 source like
[NASA images](https://www.nasa.gov/images) or
[Wikimedia Commons](https://commons.wikimedia.org/wiki/Category:CC0).

### Step 3: Ask Claude to add a fourth analyzer

Try this prompt:

> I have a DisSysLab photo quality scorer with three parallel analyzers:
> SharpnessAnalyzer, ExposureAnalyzer, and CompositionAnalyzer. They
> connect through MergeSynch to a PhotoDashboard.
>
> Add a fourth analyzer called ColorVibrancyAnalyzer. It should use the
> `pixels` array (H×W×3 RGB float array) to compute:
> - `saturation_mean`: average color saturation (0=grey, 1=fully saturated)
> - `saturation_score`: normalized 0–1 score (higher = more vibrant)
> - `verdict`: "vibrant" / "muted" / "greyscale"
>
> Update MergeSynch to num_inputs=4, add merge.in_3, and update
> PhotoDashboard to unpack and display the fourth result.

### Experiment: adjust the quality weights

In `photo_dashboard.py`, the verdict function:

```python
quality_score = 0.4 * sharpness_score
              + 0.4 * exposure_score
              + 0.2 * composition_score
```

Try prioritizing composition for artistic photos:

```python
quality_score = 0.3 * sharpness_score
              + 0.3 * exposure_score
              + 0.4 * composition_score
```

Does the ranking of your photos change?

### Plot the scores

After running `app.py`, a `photo_scores.jsonl` file is saved. Plot it:

```python
import json
import matplotlib.pyplot as plt

data = [json.loads(line) for line in open("photo_scores.jsonl")]

filenames = [d["filename"]         for d in data]
quality   = [d["quality_score"]    for d in data]
sharpness = [d["sharpness_score"]  for d in data]
exposure  = [d["exposure_score"]   for d in data]
composit  = [d["composition_score"] for d in data]

x = range(len(filenames))
width = 0.25

fig, ax = plt.subplots(figsize=(12, 6))
ax.bar([i - width   for i in x], sharpness, width, label="Sharpness",   color="steelblue")
ax.bar([i           for i in x], exposure,  width, label="Exposure",    color="orange")
ax.bar([i + width   for i in x], composit,  width, label="Composition", color="green")
ax.plot(x, quality, "ro--", label="Quality score", linewidth=2, markersize=8)

ax.axhline(y=0.5, color="black", linestyle="--", alpha=0.3, label="Post it threshold")
ax.set_xticks(list(x))
ax.set_xticklabels([f.replace(".jpg", "") for f in filenames], rotation=30, ha="right")
ax.set_ylabel("Score")
ax.set_title("Photo Quality Breakdown")
ax.legend()
ax.set_ylim(0, 1.1)

plt.tight_layout()
plt.savefig("photo_quality_chart.png")
plt.show()
print("Saved: photo_quality_chart.png")
```

---

## Part 4: Real AI — Use Claude to Score Your Photos (30 minutes)

The three analyzers in this module use classical signal processing — pure
numpy and scipy, no AI. But you can replace any analyzer with a real AI
call that gives richer explanations.

Replace `SharpnessAnalyzer` with a Claude-powered analyzer:

```python
# In app.py, add:
from dissyslab.components.transformers.prompts import READABILITY_ANALYZER
from dissyslab.components.transformers.ai_agent import ai_agent

# A custom prompt for photo sharpness
PHOTO_SHARPNESS_PROMPT = """You are a professional photographer.
Analyze this image description and rate its sharpness on a scale 0-1.

Return JSON:
{
    "sharpness_score": 0.0-1.0,
    "verdict": "sharp" | "soft" | "blurry",
    "note": "one sentence explanation"
}"""

# Wrap as a DisSysLab transform
def ai_sharpness(image: dict) -> dict:
    # For a real implementation, encode image as base64 and send to Claude vision
    # For now, combine pixel statistics into a text description
    gray = image["gray"]
    description = f"Image {image['filename']}: mean brightness {gray.mean():.2f}, std {gray.std():.2f}"
    result = ai_agent(PHOTO_SHARPNESS_PROMPT)(description)
    result["filename"] = image["filename"]
    return result
```

The real power comes from Claude's vision capability — sending the actual
image pixels. That upgrade path (classical → AI) is the same one-line
import change you saw in Modules 01–05.

---

## How Each File Works

Test each component independently before running the full network:

```bash
python3 examples/module_07/download_demo_images.py    # fetch 6 CC0 photos
python3 dissyslab/components/sources/image_folder_source.py     # lists images found
python3 dissyslab/components/transformers/sharpness_analyzer.py # sharpness on all 6
python3 dissyslab/components/transformers/exposure_analyzer.py  # exposure on all 6
python3 dissyslab/components/transformers/composition_analyzer.py # composition on all 6
python3 dissyslab/components/sinks/photo_dashboard.py           # shows formatted output
```

| File | What it does |
|------|-------------|
| `download_demo_images.py` | Downloads 6 CC0 photos from picsum.photos |
| `image_folder_source.py` | Reads images from a folder, emits one dict per photo |
| `sharpness_analyzer.py` | Laplacian variance — detects blur |
| `exposure_analyzer.py` | Mean brightness + clipping — detects under/overexposure |
| `composition_analyzer.py` | Rule of thirds via Sobel edges |
| `photo_dashboard.py` | Terminal display, unpacks MergeSynch output |
| `app.py` | Full network wiring — 9 lines, identical structure to M06 |
| `test_module_07.py` | Tests for all components and the full network |

---

## Run the Tests

```bash
pytest examples/module_07/test_module_07.py -v
```

Tests are in three layers. The first layer (unit tests) runs without demo
images — it uses synthetic numpy arrays. The second and third layers
(integration and network tests) require the demo images and are
automatically skipped if you haven't run `download_demo_images.py` yet.

---

## Key Concepts in This Module

**Same pattern, different domain** — the gather-scatter topology works for
any data. RL checkpoints in Module 06, images here, financial data, sensor
readings, log files. The DSL network wiring stays the same; only the source
and analyzers change.

**Classical signal processing** — sharpness (Laplacian variance), edge
detection (Sobel operator), and brightness analysis are the foundation of
computer vision. Neural networks are built on top of these primitives.

**Feature vectors** — each photo produces a 3-number vector
`[sharpness_score, exposure_score, composition_score]`. This is the same
concept used in machine learning: a structured numerical representation
of an input. In Module 08, this vector becomes the state input to a
reinforcement learning agent that learns your personal photo preferences.

**Stateless analyzers** — all three analyzers in this module are stateless.
Each photo is analyzed independently. Compare to Module 06's
`LearningCurveAnalyzer`, which was stateful (it accumulated history across
checkpoints). Stateless transforms are simpler, easier to test, and
naturally parallelizable.

---

## Next Module

Module 08 closes the loop: a human labels photos as "keep" or "delete",
and those labels become the reward signal for an RL agent that learns your
personal aesthetic. The 3-number quality vector from Module 07 becomes
the RL agent's state. You will have built a simplified version of the same
training technique used to align large language models — reinforcement
learning from human feedback (RLHF).
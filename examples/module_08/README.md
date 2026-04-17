# Module 08: Photo Quality Scorer — Process Edition

*The same app as Module 07. One word changed. True CPU parallelism.*

---

## What You'll Build

A photo quality scorer that reads images from a folder, runs three analyses
in parallel — sharpness, exposure, and composition — merges the results, and
produces a verdict for each photo: `post_it`, `maybe`, or `delete`.

```
                    ┌→ sharpness_analyzer  ──┐
                    │                        │
images ─────────────┼→ exposure_analyzer   ──┼──→ merge_synch ──→ dashboard
                    │                        │                └──→ archive
                    └→ composition_analyzer ─┘
```

This is identical to Module 07. The only change is one word in the last line
of the file:

```python
# Module 07
g.run_network(timeout=120)     # each analyzer runs in its own thread

# Module 08
g.process_network(timeout=120) # each analyzer runs in its own process
```

That single word — `process_network` instead of `run_network` — is the
entire lesson.

---

## Part 1: Run It (5 minutes)

**Step 1 — Get demo images (run once):**

```bash
python3 examples/module_07/download_demo_images.py
```

**Step 2 — Run Module 08:**

```bash
python3 -m examples.module_08.app
```

You'll see output like:

```
Module 08: Photo scorer running with processes (not threads).
Each analyzer runs in its own OS process — true CPU parallelism.

📸 Photo Quality Dashboard
──────────────────────────────────────────────────────
  beach_sunset.jpg        score: 0.782  ✅ post_it
  city_night.jpg          score: 0.341  🤔 maybe
  blurry_cat.jpg          score: 0.187  🗑  delete
  mountain_lake.jpg       score: 0.651  ✅ post_it
  ...
──────────────────────────────────────────────────────
Results saved to photo_scores_m08.jsonl
```

**Step 3 — Compare with Module 07:**

Run Module 07 right after:

```bash
python3 -m examples.module_07.app
```

Look at two things: the results are identical, and the timing may differ.
The DSL produced the same output regardless of whether threads or processes
were used. You didn't change any of your own code.

---

## Part 2: Understand It (20 minutes)

### The one-word difference

Here is the complete diff between `module_07/app.py` and `module_08/app.py`.
Every single line is identical except the last one:

```python
# module_07/app.py  ← identical in every respect
g.run_network(timeout=120)

# module_08/app.py  ← one word changed
g.process_network(timeout=120)
```

That is the entire difference. Open both files side by side and confirm it
for yourself.

### What threads do (Module 07)

When you call `g.run_network()`, DisSysLab starts one **thread** per node.
Threads share the same Python interpreter — the same process, the same memory,
the same CPU. Python has a rule called the GIL (Global Interpreter Lock) that
only lets one thread run Python bytecode at a time. For I/O-heavy work (reading
files, waiting for network responses) threads are fine. For CPU-heavy work like
image analysis, threads can only run one at a time even on a multicore machine.

```
Module 07 — threads share one Python interpreter
┌─────────────────────────────────────────────┐
│ Python process                              │
│                                             │
│  Thread A: SharpnessAnalyzer ←─ GIL ──┐   │
│  Thread B: ExposureAnalyzer            │   │ ← only ONE runs at a time
│  Thread C: CompositionAnalyzer ←───────┘   │
└─────────────────────────────────────────────┘
```

### What processes do (Module 08)

When you call `g.process_network()`, DisSysLab starts one **OS process** per
node. Each process has its own Python interpreter, its own memory, and its own
GIL. Three processes on a three-core machine genuinely run at exactly the same
moment.

```
Module 08 — processes each have their own interpreter
┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐
│ Process A          │  │ Process B          │  │ Process C          │
│ SharpnessAnalyzer  │  │ ExposureAnalyzer   │  │ CompositionAnalyzer│
│ (own GIL)          │  │ (own GIL)          │  │ (own GIL)          │
└────────────────────┘  └────────────────────┘  └────────────────────┘
       ↑                        ↑                        ↑
  CPU core 1              CPU core 2              CPU core 3
```

### Why does the application code stay the same?

Because the DSL separates **what your nodes do** from **how they are
executed**. Your Python functions (`sharpness_an.run`, `exposure_an.run`,
`composition_an.run`) are ordinary Python. They don't know or care whether
they're running inside a thread or a process. The framework handles the
mechanics — starting threads or processes, routing messages between them,
shutting everything down cleanly. You write the logic; the DSL chooses the
execution engine.

```python
# Your code — completely unchanged between M07 and M08
sharpness_node   = Transform(fn=sharpness_an.run,   name="sharpness")
exposure_node    = Transform(fn=exposure_an.run,     name="exposure")
composition_node = Transform(fn=composition_an.run,  name="composition")

g = network([
    (image_source,     sharpness_node),
    (image_source,     exposure_node),
    (image_source,     composition_node),
    (sharpness_node,   merge.in_0),
    (exposure_node,    merge.in_1),
    (composition_node, merge.in_2),
    (merge, dashboard_sink),
    (merge, archive_sink),
])

# Module 07:  g.run_network(timeout=120)
# Module 08:  g.process_network(timeout=120)   ← the only change
```

### When to use each

| | `run_network()` — threads | `process_network()` — processes |
|---|---|---|
| **Best for** | I/O-bound work: network, files, APIs | CPU-bound work: image processing, numpy, ML |
| **Parallelism** | Limited by GIL | True parallelism across CPU cores |
| **Memory** | Shared — lightweight | Separate — uses more RAM |
| **Startup** | Instant | Slightly slower (process launch) |
| **Overhead** | Very low | Slightly higher |

For the photo scorer — which uses numpy and scipy — `process_network()` can
genuinely run all three analyzers at the same time on separate CPU cores.

### The GIL: a quick intuition

Imagine three chefs (threads) in one kitchen. They share one stove (the GIL).
Only one can cook at a time; when one is waiting for water to boil (I/O), others
can take a turn. If all three are actively chopping at the same time (CPU-heavy),
they're still rotating through the stove one at a time.

Now give each chef their own kitchen (processes). No sharing — all three cook
simultaneously. It costs more (more kitchens, more setup), but the parallelism
is real.

---

## Part 3: Make It Yours (15 minutes)

### Experiment 1: Confirm the results are identical

Run both versions and compare the output files:

```bash
python3 -m examples.module_07.app   # produces photo_scores_m07.jsonl
python3 -m examples.module_08.app   # produces photo_scores_m08.jsonl
diff photo_scores_m07.jsonl photo_scores_m08.jsonl
```

If the files are identical (or very close), you've confirmed that the DSL
gives you the same results regardless of execution mode.

### Experiment 2: Add a fourth analyzer with processes

Extend the photo scorer with a fourth parallel analyzer — for example, a color
richness scorer. Ask Claude:

> "Add a ColorAnalyzer to the Module 08 app. It should score how colorful an
> image is (0.0 = grayscale, 1.0 = very colorful). Wire it in parallel with
> the other three analyzers and include color_score in the final verdict."

Notice that you add a fourth node, extend `MergeSynch` to `num_inputs=4`, and
keep `g.process_network()`. The network grows; the execution call stays the same.

### Experiment 3: Switch a CPU-heavy transform to use processes

Take any network from an earlier module that does heavy text processing and
replace `g.run_network()` with `g.process_network()`. Did it work? Did the
results change? Did it run faster?

---

## Part 4: Real Image Processing (when you want it)

Module 08 already uses real image processing via Pillow, numpy, and scipy —
no mock components for the analyzers. The only thing the demo setup does is
download a small set of sample images for you.

To use your own photos:

```python
# In app.py, change this line:
imgs = ImageFolderSource(folder="examples/module_07/demo_images")

# To point at your own folder:
imgs = ImageFolderSource(folder="/path/to/your/photos")
```

Everything else stays the same.

---

## Key Concepts

### `run_network()` vs `process_network()` — the summary

```python
g.run_network()      # threads  — shared interpreter, limited by GIL
g.process_network()  # processes — separate interpreters, true parallelism
```

Same network definition. Same node functions. Same results. Different execution
engine. The DSL hides the difference.

### MergeSynch waits for all parallel results

The merger collects one result from each analyzer for the same image before
producing output. Even if one process finishes ahead of the others, the merged
result waits until all three have arrived. Order is preserved: `in_0` is always
sharpness, `in_1` is always exposure, `in_2` is always composition.

```python
merge = MergeSynch(num_inputs=3, name="merge_synch")

# The three parallel paths feed into numbered ports
(sharpness_node,   merge.in_0),
(exposure_node,    merge.in_1),
(composition_node, merge.in_2),
```

### The verdict formula

```python
quality_score = 0.4 * sharpness_score
              + 0.4 * exposure_score
              + 0.2 * composition_score

verdict = "post_it"  if quality_score > 0.50
        = "maybe"    if quality_score > 0.30
        = "delete"   otherwise
```

Sharpness and exposure each carry 40% of the weight. Composition is 20%.
The weights are in `archive_merged` in `app.py` — change them to match your
own aesthetic judgment.

---

## Homework

**Assignment 1:** Start from the Module 07 app. Make the single-word change to
`process_network()`. Confirm it still runs and produces the same results. Write
one sentence explaining why the results are identical even though the execution
mechanism changed.

**Assignment 2:** The three image analyzers score photos by sharpness, exposure,
and composition. Which of these three would benefit most from running in a
separate CPU process versus a thread? Write a brief justification for your answer.

**Assignment 3:** Design a network for a problem you care about where multiple
CPU-heavy analyses run in parallel on the same input. It doesn't have to be
photos — it could be audio files, documents, numerical datasets, anything.
Draw the network topology (ASCII art is fine), label each node, and state
whether you'd use `run_network()` or `process_network()` and why.

---

## Files in This Module

```
examples/module_08/
├── README.md          ← you are here
├── app.py             ← the complete application
└── test_module_08.py  ← tests (Layers 1–4)
```

The image analyzers and dashboard are shared with Module 07:

```
dissyslab/components/
├── sources/
│   └── image_folder_source.py
├── transformers/
│   ├── sharpness_analyzer.py
│   ├── exposure_analyzer.py
│   └── composition_analyzer.py
└── sinks/
    ├── photo_dashboard.py
    └── jsonl_recorder.py
```

---

## Running the Tests

```bash
pytest examples/module_08/test_module_08.py -v
```

Tests are organized in four layers:

**Layer 1 — Components:** Each analyzer works in isolation on a synthetic
image. No network, no demo images required.

**Layer 2 — Transform functions:** The `archive_merged` scoring and verdict
logic is correct (weights, clamping, thresholds).

**Layer 3 — Full network:** `process_network()` runs without error, produces
results, and all scores are in [0.0, 1.0]. *(Requires demo images.)*

**Layer 4 — Equivalence:** `process_network()` and `run_network()` produce the
same number of results and the same verdicts for the same images. This directly
tests the key lesson of Module 08. *(Requires demo images.)*

---

## Next Steps

**Module 09** introduces real-world data connectors — live sources like BlueSky,
email inboxes, and calendar events. You'll use everything you've learned here
to build networks that process live streaming data rather than files.

**Want to go further with parallel processing?** The DSL's `process_network()`
works with any combination of node types: Source, Transform, Sink, MergeSynch,
Split, Broadcast. Any network you can run with threads can run with processes
by changing one word.

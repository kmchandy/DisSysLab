# backyard_birds

Identify the bird species in a folder of audio recordings.

This office reads `.mp3` clips from `./samples/`, runs each one
through [BirdNET](https://github.com/kahst/BirdNET-Analyzer), and
emits one message per detected species. The detections appear in
the terminal and are recorded to `bird_detections.jsonl` for later
analysis.

It is the smallest gallery example of an **ML-model agent** — an
agent in a DisSysLab office that is not an LLM but a classical
classifier. No tokens, no API key, no temperature.

## What it does

```
audio_folder  →  Alex (bird_classifier)  →  intelligence_display
                                         →  bird_detections.jsonl
```

Each `.mp3` in `./samples/` becomes one input to Alex. Alex calls
BirdNET on the clip, then emits one structured message per
detected species above the confidence threshold:

```json
{
  "source": "backyard_birds",
  "title": "Carolina Wren",
  "species": "Carolina Wren",
  "scientific_name": "Thryothorus ludovicianus",
  "confidence": 0.87,
  "start_time": 12.0,
  "end_time": 15.0,
  "file": "morning_chorus.mp3",
  "significance": "HIGH"
}
```

## Setup

```bash
pip install birdnetlib librosa resampy
```

The first analysis downloads the BirdNET model (~50 MB) to a cache
directory in your home folder. Subsequent runs are offline.

## Audio clips

The `samples/` folder is empty by default. Drop one or more `.mp3`
clips into it and rerun:

```bash
dsl run backyard_birds
```

Sources for free Creative-Commons recordings:

- [xeno-canto.org](https://www.xeno-canto.org/) — community bird-call
  archive, browse by species or region. Most recordings are CC-BY
  or CC-BY-NC.
- [Macaulay Library](https://www.macaulaylibrary.org/) — Cornell Lab
  of Ornithology. Use the search filters for licensed recordings.
- Your own phone recordings of the birds outside your window.

Five 30-second clips are enough to demonstrate the pipeline.

## Output

The terminal shows one card per detection, colour-tinted by
confidence. The `.jsonl` file accumulates every detection across
runs, so you can:

```bash
# Most-detected species this week
cat bird_detections.jsonl \
  | jq -r '.species' \
  | sort | uniq -c | sort -rn | head
```

## Tuning

Edit `office.md` and rerun:

```
Agents:
Alex is a bird_classifier(min_confidence=0.7).
```

Higher `min_confidence` cuts false positives at the cost of missing
quieter calls. `0.5` is permissive; `0.7` is conservative; `0.85`
is "I want only the unambiguous ones."

To process more files per run:

```
Sources: audio_folder(path="./samples/", glob="*.mp3", max_files=50)
```

## What this demonstrates

| DisSysLab feature | Where it shows up |
|---|---|
| Source primitive for streaming files | `audio_folder` in `office.md` |
| ML-model agent (no LLM) | Alex is a `bird_classifier` |
| Fan-out to multiple sinks | Alex's `out` goes to display *and* jsonl |
| Pure-Python role with lazy dependency | `roles/bird_classifier.py` |

The same office shape — `audio_folder → classifier → sinks` —
works for any clip-level audio model. Swap the role for a speech
transcriber, a music-genre classifier, or a loudness meter and the
rest of the office is unchanged.

## License

MIT. BirdNET-Analyzer is CC-BY-NC-SA-4.0; consult the project for
permitted uses.

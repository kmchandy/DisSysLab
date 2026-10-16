# backyard_birds

Which birds are singing in these recordings? Each audio clip in
`samples/` goes to Alex, who runs [BirdNET](https://github.com/kahst/BirdNET-Analyzer)
on it and sends one message per species heard -- or one "No birds in
..." message, so no clip disappears silently.

    clips -> Alex -> intelligence_display, jsonl_recorder

Alex is not a language model. It is a classifier: no tokens, no API key,
and the same clip always gives the same answer. The office does not
care: an agent is anything that takes a message and sends messages.

## Setup

    pip install birdnetlib librosa resampy

`bird_classifier.py` lists these under `needs:`. If one is missing, the
run stops before it starts and names the `pip install` line. The first
run downloads the BirdNET model (about 50 MB).

Put some `.mp3` clips in `samples/` (free Creative Commons recordings:
[xeno-canto.org](https://www.xeno-canto.org/), or your phone), then

    dsl run backyard_birds

## Things to try

- `min_confidence=0.7` on Alex's line: fewer false positives, more
  missed quiet calls.
- Read `step` in `roles/bird_classifier.py`. It is the whole of Alex's
  logic apart from BirdNET, and you can test it with a list of made-up
  detections.
- Swap the role for another clip-level model (a speech transcriber, a
  loudness meter); the rest of the office is unchanged.

BirdNET-Analyzer is CC-BY-NC-SA-4.0; consult the project for permitted uses.

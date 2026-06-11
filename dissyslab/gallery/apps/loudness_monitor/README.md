# loudness_monitor

Watch an audio stream; emit a card when the room gets loud.

This is the smallest streaming office in the gallery and the
cleanest illustration of the **sense → detect → respond** arc. No
LLM. No ML. Two short Python roles and four English wirings.
Played silence and you see nothing; played a loud sound and you
see a card.

## What it does

```
audio_clip  →  Alex (rms_meter)  →  Bryn (threshold_detector)  →  intelligence_display
```

Five specialist agents:

- `audio_clip` streams 200 ms chunks of an audio file
- **Alex** computes the chunk's loudness in dBFS (RMS → dB)
- **Bryn** watches the dB stream and emits **only** at the rising edge above −30 dBFS, with 400 ms debounce before re-arming
- `intelligence_display` shows each event as a card in your terminal

Most chunks produce no downstream message. The display is silent
until something happens. That silence is the demonstration: this
is not a chain that fires on every input — it is an office that
*reacts to changes*.

## Run it

The office ships with a 60-second synthetic thunderstorm clip
(`samples/thunderstorm.mp3`) so the demo works on a fresh clone
with no audio equipment. One dependency:

```bash
pip install librosa numpy
```

`librosa` installs as a pure-Python wheel on macOS and Linux — no
brew, no portaudio.

Then:

```bash
dsl run loudness_monitor
```

You should see **six "Loud event" cards** roll into the terminal
over about a minute, one per thunder clap. The loudest clap is
tagged `HIGH` significance; the rest are `MEDIUM`.

## Listen along (optional)

Open a second terminal at the same time as `dsl run` and play the
clip — you'll hear the thunder claps that are producing the cards
on the first terminal:

```bash
# macOS
afplay dissyslab/gallery/apps/loudness_monitor/samples/thunderstorm.mp3

# Linux
aplay dissyslab/gallery/apps/loudness_monitor/samples/thunderstorm.mp3
```

The sense-and-respond arc becomes obvious when you can both *hear*
the input and *see* the response.

## Use your own microphone instead

The pipeline is structured so the source is the only piece that
knows about audio. Swap the source line in `office.md` to use your
laptop's microphone, and the rest of the office is unchanged:

```
Sources: audio_mic(chunk_ms=200, max_seconds=60)
...
Connections:
audio_mic's destination is Alex.
...
```

(The connection line that references `audio_clip` must also be
updated to `audio_mic` — sources are referenced by name everywhere
they appear.)

`audio_mic` needs `sounddevice`, which links against PortAudio:

```bash
# macOS
brew install portaudio
pip install sounddevice numpy

# Linux
sudo apt install libportaudio2     # Ubuntu/Debian
pip install sounddevice numpy
```

First-run permissions: macOS will prompt the terminal to access the
microphone the first time `dsl run loudness_monitor` is invoked.
Grant permission once. The office captures for 60 seconds by
default (`max_seconds=60`), then exits cleanly. Clap, snap, slam
a door, talk to the computer — anything above conversational
volume should trigger a card.

This is the **mix-and-match property of specialist agents in
action**: same downstream agents, different source, same contract
on the messages flowing between them.

## Regenerating the sample audio

The thunderstorm clip is reproducible. `samples/make_thunder.py`
synthesises it from scratch in a few seconds:

```bash
cd dissyslab/gallery/apps/loudness_monitor/samples
python make_thunder.py
```

The script uses a seeded random number generator, so the bytes
are identical on every run. Read the script if you want to see
how the clip is built (low-pass-filtered noise for the rumble,
band-pass for the crack, ADSR envelope) — it's a worked example
of a Python role's worth of DSP, separate from the office.

## Tuning the threshold

Edit `office.md` and rerun:

```
Agents:
Bryn is a threshold_detector(db_threshold=-25, debounce_ms=600).
```

- `db_threshold` — higher (closer to 0) means louder to fire.
  −30 dBFS is "anything notable in a quiet room." −20 dBFS is
  "noticeable bang." −10 dBFS approaches digital clipping.
- `debounce_ms` — how long the level must stay below the threshold
  before the detector re-arms. 400 ms is responsive; 1000 ms is
  conservative.

Run length on the file source is set by the clip length; on
`audio_mic`, by the `max_seconds` parameter. Drop `max_seconds`
for indefinite operation.

## How these Python roles were written

The two Python roles in `roles/` were written by Claude, using
short prompts that gave the input/output contract and pointed at
an existing DSL role as a pattern reference. The prompts are
reproduced below so you can adapt them to your own roles.

### Prompt for `rms_meter.py`

> *I am writing a DisSysLab Python role. The file goes in
> `roles/rms_meter.py` and is loaded by the framework via
> `AgentRoleEntry`. Use
> `dissyslab/gallery/apps/debate/roles/gate.py` as the pattern for
> the boilerplate (subclass `Agent`, declare `inports=["in_"]` and
> `outports=["out_"]`, register at module level with
> `AgentRoleEntry`).*
>
> *The agent receives one message per audio chunk on inport `in_`.
> Each message has shape*
>
> >     {"samples": np.ndarray, "sample_rate": int,
> >      "timestamp": float, "chunk_index": int}
>
> *For each message, compute the RMS (root mean square) of the
> samples and convert to dBFS using
> `db = 20 * log10(max(rms, 1e-10))`. Emit one message on outport
> `out_` with shape*
>
> >     {"db": float, "rms": float,
> >      "timestamp": float, "chunk_index": int}
>
> *No LLM, no API calls — pure arithmetic. Lazy-import numpy so
> `dsl build` succeeds even when numpy is not installed.*

### Prompt for `threshold_detector.py`

> *Another DisSysLab Python role, same boilerplate. The agent
> watches a dB stream from `rms_meter` and emits messages only
> at the rising edge above a threshold.*
>
> *Constructor parameters: `db_threshold=-30.0`, `debounce_ms=400.0`.*
>
> *Semantics: keep an `armed` flag. When `armed` is True and an
> inbound message has `db >= db_threshold`, fire one event message
> and set `armed=False`. After firing, the level must stay below
> threshold for `debounce_ms` continuously before `armed` returns
> to True. Any above-threshold reading during the debounce period
> resets the debounce timer.*
>
> *The output message has shape*
>
> >     {"event": "loud", "peak_db": float,
> >      "started_at": <iso string>, "title": "Loud event",
> >      "text": "Detected at <db> dBFS.",
> >      "significance": "HIGH"/"MEDIUM"/"LOW",
> >      "source": "loudness_monitor"}
>
> *Bucket significance by peak_db: >= -15 → HIGH, >= -22 → MEDIUM,
> else LOW.*

Both prompts are short because the roles themselves are small. For
larger roles the same pattern works — describe the input contract,
the output contract, the behaviour, and point at an existing role
file as the boilerplate template.

## What this demonstrates

| DSL feature | Where it shows up |
|---|---|
| Streaming source primitive | `audio_clip` chunks audio at fixed cadence |
| Source-swap by contract | `audio_mic` plugs into the same pipeline unchanged |
| Pure-Python specialist agent | `rms_meter` is arithmetic, no LLM |
| Edge-triggered event detector | `threshold_detector` emits only when something happens |
| Reactive sink | `intelligence_display` renders the response |
| LLM-as-code-generator | both Python roles were written by Claude from the prompts above |

## License

MIT. `sounddevice` (PortAudio binding) and `librosa` carry their
own licenses; consult their projects. The synthetic
`thunderstorm.mp3` is generated by `make_thunder.py` and is
released under the same MIT license as the rest of the framework.

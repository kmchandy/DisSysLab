# recovery_demo

Demonstrates **distributed snapshot checkpoint-recovery** — the
Chandy-Lamport algorithm — on a small Monte Carlo office that
estimates π. This is the smallest office in the gallery that
exercises every piece of DisSysLab's checkpoint-recovery
machinery introduced in v1.6.

## What it does

```
csv_points_source  →  Alex (inside_classifier)  →  Pi (pi_combiner)  →  display
                  ↘  Bob  (outside_classifier) ↗
```

Five specialist agents:

- `csv_points_source` reads `(x, y)` pairs from `samples/points.txt` one per emission
- The compiler auto-inserts a **Broadcast** in front of the two classifiers because the source's outport fans out to two destinations
- **Alex** (`inside_classifier`) counts points with `x² + y² < 1`
- **Bob** (`outside_classifier`) counts points with `x² + y² ≥ 1`
- The compiler auto-inserts a **MergeAsynch** in front of Pi because two outports fan into one inport
- **Pi** (`pi_combiner`) tracks the running inside/outside counts and emits `π ≈ 4 · inside / (inside + outside)` after every received message
- `intelligence_display` shows the running estimate as a card stream

Three agents have state, two of them stateless (the auto-inserted
Broadcast and MergeAsynch). Each stateful agent overrides
`save_state` / `load_state`:

| Agent | State saved | When |
|---|---|---|
| `csv_points_source` (via Source wrapper) | `{"cursor": int}` | snapshot |
| Alex (`inside_classifier`) | `{"count": int}` | snapshot |
| Bob (`outside_classifier`) | `{"count": int}` | snapshot |
| Pi (`pi_combiner`) | `{"inside": int, "outside": int}` | snapshot |

## Setup

```bash
cd dissyslab/gallery/apps/recovery_demo/samples
python make_points.py            # generates points.txt (~10000 lines, ~150 KB)
cd ..
```

Pure standard library — no `pip install` required beyond what
DisSysLab already needs.

## Run the demo without checkpointing

```bash
dsl run recovery_demo
```

The office reads all 10 000 points (~50 seconds at the default
`interval=0.005`) and you watch the π estimate converge toward
3.14159 in real time.

## Run the demo with periodic checkpointing

```bash
dsl run recovery_demo --snapshot-interval 5
```

Every 5 seconds the OS manager initiates a distributed snapshot.
Snapshots land under `snapshots/checkpoints/<N:06d>/` containing:

- `manifest.json` — office name, snapshot number, timestamp, agent list
- `agents/<agent_name>.pkl` — each agent's saved state
- `channels/<dst>__<port>.pkl` — in-flight messages on each channel at the cut

After ~30 seconds press **Ctrl-C**. A few snapshots will have been written.

## Resume from a snapshot

```bash
dsl run recovery_demo --resume latest --snapshot-interval 5
```

The office reconstructs the agents, loads each agent's state from
disk, refills the channel queues with the messages that were
in-flight at the cut, and continues. The π estimate picks up from
the saved counts rather than restarting at zero — visible
confirmation that the four-way recovery handshake worked.

Specific snapshot numbers also work: `--resume 3` resumes from
`snapshots/checkpoints/000003/`.

## What this demonstrates

| Concept | Where it shows up |
|---|---|
| **Distributed snapshot algorithm** | The framework's `OsAgent` broadcasts `_Checkpoint(N)` to source input queues; the marker propagates via upstream-forwarding through the data graph. |
| **Per-agent `save_state` / `load_state`** | The three stateful roles in `roles/` each override the two methods in five lines. |
| **Per-edge channel-state recording** | The Monte Carlo flow has fan-out and fan-in; each edge's in-flight messages are captured per-snapshot and replayed on resume. |
| **MergeAsynch under concurrency** | Pi's single inport is fed by two outports; the compiler auto-inserts a multi-worker MergeAsynch. The snapshot lock added in v1.6 keeps the protocol correct under thread races. |
| **Four-way recovery handshake** | `_PrepareRecover` → `_RecoverReady` → `_StartRecover` synchronizes every agent before any of them produces post-recovery output. |
| **Source / sink boundary protocol** | `csv_points_source` records `ptr(N)` at each snapshot and `ptr_to_now` at each recover; on replay it re-reads the file from `cursor` and the office sees no gap. |

## Algorithm reference

The algorithm's specification lives in
[`dev/CHECKPOINT_RESUME_ALGORITHM.md`](../../../dev/CHECKPOINT_RESUME_ALGORITHM.md).
Read that document and then read the three role files
alongside `dissyslab/core.py`'s `Agent._handle_checkpoint` /
`_handle_prepare_recover` / `_handle_start_recover` and
`dissyslab/os_agent.py`'s `_initiate_snapshot` /
`initiate_recovery` to see the algorithm and its implementation
side-by-side. The implementation is ~500 lines of Python that
maps cleanly onto the pseudocode in the algorithm document.

## License

MIT.

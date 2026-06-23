# Changelog

All notable changes to DisSysLab are documented here. The format
loosely follows [Keep a Changelog](https://keepachangelog.com/);
versions follow [SemVer](https://semver.org/).


## [1.6.1] — 2026-06-23

### Fixed

- `gallery/apps/debate/roles/gate.py`: when the problem bank is
  exhausted, the gate role now `continue`s in its `recv()` loop
  instead of returning. Returning voluntarily killed the agent's
  thread before `os_agent` could finish polling it; termination
  detection stayed blocked indefinitely. Also dropped the now-
  unnecessary `{"end_of_stream": True}` sentinel emission, which
  was being mis-processed as a real problem by downstream
  panellists. Net effect: the gallery debate office terminates
  cleanly when its bank is exhausted.
  
## [Unreleased] — will become 1.6.0

### Added

- **Distributed snapshot checkpoint-recovery** for offices —
  implementation of the Chandy-Lamport (1985) distributed snapshot
  algorithm, adapted for DSL's office-shaped systems. Algorithm
  authored by K. Mani Chandy with implementation help from Claude.
  Specification in
  [`docs/algorithms/CHECKPOINT_RESUME.md`](docs/algorithms/CHECKPOINT_RESUME.md).
- New `dsl run` flags:
  - `--snapshot-interval <seconds>` — initiate a distributed
    snapshot every N seconds while running. Snapshots persist
    under `<office_dir>/snapshots/checkpoints/<N>/`.
  - `--resume <N|latest>` — restart from a saved snapshot. Each
    agent reloads its checkpoint state; each channel's in-flight
    messages are replayed into its inport queue; the office
    continues from the consistent cut.
- New gallery office: **`recovery_demo`** — a Monte Carlo π
  estimator that demonstrates the protocol end-to-end. Three
  stateful agents (Alex, Bob, Pi) with auto-inserted Broadcast
  and MergeAsynch. Each stateful agent overrides `save_state` /
  `load_state` in five lines.
- New framework primitives:
  - `dissyslab/snapshot.py` — on-disk persistence layer
    (manifest.json + per-agent pickles + per-channel pickles).
  - `dissyslab/components/sources/csv_points_source.py` — a
    checkpoint-aware CSV source.
  - `Agent.save_state()` / `Agent.load_state()` — overridable
    hooks on the base class (defaults are no-ops, so existing
    agents work unchanged).
  - `Agent._poll_os()` — source-side polling for OS messages.
  - `Agent._snapshot_state` (enum: NORMAL, RECORDING,
    RECOVER_WAITING) — explicit state machine for the snapshot
    protocol.
  - 5 new `_OsMessage` subclasses (`_Checkpoint`, `_Reply`,
    `_PrepareRecover`, `_RecoverReady`, `_StartRecover`).

### Changed

- `Source.run()` polls for OS messages between iterations and
  blocks during `RECOVER_WAITING`. Backward compatible: when no
  snapshot is configured, `_poll_os` is a no-op.
- Generated `build/run.py` artifacts read three new environment
  variables (`DSL_SNAPSHOT_INTERVAL`, `DSL_RESUME`,
  `DSL_SNAPSHOT_DIR`) set by `dsl run` and configure the
  network's snapshot attributes before calling `run_network()`.
- `MergeAsynch.__init__` upgrades its inherited `_NO_LOCK`
  singleton to a real `threading.Lock` — the only multi-threaded
  agent in the framework needs real synchronisation on shared
  snapshot state.

### Documentation

- New `docs/algorithms/` directory; first occupant is the
  checkpoint-resume algorithm specification.
- README gains a *Current limitations* subsection naming what
  the framework does **not** do (multi-machine, scheduling,
  opt-in checkpointing, LLM non-determinism, no first-party
  web UI).
- README gallery table lists `recovery_demo` as the v1.6 demo
  office.

### Verified

- 417 unit tests pass (was 406; +9 new checkpoint tests + 2
  additions from the parameterised gallery-compiles test
  picking up `recovery_demo`).
- All 20 gallery offices build cleanly via `dsl build`.
- `dsl run periodic_brief` produces identical output to v1.5
  (backward compatibility).
- End-to-end `recovery_demo` with periodic snapshots: all four
  agents (plus auto-inserted Broadcast and MergeAsynch) appear
  in each snapshot's manifest; agent state correctly persisted.

### Out of scope for 1.6 (named honestly in `dev/POST_HN_BACKLOG.md`)

- Multi-machine snapshots
- Multi-process snapshots (`dsl run --processes`)
- Snapshot timeout / queue-failure detection
- Encrypted snapshots
- Schema evolution across snapshots

## [1.4.0] — pre-1.6 baseline

Tagged at commit `547827d`. Pre-checkpoint-recovery snapshot of
the framework — sense-and-respond positioning, gallery of audio
+ image + text apps, English office grammar with mix-and-match
per-agent LLM backends, library of specialist agents
(`confidence_filter`, English roles), `dsl new`, the office
microcourse. See git history between `547827d` and the v1.6
commit for the full set of changes since the last tagged
release.

A formal changelog for 1.5.x was never published as a release;
the work that would have been 1.5 — alpha contract refactor,
debate office, audio + image gallery apps, Nyasha's React
deployment pattern, specialist-agents README rewrite — is
folded into the 1.6 release notes above.

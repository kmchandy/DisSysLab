# dissyslab/snapshot.py
"""
On-disk layout for distributed snapshots (v1.6).

Single source of truth for the file layout, naming conventions,
and read/write helpers used by both the snapshot writer in
``os_agent.py`` and the recovery reader in ``core.py``'s
``Agent._load_checkpoint_from_disk``.

Layout:

    <snapshot_dir>/checkpoints/<N:06d>/
        manifest.json                       — office name, N, timestamp, agent list, edges
        agents/<agent_name>.pkl             — pickled state dict (from agent.save_state())
        channels/<dst_agent>__<dst_port>.pkl  — pickled list of in-flight messages

Naming convention for channel files: keyed by the destination
agent + destination port. Each edge in DSL's flattened graph
``(src_agent, src_port, dst_agent, dst_port)`` has exactly one
sender, so ``(dst, port)`` uniquely identifies the channel. When
``MergeAsynch`` is eliminated in v2.0 (see
``dev/POST_HN_BACKLOG.md``), the convention will gain a sender
prefix.

Agent names that contain ``::`` (DSL's flattened-path separator
for nested networks) are sanitized by ``safe_filename`` to
``__`` so they map cleanly to a single file.
"""

from __future__ import annotations

import json
import pickle
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple


# ── Naming helpers ───────────────────────────────────────────────────────

def safe_filename(name: str) -> str:
    """Sanitize a flattened agent name into a filesystem-safe filename.

    DSL's flattened agent names use ``::`` as a path separator
    (e.g. ``root::spam_filter``). Replace with double underscore.
    Also strip forward and back slashes for paranoia on weird
    platforms.
    """
    return name.replace("::", "__").replace("/", "_").replace("\\", "_")


def snapshot_root(snapshot_dir: Path, N: int) -> Path:
    """Return the directory that holds snapshot N's files."""
    return Path(snapshot_dir) / "checkpoints" / f"{N:06d}"


def agent_file_path(snapshot_dir: Path, N: int, agent_name: str) -> Path:
    """Return the path to one agent's state pickle for snapshot N."""
    return snapshot_root(snapshot_dir, N) / "agents" / f"{safe_filename(agent_name)}.pkl"


def channel_file_path(
    snapshot_dir: Path, N: int, dst_agent: str, dst_port: str
) -> Path:
    """Return the path to one edge's channel-state pickle for snapshot N."""
    return (
        snapshot_root(snapshot_dir, N)
        / "channels"
        / f"{safe_filename(dst_agent)}__{dst_port}.pkl"
    )


def manifest_path(snapshot_dir: Path, N: int) -> Path:
    """Return the path to snapshot N's manifest.json."""
    return snapshot_root(snapshot_dir, N) / "manifest.json"


# ── Snapshot writer ───────────────────────────────────────────────────────

def write_snapshot(
    snapshot_dir: Path,
    office_name: str,
    N: int,
    graph_connections: List[Tuple[str, str, str, str]],
    replies: Dict[str, Any],
) -> None:
    """Persist snapshot N to disk.

    Parameters
    ----------
    snapshot_dir : Path
        The office's checkpoint directory. ``checkpoints/<N:06d>/``
        will be created inside it.
    office_name : str
        The office's name; written to manifest.json for resume
        validation.
    N : int
        Snapshot number.
    graph_connections : list
        The flattened graph's edges; written to manifest.json so
        ``--resume`` can validate that the running office matches
        the snapshot.
    replies : dict
        Mapping from agent name to that agent's ``_Reply`` object,
        which carries ``state`` and ``channel_states``.
    """
    root = snapshot_root(snapshot_dir, N)
    agents_dir = root / "agents"
    channels_dir = root / "channels"
    agents_dir.mkdir(parents=True, exist_ok=True)
    channels_dir.mkdir(parents=True, exist_ok=True)

    # Per-agent state.
    for agent_name, reply in replies.items():
        with agent_file_path(snapshot_dir, N, agent_name).open("wb") as f:
            pickle.dump(reply.state, f)
        # Per-inport channel state.
        for inport, msgs in (reply.channel_states or {}).items():
            with channel_file_path(
                snapshot_dir, N, agent_name, inport
            ).open("wb") as f:
                pickle.dump(list(msgs), f)

    # Manifest.
    manifest = {
        "office":     office_name,
        "N":          N,
        "timestamp":  time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "agents":     sorted(replies.keys()),
        "edges":      [list(edge) for edge in graph_connections],
    }
    with manifest_path(snapshot_dir, N).open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


# ── Snapshot readers ──────────────────────────────────────────────────────

def read_manifest(snapshot_dir: Path, N: int) -> Dict[str, Any]:
    """Read and return snapshot N's manifest. Raises if missing."""
    with manifest_path(snapshot_dir, N).open("r", encoding="utf-8") as f:
        return json.load(f)


def load_agent_state(snapshot_dir: Path, N: int, agent_name: str) -> Any:
    """Return the saved state dict for one agent in snapshot N.

    Returns ``None`` if the agent file does not exist (e.g., the
    agent was added after the snapshot was taken — caller decides
    how to handle).
    """
    path = agent_file_path(snapshot_dir, N, agent_name)
    if not path.is_file():
        return None
    with path.open("rb") as f:
        return pickle.load(f)


def load_channel_state(
    snapshot_dir: Path, N: int, dst_agent: str, dst_port: str
) -> List[Any]:
    """Return the list of in-flight messages for one channel in
    snapshot N.

    Returns ``[]`` if the channel file does not exist (the channel
    had empty state at the cut, or did not exist in the snapshot).
    """
    path = channel_file_path(snapshot_dir, N, dst_agent, dst_port)
    if not path.is_file():
        return []
    with path.open("rb") as f:
        return list(pickle.load(f))


# ── Snapshot listing ──────────────────────────────────────────────────────

def list_snapshots(snapshot_dir: Path) -> List[int]:
    """Return the sorted list of snapshot numbers N present on disk.

    Returns an empty list if no snapshots have been written yet
    or if the directory does not exist.
    """
    checkpoints = Path(snapshot_dir) / "checkpoints"
    if not checkpoints.is_dir():
        return []
    out = []
    for entry in checkpoints.iterdir():
        if entry.is_dir() and entry.name.isdigit():
            out.append(int(entry.name))
    return sorted(out)


def latest_snapshot(snapshot_dir: Path) -> int | None:
    """Return the highest snapshot number on disk, or None."""
    snapshots = list_snapshots(snapshot_dir)
    return snapshots[-1] if snapshots else None

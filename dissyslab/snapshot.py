"""Alias: moved to :mod:`dissyslab.runtime.snapshot`."""

from dissyslab.runtime.snapshot import (
    agent_file_path,
    channel_file_path,
    latest_snapshot,
    list_snapshots,
    load_agent_state,
    load_channel_state,
    manifest_path,
    read_manifest,
    safe_filename,
    snapshot_root,
    write_snapshot,
)

__all__ = [
    "agent_file_path",
    "channel_file_path",
    "latest_snapshot",
    "list_snapshots",
    "load_agent_state",
    "load_channel_state",
    "manifest_path",
    "read_manifest",
    "safe_filename",
    "snapshot_root",
    "write_snapshot",
]

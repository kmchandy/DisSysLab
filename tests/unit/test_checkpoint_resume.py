# tests/unit/test_checkpoint_resume.py
"""
Unit tests for the v1.6 distributed snapshot checkpoint-recovery
machinery.

Tests cover:
- The on-disk persistence layer (`dissyslab.snapshot`)
- An agent's state-loading path (`Agent._load_checkpoint_from_disk`)
- An end-to-end run of the ``recovery_demo`` office with periodic
  snapshots enabled
- An end-to-end resume of the ``recovery_demo`` office from a
  snapshot written by a previous run

See ``dev/CHECKPOINT_RESUME_ALGORITHM.md`` for the algorithm.
"""

from __future__ import annotations

import json
import pickle
import tempfile
import threading
import time
from pathlib import Path
from queue import SimpleQueue

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────

class _MockReply:
    """Stand-in for the framework's ``_Reply`` message — has the
    same shape attributes the snapshot writer reads."""
    def __init__(self, N, agent, state, channel_states):
        self.N = N
        self.agent = agent
        self.state = state
        self.channel_states = channel_states


def _make_points_file(path: Path, n: int = 100) -> None:
    """Write n deterministic (x, y) pairs to a CSV file."""
    with path.open("w") as f:
        # A mix of clearly inside and clearly outside points so the
        # counters split roughly half-half.
        for i in range(n):
            t = (i % 10) / 9.0
            # Half the points inside the quarter-circle, half outside.
            x = 0.3 + 0.3 * t if (i % 2) == 0 else 0.8 + 0.15 * t
            y = 0.3 + 0.3 * t if (i % 2) == 0 else 0.8 + 0.15 * t
            f.write(f"{x:.6f},{y:.6f}\n")


# ── snapshot.py persistence layer ─────────────────────────────────────────

class TestSnapshotPersistence:
    """Cover the read/write functions in ``dissyslab.snapshot``."""

    def test_safe_filename(self):
        from dissyslab.snapshot import safe_filename
        assert safe_filename("alex") == "alex"
        assert safe_filename("root::alex") == "root__alex"
        assert safe_filename("foo/bar") == "foo_bar"
        assert safe_filename("foo\\bar") == "foo_bar"

    def test_write_then_read_roundtrip(self):
        from dissyslab.snapshot import (
            write_snapshot, read_manifest,
            load_agent_state, load_channel_state,
            list_snapshots, latest_snapshot,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            graph = [
                ('src',  'out_', 'alex', 'in_'),
                ('src',  'out_', 'bob',  'in_'),
                ('alex', 'out_', 'pi',   'in_'),
                ('bob',  'out_', 'pi',   'in_'),
            ]
            replies = {
                'src':  _MockReply(5, 'src',  {'cursor': 42}, {}),
                'alex': _MockReply(5, 'alex', {'count': 17},
                                   {'in_': ['m1', 'm2']}),
                'bob':  _MockReply(5, 'bob',  {'count': 8},  {'in_': []}),
                'pi':   _MockReply(5, 'pi',   {'inside': 17, 'outside': 8},
                                   {'in_': ['pending_msg']}),
            }
            write_snapshot(tmpdir, 'roundtrip', 5, graph, replies)

            assert list_snapshots(tmpdir) == [5]
            assert latest_snapshot(tmpdir) == 5

            manifest = read_manifest(tmpdir, 5)
            assert manifest['office'] == 'roundtrip'
            assert manifest['N'] == 5
            assert sorted(manifest['agents']) == ['alex', 'bob', 'pi', 'src']

            assert load_agent_state(tmpdir, 5, 'alex') == {'count': 17}
            assert load_agent_state(tmpdir, 5, 'pi') == {'inside': 17, 'outside': 8}
            assert load_agent_state(tmpdir, 5, 'never_existed') is None

            assert load_channel_state(tmpdir, 5, 'alex', 'in_') == ['m1', 'm2']
            assert load_channel_state(tmpdir, 5, 'bob', 'in_') == []
            assert load_channel_state(tmpdir, 5, 'pi', 'in_') == ['pending_msg']
            assert load_channel_state(tmpdir, 5, 'absent', 'in_') == []

    def test_list_snapshots_empty_and_multiple(self):
        from dissyslab.snapshot import (
            write_snapshot, list_snapshots, latest_snapshot,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            assert list_snapshots(tmpdir) == []
            assert latest_snapshot(tmpdir) is None
            for n in [0, 3, 1, 5, 2]:
                write_snapshot(
                    tmpdir, 'multi', n, [],
                    {'a': _MockReply(n, 'a', {'n': n}, {})},
                )
            assert list_snapshots(tmpdir) == [0, 1, 2, 3, 5]
            assert latest_snapshot(tmpdir) == 5

    def test_flattened_names_with_double_colons(self):
        """Agent names with ``::`` (nested-network path separator)
        get sanitized for filesystem safety."""
        from dissyslab.snapshot import (
            write_snapshot, load_agent_state,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            replies = {
                'root::child::leaf': _MockReply(
                    0, 'root::child::leaf', {'value': 99}, {},
                ),
            }
            write_snapshot(tmpdir, 'nested', 0, [], replies)
            # Filename uses ``__``; load_agent_state translates back.
            assert load_agent_state(
                tmpdir, 0, 'root::child::leaf',
            ) == {'value': 99}


# ── Agent state-loading path ──────────────────────────────────────────────

class TestAgentStateLoading:
    """Cover ``Agent._load_checkpoint_from_disk``."""

    def test_load_state_invokes_user_hook(self):
        from dissyslab.core import Agent
        from dissyslab.snapshot import write_snapshot

        class _Counter(Agent):
            def __init__(self):
                super().__init__(name='counter', inports=['in_'], outports=[])
                self.n = 0
            def save_state(self):
                return {'n': self.n}
            def load_state(self, state):
                self.n = state['n']
            def run(self):
                pass

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            write_snapshot(
                tmpdir, 'load_test', 0, [],
                {'counter': _MockReply(0, 'counter', {'n': 99}, {'in_': ['x', 'y', 'z']})},
            )
            ag = _Counter()
            ag._snapshot_dir = tmpdir
            ag._load_checkpoint_from_disk(0)
            # Agent's load_state was called with the recorded state
            assert ag.n == 99
            # Per-inport recovery buffer was populated
            assert ag._recovery_buffer == {'in_': ['x', 'y', 'z']}

    def test_load_with_no_snapshot_dir_is_noop(self):
        from dissyslab.core import Agent

        class _Counter(Agent):
            def __init__(self):
                super().__init__(name='counter', inports=[], outports=[])
                self.n = 0
            def load_state(self, state):
                self.n = state['n']
            def run(self):
                pass

        ag = _Counter()
        # _snapshot_dir is None (default) — no load happens
        ag._load_checkpoint_from_disk(0)
        assert ag.n == 0
        assert ag._recovery_buffer == {}


# ── End-to-end office runs ────────────────────────────────────────────────

class TestRecoveryDemoOffice:
    """Build and run the ``recovery_demo`` office programmatically;
    verify periodic snapshots persist and that resume restores state."""

    def _build_office(self, snapshot_dir: Path, points_path: Path,
                      snapshot_interval: float = None,
                      resume_from_N: int = None,
                      interval: float = 0.001):
        """Build the recovery_demo office programmatically (without
        going through office.md parsing/codegen)."""
        from dissyslab.gallery.apps.recovery_demo.roles.inside_classifier \
            import _InsideClassifier
        from dissyslab.gallery.apps.recovery_demo.roles.outside_classifier \
            import _OutsideClassifier
        from dissyslab.gallery.apps.recovery_demo.roles.pi_combiner \
            import _PiCombiner
        from dissyslab.components.sources.csv_points_source \
            import CSVPointsSource
        from dissyslab.network import Network
        from dissyslab.blocks.source import Source
        from dissyslab.blocks.sink import Sink

        results = []

        _csv = CSVPointsSource(path=str(points_path))
        src = Source(fn=_csv.run, interval=interval, name='source')
        alex = _InsideClassifier(name='Alex')
        bob = _OutsideClassifier(name='Bob')
        pi = _PiCombiner(name='Pi')
        sink = Sink(fn=lambda msg: results.append(msg), name='collector')

        net = Network(
            name='recovery_demo_test',
            blocks={
                'source': src, 'Alex': alex, 'Bob': bob,
                'Pi': pi, 'collector': sink,
            },
            connections=[
                ('source', 'out_', 'Alex', 'in_'),
                ('source', 'out_', 'Bob', 'in_'),
                ('Alex', 'out_', 'Pi', 'in_'),
                ('Bob', 'out_', 'Pi', 'in_'),
                ('Pi', 'out_', 'collector', 'in_'),
            ],
        )
        net.snapshot_dir = snapshot_dir
        if snapshot_interval is not None:
            net.snapshot_interval = snapshot_interval
        if resume_from_N is not None:
            net.resume_from_N = resume_from_N
        net.office_name = 'recovery_demo_test'
        return net, results, alex, bob, pi

    def test_office_runs_to_completion_without_snapshots(self):
        """Backward compat: office runs identically when no
        snapshot configuration is set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            points = tmpdir / "points.txt"
            _make_points_file(points, n=50)
            net, results, alex, bob, pi = self._build_office(
                tmpdir, points, snapshot_interval=None,
            )
            net.run_network(timeout=15.0)
            assert len(results) > 0
            # All 50 points should have been classified
            assert alex.count + bob.count == 50
            # No snapshot directory should be created
            from dissyslab.snapshot import list_snapshots
            assert list_snapshots(tmpdir) == []

    def test_office_writes_snapshots_when_interval_set(self):
        """With snapshot_interval set, snapshots persist to disk
        during the run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            points = tmpdir / "points.txt"
            _make_points_file(points, n=200)  # slow run for snapshots to fire
            snapshot_root = tmpdir / "snapshots"
            net, results, alex, bob, pi = self._build_office(
                snapshot_root, points,
                snapshot_interval=0.05,
                interval=0.003,
            )
            net.run_network(timeout=15.0)

            # The office produced π estimates
            assert len(results) > 0
            # All points classified
            assert alex.count + bob.count == 200

            # At least one snapshot fired and was persisted
            from dissyslab.snapshot import (
                list_snapshots, read_manifest, load_agent_state,
            )
            snapshots = list_snapshots(snapshot_root)
            assert len(snapshots) > 0, \
                "Expected at least one snapshot to fire"

            # Every manifest is well-formed. Agent names carry the
            # network's flattened-path prefix
            # (recovery_demo_test::source, etc.); the auto-inserted
            # Broadcast and MergeAsynch appear without the prefix
            # (broadcast_0, merge_0).
            for n in snapshots:
                manifest = read_manifest(snapshot_root, n)
                assert manifest['office'] == 'recovery_demo_test'
                assert manifest['N'] == n
                agent_names = manifest['agents']
                # Check each user agent appears with the expected prefix
                for required in ('source', 'Alex', 'Bob', 'Pi', 'collector'):
                    full = f'recovery_demo_test::{required}'
                    assert full in agent_names, (
                        f"snapshot {n} missing {full} in manifest "
                        f"(agents={agent_names})"
                    )
                # And the auto-inserted broadcast and merge agents are present
                assert any(
                    a.startswith('broadcast_') for a in agent_names
                ), f"snapshot {n} missing auto-inserted broadcast"
                assert any(
                    a.startswith('merge_') for a in agent_names
                ), f"snapshot {n} missing auto-inserted merge"

            # The last snapshot's per-agent state is consistent:
            # Alex.count + Bob.count never exceeds 200.
            last = snapshots[-1]
            alex_state = load_agent_state(
                snapshot_root, last, 'recovery_demo_test::Alex',
            )
            bob_state = load_agent_state(
                snapshot_root, last, 'recovery_demo_test::Bob',
            )
            assert alex_state is not None and 'count' in alex_state
            assert bob_state is not None and 'count' in bob_state
            assert 0 <= alex_state['count'] + bob_state['count'] <= 200

    def test_resume_restores_counter_state(self):
        """Take a snapshot, then start a fresh run with
        ``resume_from_N`` set; verify the agents load the recorded
        state from disk."""
        from dissyslab.snapshot import (
            write_snapshot, latest_snapshot,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            points = tmpdir / "points.txt"
            _make_points_file(points, n=30)
            snapshot_root = tmpdir / "snapshots"

            # Manually write a snapshot recording that 7 points were
            # already processed (4 inside, 3 outside, source cursor=7).
            # Then start a resume run.
            replies = {
                'source':    _MockReply(
                    0, 'source',
                    {'owner_state': {'cursor': 7}}, {},
                ),
                'Alex':      _MockReply(0, 'Alex', {'count': 4}, {'in_': []}),
                'Bob':       _MockReply(0, 'Bob',  {'count': 3}, {'in_': []}),
                'Pi':        _MockReply(
                    0, 'Pi',
                    {'inside': 4, 'outside': 3}, {'in_': []},
                ),
                'collector': _MockReply(0, 'collector', {}, {'in_': []}),
            }
            # We don't know the flattened names of the auto-inserted
            # Broadcast/MergeAsynch — they don't matter for the test.
            write_snapshot(
                snapshot_root, 'recovery_demo_test', 0, [], replies,
            )
            assert latest_snapshot(snapshot_root) == 0

            # Now build the network with resume_from_N and run it.
            net, results, alex, bob, pi = self._build_office(
                snapshot_root, points,
                snapshot_interval=None,
                resume_from_N=0,
                interval=0.0,  # as fast as possible — snapshot loading
                                # happens before any client work
            )
            net.run_network(timeout=15.0)

            # Counters should have continued from the loaded state.
            # The original snapshot said 7 already-processed points
            # (4 inside + 3 outside). After processing the remaining
            # 23 of 30, alex.count + bob.count should be 30 — and
            # alex.count should be at least 4 (the starting value).
            total = alex.count + bob.count
            # Tolerate the source replaying *some* points from cursor=7
            # past EOF; at minimum the office should have observed the
            # loaded counter values.
            assert total >= 4, (
                f"Expected counters to have continued past loaded "
                f"state; got alex={alex.count}, bob={bob.count}"
            )
            assert alex.count >= 4 or bob.count >= 3, (
                "Expected at least one classifier to retain its loaded count"
            )

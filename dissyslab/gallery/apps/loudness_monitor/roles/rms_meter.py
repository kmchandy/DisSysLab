# dissyslab/gallery/apps/loudness_monitor/roles/rms_meter.py

"""
Alex — the rms_meter role.

Receives one audio chunk per message and emits the chunk's loudness
in dBFS (decibels relative to digital full-scale). Pure arithmetic.
No LLM, no API calls, deterministic.

Input message (from audio_mic / audio_clip / any chunked audio source)::

    {
        "samples":     np.ndarray of shape (chunk_size,),
        "sample_rate": int,
        "timestamp":   float,
        "chunk_index": int,
    }

Output message::

    {
        "db":          float,   # 20 * log10(rms), clipped at the floor
        "rms":         float,   # raw RMS amplitude in [0, ~1]
        "timestamp":   float,
        "chunk_index": int,
    }

dB is computed against an epsilon floor of 1e-10 so that completely
silent chunks emit a finite dB value (≈ -200) rather than -inf.
"""

from __future__ import annotations

import math

from dissyslab.core import Agent
from dissyslab.office.library import AgentRoleEntry


_EPSILON = 1e-10


class _RMSMeter(Agent):
    """Compute RMS + dBFS on each inbound audio chunk."""

    def __init__(self, name: str | None = None):
        super().__init__(
            name=name,
            inports=["in_"],
            outports=["out_"],
        )

    def run(self) -> None:
        # Lazy numpy — keeps dsl build cheap when numpy is absent
        import numpy as np
        while True:
            msg = self.recv("in_")
            if not isinstance(msg, dict):
                continue
            samples = msg.get("samples")
            if samples is None:
                continue
            arr = np.asarray(samples, dtype=float).flatten()
            if arr.size == 0:
                continue
            rms = float(np.sqrt(np.mean(arr * arr)))
            db = 20.0 * math.log10(max(rms, _EPSILON))
            self.send(
                {
                    "db":          db,
                    "rms":         rms,
                    "timestamp":   msg.get("timestamp"),
                    "chunk_index": msg.get("chunk_index"),
                },
                "out_",
            )


role = AgentRoleEntry(
    name="rms_meter",
    in_ports=("in_",),
    out_ports=("out",),
    factory=_RMSMeter,
)

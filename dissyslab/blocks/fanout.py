"""Moved to :mod:`dissyslab.runtime.plumbing`.

Kept so existing imports keep working until the restructuring removes
``dissyslab.blocks`` (restructure_plan.md, Phase 5).
"""

from dissyslab.runtime.plumbing import Broadcast

__all__ = ["Broadcast"]

# tests/unit/test_core.py
"""Tests for dsl.core module."""

import pytest
from queue import SimpleQueue

from dsl.builder import PortReference


class TestAgent:
    """Test Agent base class behavior via concrete block subclasses."""

    def test_agent_send_filters_none(self):
        """Agent.send() filters None messages."""
        from dsl.blocks import Transform

        transform = Transform(fn=lambda x: x, name="test")
        transform.out_q["out_"] = SimpleQueue()

        # Send None — should be filtered
        transform.send(None, "out_")
        assert transform.out_q["out_"].empty()

        # Send actual message — should go through
        transform.send(42, "out_")
        assert transform.out_q["out_"].get() == 42

    def test_agent_getattr_creates_portreference(self):
        """Agent.__getattr__ creates PortReference for valid ports."""
        from dsl.blocks import Source

        source = Source(fn=lambda: None, name="test")
        ref = source.out_

        assert isinstance(ref, PortReference)
        assert ref.agent is source
        assert ref.port_name == "out_"

    def test_agent_default_inport(self):
        """Agent with single inport has default_inport."""
        from dsl.blocks import Transform

        transform = Transform(fn=lambda x: x, name="test")
        assert transform.default_inport == "in_"

    def test_agent_default_outport(self):
        """Agent with single outport has default_outport."""
        from dsl.blocks import Source

        source = Source(fn=lambda: None, name="test")
        assert source.default_outport == "out_"

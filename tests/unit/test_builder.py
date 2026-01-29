"""Tests for dsl.builder module."""

import pytest

from dsl.builder import network, PortReference
from dsl.blocks import Source, Transform, Sink, Split


class TestPortReference:
    """Test PortReference class."""

    def test_portreference_creation(self):
        """PortReference stores agent and port name."""
        source = Source(fn=lambda: None, name="src")
        ref = PortReference(agent=source, port_name="out_")

        assert ref.agent is source
        assert ref.port_name == "out_"

    def test_portreference_str(self):
        """PortReference string uses dot notation."""
        source = Source(fn=lambda: None, name="src")
        ref = PortReference(agent=source, port_name="out_")

        assert str(ref) == "src.out_"

    def test_portreference_repr(self):
        """PortReference has readable repr."""
        source = Source(fn=lambda: None, name="src")
        ref = PortReference(agent=source, port_name="out_")

        assert "src" in repr(ref)
        assert "out_" in repr(ref)


class TestNetworkFunction:
    """Test network() builder function."""

    def test_network_simple_pipeline(self):
        """Build simple source → sink pipeline."""
        source = Source(fn=lambda: None, name="src")
        sink = Sink(fn=print, name="sink")

        g = network([
            (source, sink)
        ])

        assert "src" in g.blocks
        assert "sink" in g.blocks
        assert len(g.connections) == 1
        assert g.connections[0] == ("src", "out_", "sink", "in_")

    def test_network_explicit_ports(self):
        """Use explicit port syntax with PortReference."""
        source = Source(fn=lambda: None, name="src")
        transform = Transform(fn=lambda x: x, name="trans")

        g = network([
            (source.out_, transform.in_)
        ])

        assert g.connections == [("src", "out_", "trans", "in_")]

    def test_network_mixed_syntax(self):
        """Mix default and explicit port syntax."""
        source = Source(fn=lambda: None, name="src")
        split = Split(fn=lambda x: [x, None], num_outputs=2, name="split")
        sink = Sink(fn=print, name="sink")

        g = network([
            (source, split),              # Both defaults
            (split.out_0, sink)           # Explicit from, default to
        ])

        assert g.connections[0] == ("src", "out_", "split", "in_")
        assert g.connections[1] == ("split", "out_0", "sink", "in_")

    def test_network_duplicate_name_error(self):
        """Error on duplicate agent names."""
        src_a = Source(fn=lambda: None, name="src")
        src_b = Source(fn=lambda: None, name="src")  # Same name!
        sink = Sink(fn=print, name="sink")

        with pytest.raises(ValueError, match="Duplicate agent name"):
            network([
                (src_a, sink),
                (src_b, sink)  # Duplicate name detected here
            ])

    def test_network_no_default_outport_error(self):
        """Error when agent has no default outport."""
        split = Split(fn=lambda x: [x, None], num_outputs=2, name="split")
        sink = Sink(fn=print, name="sink")

        with pytest.raises(ValueError, match="no default outport"):
            network([
                (split, sink)  # split has no default outport
            ])

    def test_network_invalid_port_error(self):
        """Error when port doesn't exist on agent."""
        source = Source(fn=lambda: None, name="src")
        transform = Transform(fn=lambda x: x, name="trans")

        # Create invalid PortReference manually
        bad_ref = PortReference(agent=source, port_name="invalid")

        with pytest.raises(ValueError, match="not a valid outport"):
            network([
                (bad_ref, transform)
            ])

    def test_network_edges_not_list_error(self):
        """Error when edges is not a list."""
        with pytest.raises(TypeError, match="must be a list"):
            network("not a list")

    def test_network_edge_not_tuple_error(self):
        """Error when edge is not a 2-tuple."""
        source = Source(fn=lambda: None, name="src")
        transform = Transform(fn=lambda x: x, name="trans")

        with pytest.raises(TypeError, match="must be a 2-tuple"):
            network([
                (source, transform, "extra")  # 3-tuple
            ])

    def test_network_multiple_edges(self):
        """Build network with multiple edges."""
        source = Source(fn=lambda: None, name="src")
        transform = Transform(fn=lambda x: x, name="trans")
        sink = Sink(fn=print, name="sink")

        g = network([
            (source, transform),
            (transform, sink)
        ])

        assert len(g.connections) == 2
        assert "src" in g.blocks
        assert "trans" in g.blocks
        assert "sink" in g.blocks

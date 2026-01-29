"""Tests for dsl.network module - Network compilation and nested networks."""

import pytest
from dsl import network
from dsl.network import Network
from dsl.blocks import Source, Transform, Sink, Broadcast, MergeAsynch, Split


class TestNetworkValidation:
    """Test Network validation (check() method)."""

    def test_network_rejects_invalid_block_names_with_colons(self):
        """Network rejects block names containing '::'."""
        source = Source(fn=lambda: None, name="src")

        with pytest.raises(ValueError, match="cannot contain '::'"):
            Network(
                blocks={"my::block": source},
                connections=[]
            )

    def test_network_rejects_external_as_block_name(self):
        """Network rejects 'external' as a block name."""
        source = Source(fn=lambda: None, name="src")

        with pytest.raises(ValueError, match="'external' is reserved"):
            Network(
                blocks={"external": source},
                connections=[]
            )

    def test_network_validates_connection_endpoints(self):
        """Network validates all connection endpoints exist."""
        source = Source(fn=lambda: None, name="src")

        with pytest.raises(ValueError, match="unknown from_block"):
            Network(
                blocks={"src": source},
                connections=[("missing", "out_", "src", "in_")]
            )

    def test_network_validates_ports_exist(self):
        """Network validates ports exist on blocks."""
        source = Source(fn=lambda: None, name="src")
        sink = Sink(fn=print, name="sink")

        with pytest.raises(ValueError, match="Unknown from_port"):
            Network(
                blocks={"src": source, "sink": sink},
                connections=[("src", "invalid_port", "sink", "in_")]
            )

    def test_network_validates_external_ports_connected(self):
        """Network validates external ports are connected when declared."""
        source = Source(fn=lambda: None, name="src")
        transform = Transform(fn=lambda x: x, name="trans")

        # Declare external outport but don't connect it
        with pytest.raises(ValueError, match="External outport .* is not connected"):
            Network(
                outports=["out"],  # Declared but not connected!
                blocks={"src": source, "trans": transform},
                connections=[
                    ("src", "out_", "trans", "in_")
                    # Missing: ("trans", "out_", "external", "out")
                ]
            )


class TestFanoutFaninInsertion:
    """Test automatic Broadcast and MergeAsynch insertion."""

    def test_network_inserts_broadcast_for_fanout(self):
        """Network auto-inserts Broadcast when one output connects to multiple inputs."""
        source = Source(fn=lambda: None, name="src")
        sink_a = Sink(fn=print, name="sink_a")
        sink_b = Sink(fn=print, name="sink_b")

        net = Network(
            blocks={"src": source, "sink_a": sink_a, "sink_b": sink_b},
            connections=[
                ("src", "out_", "sink_a", "in_"),
                ("src", "out_", "sink_b", "in_")
            ]
        )

        # Before compilation, should have original blocks
        assert len(net.blocks) == 3

        # Trigger fanout/fanin insertion
        net._insert_fanout_fanin()

        # Should have inserted a broadcast
        broadcast_blocks = [
            b for b in net.blocks.values() if isinstance(b, Broadcast)]
        assert len(broadcast_blocks) == 1

        # Original source should now connect to broadcast
        # Broadcast should connect to both sinks
        assert len(net.connections) == 3  # src→bc, bc→sink_a, bc→sink_b

    def test_network_inserts_merge_for_fanin(self):
        """Network auto-inserts MergeAsynch when multiple outputs connect to one input."""
        src_a = Source(fn=lambda: None, name="src_a")
        src_b = Source(fn=lambda: None, name="src_b")
        sink = Sink(fn=print, name="sink")

        net = Network(
            blocks={"src_a": src_a, "src_b": src_b, "sink": sink},
            connections=[
                ("src_a", "out_", "sink", "in_"),
                ("src_b", "out_", "sink", "in_")
            ]
        )

        # Before compilation, should have original blocks
        assert len(net.blocks) == 3

        # Trigger fanout/fanin insertion
        net._insert_fanout_fanin()

        # Should have inserted a merge
        merge_blocks = [
            b for b in net.blocks.values() if isinstance(b, MergeAsynch)]
        assert len(merge_blocks) == 1

        # Both sources should connect to merge
        # Merge should connect to sink
        # src_a→merge, src_b→merge, merge→sink
        assert len(net.connections) == 3

    def test_network_handles_multiple_fanout_fanin(self):
        """Network handles multiple fanout and fanin patterns in one network."""
        # Pattern: src1 ──┐        ┌──→ sink1
        #                 ├→ merge ┤
        #          src2 ──┘        └──→ sink2

        src1 = Source(fn=lambda: None, name="src1")
        src2 = Source(fn=lambda: None, name="src2")
        sink1 = Sink(fn=print, name="sink1")
        sink2 = Sink(fn=print, name="sink2")
        trans = Transform(fn=lambda x: x, name="trans")

        net = Network(
            blocks={"src1": src1, "src2": src2, "trans": trans,
                    "sink1": sink1, "sink2": sink2},
            connections=[
                # Fanin to trans
                ("src1", "out_", "trans", "in_"),
                ("src2", "out_", "trans", "in_"),
                # Fanout from trans
                ("trans", "out_", "sink1", "in_"),
                ("trans", "out_", "sink2", "in_")
            ]
        )

        net._insert_fanout_fanin()

        # Should have inserted both merge and broadcast
        merge_blocks = [
            b for b in net.blocks.values() if isinstance(b, MergeAsynch)]
        broadcast_blocks = [
            b for b in net.blocks.values() if isinstance(b, Broadcast)]

        assert len(merge_blocks) == 1
        assert len(broadcast_blocks) == 1


class TestNestedNetworks:
    """Test nested network compilation and flattening."""

    def test_simple_nested_network(self):
        """Test network containing another network."""
        # Inner network: double → triple
        double = Transform(fn=lambda x: x * 2, name="double")
        triple = Transform(fn=lambda x: x * 3, name="triple")

        inner = Network(
            name="inner",
            inports=["in_"],
            outports=["out_"],
            blocks={"double": double, "triple": triple},
            connections=[
                ("external", "in_", "double", "in_"),
                ("double", "out_", "triple", "in_"),
                ("triple", "out_", "external", "out_")
            ]
        )

        # Outer network: source → inner → sink
        source = Source(fn=lambda: None, name="src")
        sink = Sink(fn=print, name="sink")

        outer = Network(
            name="outer",
            blocks={"src": source, "processor": inner, "sink": sink},
            connections=[
                ("src", "out_", "processor", "in_"),
                ("processor", "out_", "sink", "in_")
            ]
        )

        # Compile the network
        outer.compile()

        # After compilation, should have flattened to leaf agents
        assert "outer::src" in outer.agents
        assert "outer::processor::double" in outer.agents
        assert "outer::processor::triple" in outer.agents
        assert "outer::sink" in outer.agents

        # Should have direct agent-to-agent connections
        assert len(outer.graph_connections) == 3

    def test_deeply_nested_networks(self):
        """Test network with 3 levels of nesting."""
        # Level 3 (innermost): add_one
        add_one = Transform(fn=lambda x: x + 1, name="add_one")

        level3 = Network(
            name="level3",
            inports=["in_"],
            outports=["out_"],
            blocks={"add_one": add_one},
            connections=[
                ("external", "in_", "add_one", "in_"),
                ("add_one", "out_", "external", "out_")
            ]
        )

        # Level 2: double → level3 → triple
        double = Transform(fn=lambda x: x * 2, name="double")
        triple = Transform(fn=lambda x: x * 3, name="triple")

        level2 = Network(
            name="level2",
            inports=["in_"],
            outports=["out_"],
            blocks={"double": double, "processor": level3, "triple": triple},
            connections=[
                ("external", "in_", "double", "in_"),
                ("double", "out_", "processor", "in_"),
                ("processor", "out_", "triple", "in_"),
                ("triple", "out_", "external", "out_")
            ]
        )

        # Level 1 (outer): source → level2 → sink
        source = Source(fn=lambda: None, name="src")
        sink = Sink(fn=print, name="sink")

        level1 = Network(
            name="level1",
            blocks={"src": source, "proc": level2, "sink": sink},
            connections=[
                ("src", "out_", "proc", "in_"),
                ("proc", "out_", "sink", "in_")
            ]
        )

        # Compile
        level1.compile()

        # Should flatten to leaf agents with full paths
        assert "level1::src" in level1.agents
        assert "level1::proc::double" in level1.agents
        assert "level1::proc::processor::add_one" in level1.agents
        assert "level1::proc::triple" in level1.agents
        assert "level1::sink" in level1.agents

        # Verify connections form a chain
        assert len(level1.graph_connections) == 4

    def test_nested_network_with_multiple_external_ports(self):
        """Test nested network with multiple input/output ports."""
        # Inner network: two inputs, two outputs
        # in_1 → proc1 → out_1
        # in_2 → proc2 → out_2

        proc1 = Transform(fn=lambda x: x * 2, name="proc1")
        proc2 = Transform(fn=lambda x: x * 3, name="proc2")

        inner = Network(
            name="inner",
            inports=["in_1", "in_2"],
            outports=["out_1", "out_2"],
            blocks={"proc1": proc1, "proc2": proc2},
            connections=[
                ("external", "in_1", "proc1", "in_"),
                ("external", "in_2", "proc2", "in_"),
                ("proc1", "out_", "external", "out_1"),
                ("proc2", "out_", "external", "out_2")
            ]
        )

        # Outer network
        src1 = Source(fn=lambda: None, name="src1")
        src2 = Source(fn=lambda: None, name="src2")
        sink1 = Sink(fn=print, name="sink1")
        sink2 = Sink(fn=print, name="sink2")

        outer = Network(
            name="outer",
            blocks={"src1": src1, "src2": src2, "proc": inner,
                    "sink1": sink1, "sink2": sink2},
            connections=[
                ("src1", "out_", "proc", "in_1"),
                ("src2", "out_", "proc", "in_2"),
                ("proc", "out_1", "sink1", "in_"),
                ("proc", "out_2", "sink2", "in_")
            ]
        )

        # Compile
        outer.compile()

        # Should have 6 agents
        assert len(outer.agents) == 6

        # Verify connections
        assert len(outer.graph_connections) == 4

    def test_nested_network_with_fanout(self):
        """Test nested network where outer network creates fanout after flattening."""
        # Inner network: simple passthrough (in_ → trans → out_)
        transform = Transform(fn=lambda x: x * 2, name="trans")

        inner = Network(
            name="inner",
            inports=["in_"],
            outports=["out_"],
            blocks={"trans": transform},
            connections=[
                ("external", "in_", "trans", "in_"),
                ("trans", "out_", "external", "out_")
            ]
        )

        # Outer network: creates fanout by connecting inner.out_ to two sinks
        source = Source(fn=lambda: None, name="src")
        sink1 = Sink(fn=print, name="sink1")
        sink2 = Sink(fn=print, name="sink2")

        outer = Network(
            name="outer",
            blocks={"src": source, "proc": inner,
                    "sink1": sink1, "sink2": sink2},
            connections=[
                ("src", "out_", "proc", "in_"),
                ("proc", "out_", "sink1", "in_"),  # Fanout from proc.out_
                ("proc", "out_", "sink2", "in_")   # to two sinks
            ]
        )

        # Compile
        outer.compile()

        # Should have inserted broadcast in outer network for the fanout
        broadcast_agents = [
            name for name in outer.agents if "broadcast" in name]
        assert len(broadcast_agents) == 1


class TestNetworkCompilation:
    """Test complete network compilation process."""

    def test_network_compiles_successfully(self):
        """Network compiles without errors."""
        source = Source(fn=lambda: None, name="src")
        transform = Transform(fn=lambda x: x, name="trans")
        sink = Sink(fn=print, name="sink")

        net = Network(
            name="test",
            blocks={"src": source, "trans": transform, "sink": sink},
            connections=[
                ("src", "out_", "trans", "in_"),
                ("trans", "out_", "sink", "in_")
            ]
        )

        net.compile()

        assert net.compiled
        assert len(net.agents) == 3
        assert len(net.threads) == 3
        assert len(net.queues) == 2  # One per inport (trans, sink)

    def test_network_assigns_agent_names(self):
        """Network assigns full path names to agents during compilation."""
        source = Source(fn=lambda: None, name="src")
        sink = Sink(fn=print, name="sink")

        net = Network(
            name="test",
            blocks={"src": source, "sink": sink},
            connections=[("src", "out_", "sink", "in_")]
        )

        net.compile()

        # Agents should have full path names
        assert "test::src" in net.agents
        assert "test::sink" in net.agents

    def test_network_wires_queues_correctly(self):
        """Network wires queues to connect agents."""
        source = Source(fn=lambda: None, name="src")
        sink = Sink(fn=print, name="sink")

        net = Network(
            name="test",
            blocks={"src": source, "sink": sink},
            connections=[("src", "out_", "sink", "in_")]
        )

        net.compile()

        src_agent = net.agents["test::src"]
        sink_agent = net.agents["test::sink"]

        # Source output should connect to sink input
        assert src_agent.out_q["out_"] is sink_agent.in_q["in_"]

    def test_network_creates_threads(self):
        """Network creates one thread per agent."""
        source = Source(fn=lambda: None, name="src")
        transform = Transform(fn=lambda x: x, name="trans")
        sink = Sink(fn=print, name="sink")

        net = Network(
            name="test",
            blocks={"src": source, "trans": transform, "sink": sink},
            connections=[
                ("src", "out_", "trans", "in_"),
                ("trans", "out_", "sink", "in_")
            ]
        )

        net.compile()

        assert len(net.threads) == 3
        # Verify thread names
        thread_names = [t.name for t in net.threads]
        assert "test::src_thread" in thread_names
        assert "test::trans_thread" in thread_names
        assert "test::sink_thread" in thread_names


class TestNetworkExecution:
    """Test network execution (run_network)."""

    def test_simple_network_executes(self):
        """Simple network runs to completion."""
        results = []

        class ListSource:
            def __init__(self):
                self.data = [1, 2, 3]
                self.index = 0

            def run(self):
                if self.index >= len(self.data):
                    return None
                val = self.data[self.index]
                self.index += 1
                return val

        data = ListSource()
        source = Source(fn=data.run, name="src")
        double = Transform(fn=lambda x: x * 2, name="double")
        sink = Sink(fn=results.append, name="sink")

        g = network([
            (source, double),
            (double, sink)
        ])

        g.run_network()

        assert results == [2, 4, 6]

    def test_nested_network_executes(self):
        """Nested network runs to completion."""
        results = []

        class ListSource:
            def __init__(self):
                self.data = [1, 2]
                self.index = 0

            def run(self):
                if self.index >= len(self.data):
                    return None
                val = self.data[self.index]
                self.index += 1
                return val

        # Inner: double → add_ten
        double = Transform(fn=lambda x: x * 2, name="double")
        add_ten = Transform(fn=lambda x: x + 10, name="add_ten")

        inner = Network(
            name="inner",
            inports=["in_"],
            outports=["out_"],
            blocks={"double": double, "add_ten": add_ten},
            connections=[
                ("external", "in_", "double", "in_"),
                ("double", "out_", "add_ten", "in_"),
                ("add_ten", "out_", "external", "out_")
            ]
        )

        # Outer: source → inner → sink
        data = ListSource()
        source = Source(fn=data.run, name="src")
        sink = Sink(fn=results.append, name="sink")

        outer = Network(
            name="outer",
            blocks={"src": source, "proc": inner, "sink": sink},
            connections=[
                ("src", "out_", "proc", "in_"),
                ("proc", "out_", "sink", "in_")
            ]
        )

        outer.run_network()

        # 1 → *2 → +10 = 12
        # 2 → *2 → +10 = 14
        assert results == [12, 14]


class TestExternalPortResolution:
    """Test resolution of external port chains."""

    def test_external_port_chain_resolves(self):
        """External port chains collapse to direct connections."""
        # Inner network with a passthrough agent (can't be empty!)
        passthrough = Transform(fn=lambda x: x, name="pass")

        inner = Network(
            name="inner",
            inports=["in"],
            outports=["out"],
            blocks={"pass": passthrough},  # Now has a block
            connections=[
                ("external", "in", "pass", "in_"),
                ("pass", "out_", "external", "out")
            ]
        )

        # Outer network
        source = Source(fn=lambda: None, name="src")
        sink = Sink(fn=print, name="sink")

        outer = Network(
            name="outer",
            blocks={"src": source, "proc": inner, "sink": sink},
            connections=[
                ("src", "out_", "proc", "in"),
                ("proc", "out", "sink", "in_")
            ]
        )

        outer.compile()

        # Verify external chains resolved correctly
        assert "outer::proc::pass" in outer.agents

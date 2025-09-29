from dsl.core import Agent, STOP
from typing import Optional, Any, Callable
import copy


# =================================================
#                     Broadcast                   |
# =================================================

class Broadcast(Agent):
    """
    Broadcasts any message received on inport "in" to all defined outports.
    Useful for duplicating a stream to multiple downstream blocks.
    Makes deep copies of messages to avoid shared state issues.
    """

    def __init__(self, num_outports: int):
        super().__init__(inports=["in"],
                         outports=[f"out_{i}" for i in range(num_outports)])

    def run(self):
        while True:
            msg = self.recv("in")
            if isinstance(msg, str) and msg == STOP:
                self.stop()
                return
            else:
                for outport in self.outports:
                    outport_msg = copy.deepcopy(msg)
                    self.send(outport_msg, outport=outport)


class SplitBinary(Agent):
    """
    Single inport "in" and two outports "out_0" and "out_1"
    Splits incoming stream into two streams based on a predicate function.
    If predicate(msg) is True, msg is sent to "out_1", else to "out_0".

    """

    def __init__(
        self,
        outports: list[str] = ["out_0", "out_1"],
        func: Optional[Callable[[Any], bool]] = None,
    ):
        if func is None:
            raise ValueError(
                "A predicate function must be provided for {name} in TwoWaySplit.")
        self.func = func

        super().__init__(inports=["in"], outports=outports)

    def run(self):
        while True:
            msg = self.recv("in")
            if isinstance(msg, str) and msg == STOP:
                self.stop()
                return
            else:
                if self.func(msg):
                    outport = self.outports[1]
                else:
                    outport = self.outports[0]
                self.send(msg=msg, outport=outport)

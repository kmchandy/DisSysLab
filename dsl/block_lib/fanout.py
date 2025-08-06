"""
Module: stream_transformers.py

Summary:
Defines the StreamTransformer class and several variants for transforming data
streams. These include wrappers for arbitrary Python functions, multi-stream
transformations, and GPT-based transformations using OpenAI's API.

Tags: ["transformer", "stream", "block", "NLP", "OpenAI", "NumPy", "GPT"]
"""


from typing import Optional,
from dsl.core import Agent

DEBUG_LOG = "dsl_debug.log"


# =================================================
#                     Broadcast                   |
# =================================================

class Broadcast(Agent):
    """
    Broadcasts any message received on inport "in" to all defined outports.
    Useful for duplicating a stream to multiple downstream blocks.
    """

    def __init__(
        self,
        outports: list[str],
        name: Optional[str] = None
    ):
        super().__init__(name=name or "Broadcast",
                         inports=["in"],
                         outports=outports,
                         run=self.run)

    def run(self):
        while True:
            msg = self.recv("in")
            if msg == "__STOP__":
                self.stop()
                return
            else:
                for outport in self.outports:
                    self.send(msg=msg, outport=outport)

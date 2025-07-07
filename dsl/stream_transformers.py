from dsl.core import Agent, StreamToList, Network
from typing import Optional, List, Callable, Dict, Tuple, Any


def generic_transformer_fn(generator_fn, *args, **kwargs):
    def stream_fn(agent):
        transform = generator_fn(*args, **kwargs)
        try:
            while True:
                msg = next(gen)
                agent.send(msg, "out")
        except StopIteration:
            agent.send("__STOP__", "out")
    return stream_fn


class StreamTransformer(SimpleAgent):

    def __init__(
        self,
        name: str = None,
        description: str = None,
        transform_fn: Optional[Callable[[Any], Any]] = None,
    ):
        def handle_msg(agent, msg):
            if msg == "__STOP__":
                agent.send("__STOP__", "out")
            else:
                transformed = transform_fn(msg)
                agent.send(transformed, "out")  # FIXED LINE

        super().__init__(
            name=name,
            description=description,
            inport="in",            # Always has an inport called 'in'
            outports=["out"],       # Always has a single outport called 'out'
            init_fn=None,
            handle_msg=handle_msg
        )

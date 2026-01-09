# dsl.blocks.split

from dsl.core import Agent, STOP


class Split(Agent):
    """
    Route messages to N outputs based on router decisions.

    The router object must have .run(msg) that returns a list of N messages,
    where each message is sent to the corresponding output port.
    If a message in the list is None, it's filtered (not sent).

    This allows:
    - Routing to one output: [msg, None, None]
    - Routing to multiple: [msg, msg, None]
    - Transforming while routing: [enriched_msg, None, None]

    Example:
        class ContentRouter:
            def run(self, msg):
                if is_spam(msg["text"]):
                    return [msg, None, None]  # Route to spam handler
                elif is_abuse(msg["text"]):
                    return [None, msg, None]  # Route to abuse handler
                else:
                    return [None, None, msg]  # Route to safe handler

        router = ContentRouter()
        split = Split(router=router, num_outputs=3)
    """

    def __init__(self, *, router, num_outputs: int):
        if not hasattr(router, 'run'):
            raise AttributeError("router must have .run(msg) method")

        self.router = router
        self.num_outputs = num_outputs
        super().__init__(
            inports=["in"],
            outports=[f"out_{i}" for i in range(num_outputs)]
        )

    def run(self):
        while True:
            msg = self.recv("in")
            if msg is STOP:
                self.broadcast_stop()
                return

            try:
                results = self.router.run(msg)

                # Validate results
                if not isinstance(results, (list, tuple)):
                    raise TypeError(
                        f"Router must return a list of {self.num_outputs} messages, "
                        f"got {type(results).__name__}"
                    )
                if len(results) != self.num_outputs:
                    raise ValueError(
                        f"Router must return exactly {self.num_outputs} messages, "
                        f"got {len(results)}"
                    )

                # Send to each output (None is filtered automatically by send())
                for i, out_msg in enumerate(results):
                    self.send(out_msg, f"out_{i}")

            except Exception as e:
                print(f"[Split] Error in router: {e}")
                import traceback
                traceback.print_exc()
                self.broadcast_stop()
                return

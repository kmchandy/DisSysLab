# dsl/connectors/sink_make_console_summary.py

from typing import Dict


def make_console_summary(every_n: int = 1):
    """
    Prints a compact summary every N messages (keeps output readable).
    """
    i = {"n": 0}

    def _sink(msg: Dict[str, float]):
        i["n"] += 1
        if i["n"] % every_n == 0:
            print(f"t={msg['t_step']:3d}, is {msg['pred_low']:+8.2f} <= {msg['x']:+8.2f} <= {msg['pred_high']:+8.2f}? anomaly={msg['anomaly']}"
                  )
        return msg
    _sink.__name__ = f"console_every_{every_n}"
    return _sink

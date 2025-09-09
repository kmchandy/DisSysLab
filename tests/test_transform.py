# tests/test_transform.py
from __future__ import annotations
from typing import Any
from dsl.core import STOP
from dsl.block_lib.transforms.transform import Transform


class _Probe:
    def __init__(self):
        self.out = []

    def send(self, msg: Any, outport: str = "out"):
        assert outport == "out"
        self.out.append(msg)


def test_transform_maps_values():
    t = Transform(func=lambda m: m * 2)
    probe = _Probe()
    t.handle_msg(probe, 3)
    t.handle_msg(probe, -1)
    assert probe.out == [6, -2]


def test_transform_passes_stop():
    t = Transform(func=lambda m: m)
    probe = _Probe()
    t.handle_msg(probe, STOP)
    assert probe.out == [STOP]


def test_transform_stores_attributes():
    t = Transform(func=sum, args=(), kwargs={})
    assert callable(t.func)
    assert isinstance(t.args, tuple)
    assert isinstance(t.kwargs, dict)

# Run without pytest


def main():
    for fn in [test_transform_maps_values, test_transform_passes_stop, test_transform_stores_attributes]:
        fn()
        print(f"{fn.__name__}: PASS")


if __name__ == "__main__":
    main()

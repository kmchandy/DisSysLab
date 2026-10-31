"""Loaded by Python before the tests run (run_tests puts this folder on
PYTHONPATH). It cuts the network for that process: code the agent writes
can be run, but cannot reach anything. Best effort, not a sandbox: see
README.md."""
import socket


class _NoNetwork(socket.socket):
    def connect(self, *args, **kwargs):
        raise OSError("network disabled for the lab's test runs")

    def connect_ex(self, *args, **kwargs):
        raise OSError("network disabled for the lab's test runs")


socket.socket = _NoNetwork
socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(
    OSError("network disabled for the lab's test runs"))

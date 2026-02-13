# lessons.01_networks.stop_example

from dsl import network
import time


def from_list_0():
    for item in ["a", "b"]:
        yield item
        time.sleep(0.06)
    # Agent sends a stop signal and terminates execution.


def from_list_1():
    for item in ["u", "v", "w", "x", "y", "z"]:
        yield item
        time.sleep(0.03)
    # Agent sends a stop signal and terminates execution.


def uppercase(x):
    return x.upper()
    # Agent sends a stop signal when it receives a stop signal
    # on each of its inputs and then terminates execution.


results_0 = []
def to_results_0(v): results_0.append(v)
# Agent terminates execution when it receives a stop signal on
# each of its inputs.


results_1 = []
def to_results_1(v): results_1.append(v)
# Agent terminates execution when it receives a stop signal on
# each of its inputs.


g = network([(from_list_0, uppercase), (from_list_1, uppercase),
             (uppercase, to_results_0), (uppercase, to_results_1)])
g.run_network()
# Execution terminates when all agents have terminated.

assert set(results_0) == {"A", "B", "U", "V", "W", "X", "Y", "Z"}

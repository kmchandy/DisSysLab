"""The runtime: what runs an office once it has been built.

This package is the *operating system* layer of the spec
(``docs/internals/design/officespeak_revised.md``, Principle 1): agents,
the queues between them, and the framework's own plumbing. Roles know
nothing about it, and nothing in it travels inside a message.

Everything that runs an office lives here:

- :mod:`dissyslab.runtime.agent` -- ``Agent``: ports, ``send``, ``recv``,
  failure reporting, state for snapshots.
- :mod:`dissyslab.runtime.os_hooks` -- what the operating system does on
  each agent's thread: termination replies, snapshots and recovery,
  tracing. ``Agent`` inherits it; ``send`` and ``recv`` show where it
  steps in.
- :mod:`dissyslab.runtime.messages` -- the operating system's messages.
- :mod:`dissyslab.runtime.network` -- ``Network``: wires agents together
  with queues, starts one thread per agent, runs, and reports.
- :mod:`dissyslab.runtime.termination` -- the termination detector
  (``OsAgent``), which decides when an office has finished.
- :mod:`dissyslab.runtime.snapshot` -- the on-disk layout of snapshots.
- :mod:`dissyslab.runtime.plumbing` -- the two agents the framework
  inserts by itself: ``Broadcast`` (one sender, several receivers) and
  ``MergeAsynch`` (several senders, one receiver).

The agent kinds an office is built from (sources, sinks, roles,
coordinators) are still in ``dissyslab.blocks``; the spec replaces them.
``dissyslab.core``, ``dissyslab.network``, ``dissyslab.os_agent`` and
``dissyslab.snapshot`` remain as aliases for older imports.

**Frozen (October 2026).** The runtime is kept as it is while the spec
and the labs are built: no further restructuring
(``docs/internals/design/restructure_plan.md``, section 3).
"""

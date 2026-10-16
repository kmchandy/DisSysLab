"""The runtime: what runs an office once it has been built.

This package is the *operating system* layer of the spec
(``docs/internals/design/officespeak_revised.md``, Principle 1): agents,
the queues between them, and the framework's own plumbing. Roles know
nothing about it, and nothing in it travels inside a message.

It is being assembled from older modules during the restructuring
(``docs/internals/design/restructure_plan.md``, Phase 1). So far:

- :mod:`dissyslab.runtime.agent` -- ``Agent``: ports, ``send``, ``recv``,
  failure reporting, state for snapshots.
- :mod:`dissyslab.runtime.os_hooks` -- what the operating system does on
  each agent's thread: termination replies, snapshots and recovery,
  tracing. ``Agent`` inherits it; ``send`` and ``recv`` show where it
  steps in.
- :mod:`dissyslab.runtime.messages` -- the operating system's messages.
- :mod:`dissyslab.runtime.plumbing` -- the two agents the framework
  inserts by itself: ``Broadcast`` (one sender, several receivers) and
  ``MergeAsynch`` (several senders, one receiver).

The network and the termination detector still live in
``dissyslab.network`` and ``dissyslab.os_agent``.
"""

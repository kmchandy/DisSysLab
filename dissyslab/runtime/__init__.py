"""The runtime: what runs an office once it has been built.

This package is the *operating system* layer of the spec
(``docs/internals/design/officespeak_revised.md``, Principle 1): agents,
the queues between them, and the framework's own plumbing. Roles know
nothing about it, and nothing in it travels inside a message.

It is being assembled from older modules during the restructuring
(``docs/internals/design/restructure_plan.md``, Phase 1). So far:

- :mod:`dissyslab.runtime.plumbing` -- the two agents the framework
  inserts by itself: ``Broadcast`` (one sender, several receivers) and
  ``MergeAsynch`` (several senders, one receiver).

The agent base class, the network and the operating-system algorithms
(termination detection, snapshots, tracing) still live in
``dissyslab.core``, ``dissyslab.network`` and ``dissyslab.os_agent``.
"""

"""How roles become running agents (spec sections 4 to 6).

Being built in Phase 3 of ``docs/internals/design/restructure_plan.md``:

- :mod:`dissyslab.agents.reply` -- checking a role's reply against its
  front matter (spec 4.5), separately for annotators and authors.
- :mod:`dissyslab.agents.role_agent` -- the running agent for a role:
  ``AnnotatorAgent`` (a map) or ``AuthorAgent`` (a flat-map).
- :mod:`dissyslab.agents.english` -- an English role: its text and the
  message, sent to a model, nothing appended.
- :mod:`dissyslab.agents.python_role` -- a Python role: ``needs:``
  checked, one class loaded and constructed with its arguments.
- :mod:`dissyslab.agents.router` -- a router: one field, outboxes named
  by its values, ``otherwise``.
- :mod:`dissyslab.agents.synchronizer` -- the keyed synchronizer: one
  group per key, sent when every inbox has contributed; merged, or
  collected with ``collect=``; incomplete groups reported at the end.

The gate is the runtime's existing ``Gate`` (``dissyslab.blocks.gate``),
built by ``dissyslab.office.build``.
"""

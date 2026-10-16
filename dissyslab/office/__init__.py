"""dissyslab.office -- from an office folder to a running network.

Each step is its own module (spec section 8):

- ``syntax``      office.md text -> ``model.OfficeFile``
- ``frontmatter`` a role's or component's front matter
- ``resolve``     what each declaration's kind refers to
- ``components``  built-in sources and sinks, from ``utils``'s registry
- ``build``       the runtime network, and ``run_office``
- ``check``       ``dsl check``: every problem, nothing run
- ``draw``        ``dsl draw``
- ``trust`` and ``role_effects`` the guardrail notes ``check`` gives

Most people use these through the ``dsl`` command. Nothing is
re-exported here, so importing one step does not import the rest.
"""

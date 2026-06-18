# DisSysLab internals

Design and implementation notes for the framework itself. If you
are *using* DisSysLab to build offices, start with
[../README.md](../README.md) and [../BUILD_APPS.md](../BUILD_APPS.md);
the documents here are for developers who want to read the source.

Each major module has two paired documents — an *overview* of what
the module does and why, and an *implementation* note that walks
through the code:

| Module | Overview | Implementation |
|---|---|---|
| `dissyslab/core.py` | [core_overview.md](core_overview.md) | [core_implementation.md](core_implementation.md) |
| `dissyslab/network.py` | [network_overview.md](network_overview.md) | [network_implementation.md](network_implementation.md) |
| `dissyslab/builder.py` | [builder_overview.md](builder_overview.md) | [builder_implementation.md](builder_implementation.md) |
| `dissyslab/blocks/` | (see overviews above) | [blocks_implementation.md](blocks_implementation.md) |

Cross-cutting:

- [architecture.md](architecture.md) — the framework's overall design.
- [making_a_component.md](making_a_component.md) — how to add a new
  component (source, transform, sink, or other block) to the framework.

For the layered framework surface and the *"fn_lib vs library.py"*
decision rule, see [../EXTENDING.md](../EXTENDING.md). That document
sits one level up because it is for both maintainers and advanced
users; the documents in this folder are for maintainers only.

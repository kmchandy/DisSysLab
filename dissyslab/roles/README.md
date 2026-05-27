# dissyslab/roles/ — built-in role library

This folder is the framework's built-in role library. Role files
here are available to every office: when an `office.md` line says
`Alex is a severity_classifier.`, the framework first looks in the
office's own `roles/` folder, and if it doesn't find the role
there, falls back to *this* folder.

Pat's office gets to use these roles **without copying or
overriding** them. To override, drop a file with the same name
into the office's local `roles/`.

## Files

- `*.md` — LLM-prompted roles (see `nl_role` in
  `dissyslab.office.library`). Each prompt is tuned to work
  reliably across Claude and at-least-3B local SLMs (Qwen,
  Llama, Gemma) by spelling out the JSON contract explicitly.
- `*.py` — Python-function roles (see
  `dissyslab.office.library.AgentRoleEntry`). Each defines a
  module-level `role` attribute the loader picks up.

## How to add a role

1. Drop a new `.md` (LLM-driven) or `.py` (Python-driven) file in
   this folder.
2. Make sure the name doesn't collide with a role any office
   already references — if it does, the library would silently
   override the office's expectation.
3. Run `pytest` to make sure the gallery snapshot still compiles
   against the new entry.

## Curation policy

This folder is for roles that are general enough to be useful
across many offices. Domain-specific or one-off roles belong in
the office's local `roles/`, not here.

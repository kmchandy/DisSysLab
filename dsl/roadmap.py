# Suggested Roadmap for Next Steps (Saved)
#
# 1) Add a “guided demo” command (demo sentiment)
#    - Builds a tiny network step-by-step with narration.
#    - Explains each step in plain English.
#
# 2) Templates + “new from template”
#    - Add a templates folder with YAMLs.
#    - REPL: templates → list names, use template <name> → load YAML.
#
# 3) Session save/load
#    - save <path> → write to YAML.
#    - open <path> → load YAML (alias to load yaml).
#    - Optional autosave via environment variable.
#
# 4) Explain-as-you-go hints
#    - Suggest next logical command after each action.
#
# 5) ASCII graph visualization
#    - graph → show blocks and connections in ASCII.
#
# 6) Guardrails: function ↔ block-type validation
#    - Validate in set_block_function and reject invalid pairs early.
#
# 7) YAML schema + versioning
#    - Require version and kind fields in YAML root.
#
# 8) Tests & CI
#    - Add GitHub Actions to run tests on push.
#
# 9) Prompt template browser
#    - prompts → list templates.
#    - show prompt <name> → display content.
#
# 10) Wizard mode toggle
#    - wizard on → structured Q&A mode.
#    - wizard off → normal REPL.

#    - Expand pytest coverage.

# A.
#   Add more options to main(). for example, "create" "make", "block" should all create a block.
# B.
#   Add functions for fan-out. Currently only has broadcast.

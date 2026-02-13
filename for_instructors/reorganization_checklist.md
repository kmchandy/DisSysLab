# DisSysLab Repository Reorganization Checklist

**Goal:** Clean up the repository to make it ideal for target users (students, developers, researchers, hobbyists)

**Estimated Time:** 2-3 hours

---

## **Phase 1: Backup & Preparation** (5 minutes)

### Step 1.1: Create a backup branch
```bash
cd DisSysLab
git checkout -b backup-before-cleanup
git push origin backup-before-cleanup
git checkout main
```

### Step 1.2: Create a cleanup branch
```bash
git checkout -b repository-cleanup
```

**Why:** Work safely without affecting main branch

---

## **Phase 2: Clean Up examples/ Directory** (45 minutes)

### Step 2.1: Create new directories

```bash
cd examples

# Create extras directory for loose files
mkdir -p extras

# Already exists: helpers/
```

### Step 2.2: Audit and move loose Python files

**For each .py file in examples/, decide:**

**A. Is it referenced by any module?**
   - Check module READMEs
   - Search for imports: `grep -r "filename" module_*/`
   
**B. Move based on decision:**

**Move to extras/ (unreferenced examples):**
```bash
# List of files to move (verify first by checking modules):
mv simple_network.py extras/
mv simple_network_2.py extras/
mv simple_network_claude.py extras/
mv simple_agent.py extras/
mv simple_agent_2.py extras/
mv simple_broadcast.py extras/
mv simple_function_parameters.py extras/
mv simple_merge.py extras/
mv simple_pipeline.py extras/
mv simple_source_sink.py extras/
mv simple_text_analysis.py extras/
mv blocks_and_agents.py extras/
mv live_kv_console.py extras/
mv round_robin_split.py extras/  # Check module_05 first!
mv numpy_example_0.py extras/    # Check module_11 first!
```

**Move to appropriate modules:**
```bash
# Check if these are referenced first:
mv agent_entity_extractor.py module_08_prompts/  # If used
mv agent_OpenAI.py module_08_prompts/           # If used
mv agent_pipeline_template.py module_08_prompts/ # If used
mv agent_sentiment_scorer.py module_08_prompts/  # If used
mv agent_summarizer.py module_08_prompts/        # If used
```

**Move to for_instructors/demo_code/ (instructor demos):**
```bash
# Create instructor directory first (see Phase 4)
# Then move:
mv rss_NASA_demo.py ../for_instructors/demo_code/
mv rss_NASA_simple_demo.py ../for_instructors/demo_code/
mv NASA_RSS_counts.py ../for_instructors/demo_code/
```

**Keep or move based on module usage:**
```bash
# jetstream_demo.py - check if module_09 references it
# If not referenced by module_09:
mv jetstream_demo.py extras/
```

### Step 2.3: Move documentation files

```bash
# Move to appropriate modules
mv Mock_And_Real.md module_09_connectors/
mv tutorial_prompts_to_python.md module_08_prompts/
```

### Step 2.4: Delete theory directory

```bash
# Remove theory (moving to separate repo/location later)
rm -rf theory
```

### Step 2.5: Create README files for new directories

**Create examples/extras/README.md:**
```bash
cat > extras/README.md << 'EOF'
# Bonus Examples

These are additional examples for exploration.  
**Not required for the core learning path.**

After completing Modules 01-10, feel free to explore these:
- `simple_network.py` - Minimal network example
- `simple_agent.py` - Agent basics
- `jetstream_demo.py` - Live streaming demonstration

These examples may reference concepts from multiple modules.

---

**Learning DisSysLab?** Start with [Module 01](../module_01_basics/) instead.
EOF
```

**Create examples/helpers/README.md:**
```bash
cat > helpers/README.md << 'EOF'
# Helper Functions

Reusable utilities used by the example modules.  
**You don't need to study these files** - they're imported by examples.

## What's Here

- `sources_simple.py` - Basic source implementations
- `sinks_simple.py` - Basic sink implementations  
- `transforms_simple.py` - Common transform patterns
- `anomaly.py` - Anomaly detection helpers
- `sliding_window_*.py` - Window-based processing
- Other utilities for keeping example code clean

## When Learning

- **Focus on the module examples** (module_01, module_02, etc.)
- These helpers keep example code readable
- Peek at the code if curious, but it's not required

## When Building

- You can copy and adapt these patterns
- Or create your own helper functions
- Use these as reference implementations
EOF
```

---

## **Phase 3: Update examples/README.md** (15 minutes)

### Step 3.1: Replace examples/README.md

```bash
cd examples
cat > README.md << 'EOF'
# DisSysLab Examples

Progressive learning modules for building distributed systems.

## Quick Start

**New to DisSysLab?**
1. Read the main [README.md](../README.md)
2. Start with [Module 01: Basics](module_01_basics/) 
3. Follow the modules in order (see below)

## Learning Sequence

### **Core Sequence** (Start Here!)
Work through these in order:

1. **[module_01_basics](module_01_basics/)** - Your first network ⭐ START HERE
2. **[module_02_filtering](module_02_filtering/)** - Conditional message dropping
3. **[module_03_fanout](module_03_fanout/)** - Broadcast to multiple destinations
4. **[module_04_fanin](module_04_fanin/)** - Merge multiple sources
5. **[module_09_connectors](module_09_connectors/)** - Real-world data sources
6. **[module_10_build_apps](module_10_build_apps/)** - Systematic app development

### **Advanced Topics** (Optional)
Explore these after completing the core:

- **[module_05_split](module_05_split/)** - Splitting streams
- **[module_06_merge_synch](module_06_merge_synch/)** - Synchronous merging
- **[module_07_complex_patterns](module_07_complex_patterns/)** - Advanced topologies
- **[module_08_prompts](module_08_prompts/)** - AI integration
- **[module_11_numeric](module_11_numeric/)** - NumPy and pandas

### **Bonus Examples** (Extras)
Additional examples for exploration: **[extras/](extras/)**

### **Helper Utilities** (Reference)
Reusable code used by modules: **[helpers/](helpers/)**

## Running Examples

From the DisSysLab root directory:
```bash
python3 -m examples.module_01_basics.example
```

## Module Structure

Each module contains:
- **README.md** - Tutorial with concepts and explanations
- **Example files** - Working code you can run
- **__init__.py** - Module information

## Getting Help

- **Stuck?** Check [DEBUGGING.md](module_10_build_apps/DEBUGGING.md)
- **How it works:** [HOW_IT_WORKS.md](../docs/how-it-works.md)
- **Quick reference:** [QUICKSTART.md](module_10_build_apps/QUICKSTART.md)
- **Build apps:** [BUILD_APP.md](module_10_build_apps/BUILD_APP.md)

---

**Ready to start?** Go to [Module 01: Basics](module_01_basics/) →
EOF
```

---

## **Phase 4: Reorganize docs/ Directory** (20 minutes)

### Step 4.1: Clean up empty directories

```bash
cd ../docs

# Delete empty directories
rmdir guides internal api
```

### Step 4.2: Create for_instructors/ directory

```bash
cd ..
mkdir -p for_instructors/demo_code
```

### Step 4.3: Move instructor-specific files

```bash
# Move from docs/ to for_instructors/
mv docs/DOCUMENTATION_STRATEGY.md for_instructors/
mv docs/ROADMAP.md for_instructors/
```

### Step 4.4: Reorganize remaining docs

```bash
cd docs

# Create tutorials subdirectory
mkdir -p tutorials

# Move tutorial files
mv teaching_stateful_sources.md tutorials/stateful-sources.md
```

### Step 4.5: Rename files to lowercase (optional but consistent)

```bash
cd docs
mv HOW_IT_WORKS.md how-it-works.md
mv MODULE_ORDER.md module-order.md
```

### Step 4.6: Create docs/README.md

```bash
cat > README.md << 'EOF'
# DisSysLab Documentation

## For Students

**Getting Started:**
1. [Installation & Setup](getting-started.md) *(create this)*
2. [Module Learning Order](module-order.md)
3. [How DisSysLab Works](how-it-works.md)

**Building Apps:**
- [Quick Reference](../examples/module_10_build_apps/QUICKSTART.md)
- [Building Apps Systematically](../examples/module_10_build_apps/BUILD_APP.md)
- [Debugging Guide](../examples/module_10_build_apps/DEBUGGING.md)

**Tutorials:**
- [Stateful Sources](tutorials/stateful-sources.md)

## For Instructors

See [for_instructors/](../for_instructors/) directory for teaching materials.
EOF
```

### Step 4.7: Create for_instructors/README.md

```bash
cd ../for_instructors
cat > README.md << 'EOF'
# Teaching Materials for Instructors

Resources for teaching DisSysLab in courses or workshops.

## Contents

- **DOCUMENTATION_STRATEGY.md** - How documentation is organized
- **ROADMAP.md** - Future development plans
- **demo_code/** - Example demonstrations for classroom use

## Pedagogy Notes

DisSysLab is designed for self-study with these principles:

**Progressive Complexity:**
- Start simple (3-node pipeline)
- Add one concept at a time
- Build real, useful applications

**Immediate Success:**
- Students run working code in 5 minutes
- Every module produces tangible results
- Mock components for safe learning

**Core vs Advanced:**
- Core modules (01-04, 09-10) - Required
- Advanced modules (05-08, 11) - Optional
- Clear learning path documented

## Teaching Recommendations

**Week 1:** Modules 01-04 (Basics through Fanin)
**Week 2:** Module 09 (Connectors) + Module 10 (Build Apps)
**Week 3+:** Advanced topics or student projects

**Assessment Ideas:**
- Build a personal monitoring application
- Demonstrate fanin + fanout patterns
- Explain network topology design
- Debug a broken network

## Student Support

Common issues and solutions documented in:
- [DEBUGGING.md](../examples/module_10_build_apps/DEBUGGING.md)
- Each module's README troubleshooting section
EOF
```

---

## **Phase 5: Update Root Files** (15 minutes)

### Step 5.1: Replace root README.md

```bash
cd DisSysLab
cp /path/to/ROOT_README_UPDATED.md README.md
```

*(Use the updated README.md we just created)*

### Step 5.2: Update .gitignore

```bash
cat >> .gitignore << 'EOF'

# Generated documentation site
site/

# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
.pytest_cache/

# Virtual environments
.venv/
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Local development
*.local
EOF
```

### Step 5.3: Remove site/ directory from git

```bash
# If site/ is tracked
git rm -r --cached site/
```

---

## **Phase 6: Verification** (20 minutes)

### Step 6.1: Check directory structure

```bash
# From DisSysLab root, verify structure:
tree -L 2 -I '__pycache__|.venv|venv|site'
```

**Expected structure:**
```
DisSysLab/
├── README.md (updated)
├── LICENSE
├── requirements.txt
├── dsl/
├── components/
├── examples/
│   ├── README.md (updated)
│   ├── module_01_basics/
│   ├── module_02_filtering/
│   ├── ... (modules 03-11)
│   ├── helpers/ (with README)
│   └── extras/ (with README)
├── docs/
│   ├── README.md (new)
│   ├── how-it-works.md
│   ├── module-order.md
│   └── tutorials/
├── for_instructors/
│   ├── README.md (new)
│   ├── DOCUMENTATION_STRATEGY.md
│   ├── ROADMAP.md
│   └── demo_code/
└── tests/
```

### Step 6.2: Test that examples still run

```bash
# Test the first example
python3 -m examples.module_01_basics.example

# Should output:
# Results: ['HELLO!!', 'WORLD!!']
# ✓ Pipeline completed successfully!
```

### Step 6.3: Check for broken links

**Manually check these key files:**
- [ ] Root README.md - all links work
- [ ] examples/README.md - all links work
- [ ] docs/README.md - all links work
- [ ] for_instructors/README.md - all links work

### Step 6.4: Verify file movements

```bash
# Check that loose files were moved
ls examples/*.py  # Should only see __init__.py

# Check extras has files
ls examples/extras/

# Check helpers has README
ls examples/helpers/README.md

# Check for_instructors exists
ls for_instructors/
```

---

## **Phase 7: Commit Changes** (10 minutes)

### Step 7.1: Review changes

```bash
git status
git diff
```

### Step 7.2: Stage changes incrementally

```bash
# Stage in logical groups
git add examples/extras/
git add examples/helpers/README.md
git add examples/README.md
git commit -m "Reorganize examples: create extras/ and helpers/ with READMEs"

git add docs/
git commit -m "Reorganize docs: remove empty dirs, create README index"

git add for_instructors/
git commit -m "Create for_instructors directory with teaching materials"

git add README.md
git commit -m "Update root README with dual positioning (power users + students)"

git add .gitignore
git commit -m "Update .gitignore to exclude site/ and common temp files"
```

### Step 7.3: Push cleanup branch

```bash
git push origin repository-cleanup
```

### Step 7.4: Create PR or merge to main

```bash
# Option A: Create PR for review
# (Do this on GitHub)

# Option B: Merge directly if you're confident
git checkout main
git merge repository-cleanup
git push origin main
```

---

## **Phase 8: Final Touches** (Optional - Later)

These can be done after the main cleanup:

### Step 8.1: Create missing documentation

- [ ] `docs/getting-started.md` - Installation and first steps
- [ ] `docs/module-order.md` - Update or create if doesn't exist
- [ ] `CONTRIBUTING.md` - Contribution guidelines

### Step 8.2: Consistency pass

- [ ] Ensure all file names follow same convention
- [ ] Check all module READMEs for consistency
- [ ] Verify all internal links

### Step 8.3: Student testing

- [ ] Have someone unfamiliar try Module 01
- [ ] Watch where they get stuck
- [ ] Update docs based on feedback

---

## **Checklist Summary**

**Before starting:**
- [ ] Backup current state
- [ ] Create cleanup branch

**Core cleanup:**
- [ ] Create examples/extras/ directory
- [ ] Move loose .py files to extras/
- [ ] Move documentation to appropriate modules
- [ ] Create extras/README.md
- [ ] Create helpers/README.md
- [ ] Update examples/README.md
- [ ] Clean up docs/ (remove empty dirs)
- [ ] Create for_instructors/ directory
- [ ] Move instructor files
- [ ] Create docs/README.md
- [ ] Create for_instructors/README.md
- [ ] Update root README.md
- [ ] Update .gitignore

**Verification:**
- [ ] Test examples still run
- [ ] Check directory structure
- [ ] Verify all links work
- [ ] Review git diff

**Finalize:**
- [ ] Commit changes
- [ ] Push branch
- [ ] Merge to main

---

## **Time Estimates**

- Phase 1 (Backup): 5 min
- Phase 2 (Clean examples/): 45 min
- Phase 3 (Update examples/README): 15 min
- Phase 4 (Reorganize docs/): 20 min
- Phase 5 (Update root files): 15 min
- Phase 6 (Verification): 20 min
- Phase 7 (Commit): 10 min

**Total: ~2 hours**

---

## **Notes**

**Before moving files:**
- Always check if a file is referenced by a module
- Use `grep -r "filename" module_*/` to search
- When in doubt, move to extras/ rather than delete

**After cleanup:**
- Repository will be much clearer for students
- New users will have obvious starting point
- Documentation will be organized and complete

**Future work:**
- Can always create more specialized docs later
- Student feedback will guide what's needed
- This cleanup establishes the foundation

---

**Ready to start?** Begin with Phase 1: Backup & Preparation! 🚀

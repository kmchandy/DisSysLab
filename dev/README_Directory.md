# DisSysLab Directory Structure

This document describes the organization of the DisSysLab project.

## Root Directory
```
DisSysLab/
├── README.md                      # Main project documentation
├── LICENSE                        # MIT License
├── requirements.txt               # Python dependencies
├── pyproject.toml                 # Project configuration (PEP 517/518)
├── pytest.ini                     # pytest configuration
├── .gitignore                     # Git ignore rules
│
├── dsl/                           # Core framework package
├── examples/                      # Teaching modules and examples
├── docs/                          # All documentation
├── components/                    # Reusable components library
├── tests/                         # Test suite
├── scripts/                       # Utility scripts
└── dev/                           # Development and planning files
```

## Core Directories

### `dsl/` - Core Framework
The main DisSysLab package containing the framework implementation.
```
dsl/
├── __init__.py                    # Package initialization
├── decorators.py                  # @source_map, @transform_map, @sink_map
├── graph.py                       # Network topology compilation
├── agent.py                       # Agent base class
├── network.py                     # Network class
├── message.py                     # Message handling
└── blocks/                        # Pre-built node types
    ├── source.py
    ├── transform.py
    └── sink.py
```

**Purpose:** Contains all the framework code that students import and use.

### `examples/` - Teaching Modules
Progressive learning modules with complete working examples.
```
examples/
├── README.md                      # Examples overview
├── module_01_basics/              # First network (START HERE)
├── module_02_filtering/           # Message filtering with None
├── module_03_fanout/              # Broadcasting patterns
├── module_04_fanin/               # Merging patterns
├── module_05_complex_patterns/    # Combined topologies
├── module_06_numeric/             # NumPy/pandas integration
├── module_07_text_nlp/            # Text processing
├── module_08_ml/                  # Machine learning pipelines
├── module_09_ai_agents/           # AI-powered processing
├── module_10_data_pipeline/       # ETL and file I/O
├── module_11_real_world/          # Complete applications
└── theory/                        # Theoretical background (to be developed)
```

**Purpose:** Students follow these modules in sequence to learn DisSysLab.

**Each module contains:**
- `README.md` - Concepts, explanations, exercises
- `.py` files - Working example code
- `__init__.py` - Makes it a Python package

### `docs/` - Documentation
All documentation files organized by purpose.
```
docs/
├── README.md                      # Documentation index
├── MODULE_ORDER.md                # Recommended learning sequence
├── ROADMAP.md                     # Development roadmap
├── DOCUMENTATION_STRATEGY.md      # Documentation approach
├── HOW_IT_WORKS.md               # System overview for students
│
├── api/                           # API reference (to be added)
│   └── ...
│
├── guides/                        # User guides (to be added)
│   └── ...
│
└── internal/                      # Internal documentation (to be added)
    └── ...
```

**Purpose:** All `.md` documentation files live here, keeping the root clean.

### `components/` - Reusable Component Library
Pre-built sources, transforms, and sinks that students can use.
```
components/
├── __init__.py
├── sources/                       # Data sources
│   ├── rss_source.py
│   ├── list_source.py
│   └── ...
│
├── transformers/                  # Data transformers
│   ├── text_processors.py
│   ├── claude_agent.py
│   ├── prompts.py                # AI prompt library
│   └── ...
│
└── sinks/                         # Data consumers
    ├── file_writer.py
    ├── display.py
    └── ...
```

**Purpose:** Reusable building blocks students can compose into networks.

### `tests/` - Test Suite
Unit and integration tests for the framework.
```
tests/
├── __init__.py
├── test_decorators.py             # Decorator tests
├── test_graph.py                  # Network compilation tests
├── test_network.py                # End-to-end tests
└── ...
```

**Purpose:** Ensures framework reliability and correctness.

### `scripts/` - Utility Scripts
Scripts for project maintenance and organization.
```
scripts/
├── README.md
├── reorganize_examples.py         # Organize examples structure
└── cleanup_for_release.py         # Clean directory for release
```

**Purpose:** Tools for maintaining project organization.

### `dev/` - Development Files
Planning documents and development notes (this directory).
```
dev/
├── README.md                      # Development files overview
├── README_Directory.md            # This file - directory structure
├── README_Makefile.md             # Build system documentation
├── implementation_plan.md         # Implementation roadmap
├── Makefile                       # Build automation
└── mkdocs.yml                     # MkDocs configuration (if using)
```

**Purpose:** Context for contributors and maintainers, not for students.

## Files Not in Repository

These are generated files and should be in `.gitignore`:
```
# Build artifacts
__pycache__/                       # Python bytecode cache
*.pyc, *.pyo                       # Compiled Python files
*.egg-info/                        # Package metadata (e.g., dsl.egg-info/)
build/, dist/                      # Distribution builds
site/                              # MkDocs output

# Development
venv/, env/                        # Virtual environments
.pytest_cache/                     # pytest cache
.coverage                          # Coverage data

# IDE
.vscode/, .idea/                   # IDE configurations
*.swp, *.swo                       # Editor temp files

# OS
.DS_Store                          # macOS
Thumbs.db                          # Windows
```

## Key Design Principles

1. **Clean root** - Only essential files in root directory
2. **Clear separation** - Framework (dsl/), examples, docs, components
3. **Standard conventions** - Follow Python ecosystem patterns
4. **Student-focused** - Structure optimized for learning
5. **Self-documenting** - Directory names explain their purpose

## For Students

When browsing the repository:
1. **Start with:** `README.md` (root)
2. **Learn from:** `examples/module_01_basics/`
3. **Follow:** `docs/MODULE_ORDER.md`
4. **Reference:** `docs/HOW_IT_WORKS.md`
5. **Explore:** `components/` for reusable parts

## For Contributors

When contributing to the project:
1. **Read:** `docs/ROADMAP.md` for development direction
2. **Understand:** `docs/DOCUMENTATION_STRATEGY.md`
3. **Review:** `dev/` directory for development context
4. **Test:** Run `pytest` before submitting changes
5. **Document:** Update relevant docs with your changes

---

*Last updated: February 2026*
*This file should be updated whenever directory structure changes significantly.*
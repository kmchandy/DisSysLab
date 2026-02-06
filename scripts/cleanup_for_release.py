#!/usr/bin/env python3
"""
Script to clean up DisSysLab directory structure for release.

This script:
1. Organizes documentation files into proper locations
2. Moves development/planning files to a dev/ directory
3. Cleans up the root directory
4. Creates a clean, professional structure

Usage:
    python3 cleanup_for_release.py [--dry-run]
    
    --dry-run: Show what would be done without actually moving files
"""

import os
import shutil
import argparse
from pathlib import Path


def get_reorganization_plan():
    """Define where each file/directory should go."""
    return {
        # Files to keep in root (clean, essential files only)
        "keep_in_root": [
            "README.md",
            "LICENSE",
            "requirements.txt",
            "pyproject.toml",
            "pytest.ini",
            "setup.py",  # if it exists
            ".gitignore",  # if it exists
            "ROADMAP.md",
            "DOCUMENTATION_STRATEGY.md",
            "MODULE_ORDER.md",
        ],

        # Directories to keep in root
        "keep_dirs": [
            "dsl",           # Core framework
            "examples",      # Example modules
            "docs",          # Documentation
            "tests",         # Test suite
            "components",    # Reusable components
        ],

        # Move to dev/ directory (development/planning files)
        "move_to_dev": [
            "implementation_plan.md",
            "teaching_plan.md",
            "teaching_stateful_sources.md",
            "README_Directory.md",
            "README_Makefile.md",
            "PLAN_FOR_DIS_SYS_LAB.pages",
            "Makefile",  # Keep if used for build, otherwise move to dev
            "mkdocs.yml",  # Keep if using MkDocs, otherwise move to dev
        ],

        # Move to theory/ or keep organized
        "theory_files": [
            "theory",  # Already a directory
        ],

        # Build artifacts and temporary files to ignore/keep hidden
        "build_artifacts": [
            "__pycache__",
            "dsl.egg-info",
            "site",  # MkDocs build output
            "venv",
            ".pytest_cache",
            "*.pyc",
            "*.pyo",
            "*.egg-info",
        ],

        # Scripts directory
        "move_to_scripts": [
            "reorganize_examples.py",
        ],
    }


def create_clean_structure(base_path, dry_run=False):
    """Create the clean directory structure."""
    print("Creating clean directory structure...\n")

    dirs_to_create = [
        "dev",           # Development and planning files
        "scripts",       # Utility scripts
        "docs/api",      # API documentation
        "docs/guides",   # User guides
        "docs/internal",  # Internal documentation
    ]

    for dir_path in dirs_to_create:
        full_path = base_path / dir_path
        if dry_run:
            print(f"  [DRY RUN] Would create: {dir_path}/")
        else:
            full_path.mkdir(parents=True, exist_ok=True)
            print(f"  ✓ Created: {dir_path}/")


def move_files_to_dev(base_path, files_to_move, dry_run=False):
    """Move development/planning files to dev/ directory."""
    print("\nMoving development files to dev/...\n")

    dev_path = base_path / "dev"

    for filename in files_to_move:
        source = base_path / filename

        if not source.exists():
            continue

        dest = dev_path / filename

        if dry_run:
            print(f"  [DRY RUN] Would move: {filename} → dev/{filename}")
        else:
            if source.is_file():
                shutil.move(str(source), str(dest))
                print(f"  ✓ Moved: {filename} → dev/{filename}")
            elif source.is_dir():
                # For directories, move contents
                print(
                    f"  ℹ Directory {filename} kept in place (review manually)")


def move_scripts(base_path, scripts, dry_run=False):
    """Move utility scripts to scripts/ directory."""
    print("\nMoving scripts to scripts/...\n")

    scripts_path = base_path / "scripts"

    for script_name in scripts:
        source = base_path / script_name

        if not source.exists():
            continue

        dest = scripts_path / script_name

        if dry_run:
            print(
                f"  [DRY RUN] Would move: {script_name} → scripts/{script_name}")
        else:
            shutil.move(str(source), str(dest))
            print(f"  ✓ Moved: {script_name} → scripts/{script_name}")


def create_dev_readme(base_path, dry_run=False):
    """Create README for dev/ directory."""
    content = """# Development Files

This directory contains planning documents, notes, and development materials that aren't part of the main documentation.

## Contents

- **implementation_plan.md** - Implementation roadmap and technical plans
- **teaching_plan.md** - Course design and teaching strategy
- **teaching_stateful_sources.md** - Notes on teaching stateful concepts
- **README_Directory.md** - Directory structure documentation
- **README_Makefile.md** - Build system documentation
- **PLAN_FOR_DIS_SYS_LAB.pages** - Early planning documents

## For Contributors

These files provide context for development decisions and future directions. If you're contributing to DisSysLab, reading these files will help you understand the design philosophy and roadmap.

## Not for Students

Students learning DisSysLab should start with the main [README.md](../README.md) and [MODULE_ORDER.md](../MODULE_ORDER.md).
"""

    output_path = base_path / "dev" / "README.md"

    if dry_run:
        print(f"\n  [DRY RUN] Would create: dev/README.md")
    else:
        with open(output_path, 'w') as f:
            f.write(content)
        print(f"\n  ✓ Created: dev/README.md")


def create_scripts_readme(base_path, dry_run=False):
    """Create README for scripts/ directory."""
    content = """# Utility Scripts

This directory contains utility scripts for managing the DisSysLab project.

## Scripts

- **reorganize_examples.py** - Reorganizes the examples directory structure

## Usage

Run scripts from the DisSysLab root directory:
```bash
python3 scripts/script_name.py [options]
```

For help on any script:
```bash
python3 scripts/script_name.py --help
```
"""

    output_path = base_path / "scripts" / "README.md"

    if dry_run:
        print(f"  [DRY RUN] Would create: scripts/README.md")
    else:
        with open(output_path, 'w') as f:
            f.write(content)
        print(f"  ✓ Created: scripts/README.md")


def create_gitignore_if_missing(base_path, dry_run=False):
    """Create .gitignore if it doesn't exist."""
    gitignore_path = base_path / ".gitignore"

    if gitignore_path.exists():
        print("\n  ℹ .gitignore already exists")
        return

    content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Testing
.pytest_cache/
.coverage
htmlcov/

# MkDocs
site/

# OS
.DS_Store
Thumbs.db

# Distribution
*.tar.gz
*.whl
"""

    if dry_run:
        print(f"\n  [DRY RUN] Would create: .gitignore")
    else:
        with open(gitignore_path, 'w') as f:
            f.write(content)
        print(f"\n  ✓ Created: .gitignore")


def show_final_structure(base_path):
    """Show what the final directory structure looks like."""
    print("\n" + "=" * 70)
    print("FINAL DIRECTORY STRUCTURE")
    print("=" * 70)
    print("""
DisSysLab/
├── README.md                      # Main project README
├── LICENSE                        # License file
├── MODULE_ORDER.md               # Learning sequence
├── ROADMAP.md                    # Development roadmap
├── DOCUMENTATION_STRATEGY.md     # Documentation plan
├── requirements.txt              # Python dependencies
├── pyproject.toml               # Project configuration
├── pytest.ini                   # Test configuration
├── .gitignore                   # Git ignore rules
│
├── dsl/                         # Core framework code
│   ├── __init__.py
│   ├── decorators.py
│   ├── graph.py
│   └── ...
│
├── examples/                    # Learning modules
│   ├── README.md
│   ├── module_01_basics/
│   ├── module_02_filtering/
│   └── ...
│
├── docs/                        # Documentation
│   ├── HOW_IT_WORKS.md
│   ├── api/                    # API reference
│   ├── guides/                 # User guides
│   └── internal/               # Internal docs
│
├── components/                  # Reusable components
│   ├── sources/
│   ├── transformers/
│   └── sinks/
│
├── tests/                       # Test suite
│   └── ...
│
├── scripts/                     # Utility scripts
│   ├── README.md
│   └── reorganize_examples.py
│
├── dev/                         # Development files
│   ├── README.md
│   ├── implementation_plan.md
│   └── ...
│
└── theory/                      # Theoretical background
    └── ...

Hidden (not in repo):
├── __pycache__/
├── venv/
├── site/
└── *.egg-info/
""")


def main():
    parser = argparse.ArgumentParser(
        description="Clean up DisSysLab directory structure for release"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually making changes"
    )
    parser.add_argument(
        "--base-path",
        type=Path,
        default=Path.cwd(),
        help="Base path of DisSysLab project (default: current directory)"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("DisSysLab Directory Cleanup for Release")
    print("=" * 70)

    if args.dry_run:
        print("\n*** DRY RUN MODE - No changes will be made ***\n")

    print(f"\nBase path: {args.base_path.absolute()}\n")

    plan = get_reorganization_plan()

    # Confirm before proceeding
    if not args.dry_run:
        print("This will reorganize your directory structure:")
        print("  • Move development files to dev/")
        print("  • Move scripts to scripts/")
        print("  • Create .gitignore if missing")
        print("  • Create README files for new directories")
        print()
        response = input("Proceed with cleanup? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            return

    # Execute cleanup steps
    create_clean_structure(args.base_path, args.dry_run)
    move_files_to_dev(args.base_path, plan["move_to_dev"], args.dry_run)
    move_scripts(args.base_path, plan["move_to_scripts"], args.dry_run)
    create_dev_readme(args.base_path, args.dry_run)
    create_scripts_readme(args.base_path, args.dry_run)
    create_gitignore_if_missing(args.base_path, args.dry_run)

    print("\n" + "=" * 70)
    if args.dry_run:
        print("DRY RUN COMPLETE - No changes were made")
        print("\nRun without --dry-run to perform cleanup")
        show_final_structure(args.base_path)
    else:
        print("CLEANUP COMPLETE!")
        print("\nNext steps:")
        print("  1. Review the changes")
        print("  2. Update any absolute paths in documentation")
        print("  3. Test that imports still work")
        print("  4. Run: python3 -m pytest tests/")
        print("  5. Commit the cleaned structure")
        show_final_structure(args.base_path)
    print("=" * 70)


if __name__ == "__main__":
    main()

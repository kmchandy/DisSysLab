#!/usr/bin/env python3
"""
Script to reorganize DisSysLab examples and documentation.

This script:
1. Organizes the examples/ directory with clear structure
2. Creates a MODULE_ORDER.md file documenting the learning sequence
3. Ensures documentation files are in the right place
4. Creates placeholder READMEs for modules that need them

Usage:
    python3 reorganize_modules.py [--dry-run]
    
    --dry-run: Show what would be done without actually moving files
"""

import os
import shutil
import argparse
from pathlib import Path

# Define the structure for examples directory
EXAMPLES_STRUCTURE = {
    "module_01_basics": {
        "description": "Introduction to DisSysLab - First network, basic patterns",
        "topics": ["Source, Transform, Sink nodes", "Simple pipeline", "Message flow"],
    },
    "module_02_filtering": {
        "description": "Message Filtering - Returning None to drop messages",
        "topics": ["Conditional filtering", "None-dropping behavior", "Pattern matching"],
    },
    "module_03_fanout": {
        "description": "Fanout Pattern - Broadcasting to multiple destinations",
        "topics": ["One source to many destinations", "Parallel processing", "Independent branches"],
    },
    "module_04_fanin": {
        "description": "Fanin Pattern - Merging multiple sources",
        "topics": ["Multiple sources to one destination", "Message merging", "Priority handling"],
    },
    "module_05_complex_patterns": {
        "description": "Complex Topologies - Combining patterns",
        "topics": ["Fanin + Fanout", "Diamond patterns", "Multi-stage pipelines"],
    },
    "module_06_numeric": {
        "description": "Numeric Processing - NumPy and pandas integration",
        "topics": ["Array processing", "DataFrame operations", "Vectorized functions"],
    },
    "module_07_text_nlp": {
        "description": "Text Processing - NLP pipelines",
        "topics": ["Text cleaning", "Tokenization", "Language processing"],
    },
    "module_08_ml": {
        "description": "Machine Learning - scikit-learn integration",
        "topics": ["Model training", "Prediction pipelines", "Feature engineering"],
    },
    "module_09_ai_agents": {
        "description": "AI Agents - Using Claude for processing",
        "topics": ["AI-powered transforms", "Prompt engineering", "Response parsing"],
    },
    "module_10_data_pipeline": {
        "description": "Data Pipelines - File I/O and ETL",
        "topics": ["Reading files", "Data transformation", "Writing results"],
    },
    "module_11_real_world": {
        "description": "Real-World Applications - Complete projects",
        "topics": ["RSS aggregation", "Social media analysis", "Production patterns"],
    },
}

# Learning sequence for MODULE_ORDER.md
LEARNING_SEQUENCE = [
    ("examples/module_01_basics", "Introduction to DisSysLab",
     "Build your first network in 5 minutes. Learn Source, Transform, and Sink nodes."),

    ("examples/module_02_filtering", "Message Filtering",
     "Learn how returning None drops messages. Build conditional filters."),

    ("examples/module_03_fanout", "Fanout Pattern",
     "Broadcast messages to multiple destinations. Process in parallel."),

    ("examples/module_04_fanin", "Fanin Pattern",
     "Merge multiple sources into one processor. Handle diverse inputs."),

    ("examples/module_05_complex_patterns", "Complex Topologies",
     "Combine fanin and fanout. Build sophisticated graph structures."),

    ("examples/module_06_numeric", "Numeric Processing",
     "Integrate NumPy and pandas. Process arrays and DataFrames."),

    ("examples/module_07_text_nlp", "Text Processing",
     "Build NLP pipelines. Clean, tokenize, and analyze text."),

    ("examples/module_08_ml", "Machine Learning",
     "Create ML pipelines with scikit-learn. Train and predict."),

    ("examples/module_09_ai_agents", "AI Agents",
     "Use Claude for intelligent processing. Master prompt engineering."),

    ("examples/module_10_data_pipeline", "Data Pipelines",
     "Build ETL systems. Read, transform, and write data."),

    ("examples/module_11_real_world", "Real-World Applications",
     "Complete projects: RSS aggregators, social media analysis, and more."),
]


def create_examples_structure(base_path, dry_run=False):
    """Create the organized examples directory structure."""
    print("Creating examples directory structure...")

    examples_path = base_path / "examples"

    for module_name, module_info in EXAMPLES_STRUCTURE.items():
        module_path = examples_path / module_name

        if dry_run:
            print(f"  [DRY RUN] Would create: {module_path}")
        else:
            module_path.mkdir(parents=True, exist_ok=True)
            print(f"  Created: {module_path}")

            # Create __init__.py
            init_file = module_path / "__init__.py"
            if not init_file.exists():
                init_file.write_text("")
                print(f"    Created: __init__.py")

            # Create placeholder README if it doesn't exist
            readme_file = module_path / "README.md"
            if not readme_file.exists():
                readme_content = f"""# {module_name.replace('_', ' ').title()}

{module_info['description']}

## Topics Covered

"""
                for topic in module_info['topics']:
                    readme_content += f"- {topic}\n"

                readme_content += """

## Examples

[To be added]

## Running the Examples
```bash
python3 -m examples.{module_name}.example_name
```

## Key Concepts

[To be documented]

## Exercises

[To be added]

---

*See [MODULE_ORDER.md](../../MODULE_ORDER.md) for the complete learning sequence.*
""".replace("{module_name}", module_name)

                if dry_run:
                    print(f"    [DRY RUN] Would create: README.md")
                else:
                    readme_file.write_text(readme_content)
                    print(f"    Created: README.md")


def create_module_order(base_path, dry_run=False):
    """Create MODULE_ORDER.md file documenting learning sequence."""
    print("\nCreating MODULE_ORDER.md...")

    content = """# DisSysLab Module Learning Sequence

This document defines the recommended order for working through DisSysLab modules.

## Quick Start

**New to DisSysLab?** Start with `examples/module_01_basics/` - you'll build your first distributed system in 5 minutes!

## Learning Path

"""

    for i, (module_path, title, description) in enumerate(LEARNING_SEQUENCE, 1):
        content += f"### Module {i}: {title}\n\n"
        content += f"**Path:** `{module_path}/`\n\n"
        content += f"{description}\n\n"
        content += f"**Read:** See the [module README]({module_path}/README.md) for complete details and examples.\n\n"
        content += "---\n\n"

    content += """
## How to Use This Guide

1. **Start at Module 1** - Build your first network in 5 minutes
2. **Progress sequentially** - Each module builds on previous concepts
3. **Read the README** - Each module has detailed explanations
4. **Run the examples** - Execute code to see it work
5. **Do the exercises** - Practice problems in each module
6. **Experiment** - Modify examples to understand behavior
7. **Build your own** - After Module 5, try creating your own applications

## Module Categories

### Fundamentals (Modules 1-5)
Core concepts and patterns you need to know:
- Basic node types and message flow
- Filtering and conditional logic
- Network topologies (fanin, fanout)
- Complex graph structures

### Integration (Modules 6-9)
Connecting DisSysLab with the Python ecosystem:
- NumPy and pandas for data science
- NLP libraries for text processing
- scikit-learn for machine learning
- AI agents with Claude

### Applications (Modules 10-11)
Building real systems:
- Data pipelines and ETL
- Complete production applications
- Best practices and patterns

## Prerequisites

- Python 3.8+
- Basic Python knowledge (functions, classes, lists, dicts)
- No distributed systems experience required!

## Additional Resources

- **[Quick Start](README.md#quick-start)** - Get running in 5 minutes
- **[How It Works](docs/HOW_IT_WORKS.md)** - Understand the system
- **[API Reference](docs/api/)** - Complete documentation
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues
- **[Architecture](DOCUMENTATION_STRATEGY.md)** - System design

## Getting Help

- Check the module README first
- Look at working examples in the module
- Read [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) for conceptual understanding
- Check [docs/troubleshooting.md](docs/troubleshooting.md) for common errors
- Look at other modules for patterns

## Contributing

Want to add a module or improve existing ones? See [CONTRIBUTING.md](CONTRIBUTING.md) (to be created).

---

*Last updated: January 2026*
*Part of DisSysLab - A teaching framework for distributed systems*
"""

    output_path = base_path / "MODULE_ORDER.md"

    if dry_run:
        print(f"  [DRY RUN] Would create: {output_path}")
        print("  Content preview:")
        print(content[:500] + "...\n")
    else:
        with open(output_path, 'w') as f:
            f.write(content)
        print(f"  ✓ Created: {output_path}")


def verify_documentation_files(base_path, dry_run=False):
    """Verify that key documentation files exist."""
    print("\nVerifying documentation files...")

    required_docs = [
        ("ROADMAP.md", "✓ Found"),
        ("DOCUMENTATION_STRATEGY.md", "✓ Found"),
        ("docs/HOW_IT_WORKS.md", "Check location"),
    ]

    for filename, status in required_docs:
        filepath = base_path / filename
        if filepath.exists():
            print(f"  ✓ {filename} exists")
        else:
            print(f"  ✗ {filename} NOT FOUND")
            if not dry_run:
                print(f"    → Please add this file manually")


def create_examples_readme(base_path, dry_run=False):
    """Create README.md for examples directory."""
    print("\nCreating examples/README.md...")

    content = """# DisSysLab Examples

This directory contains progressive learning modules for DisSysLab.

## Getting Started

**New to DisSysLab?**

1. Read the main [README.md](../README.md) for installation
2. Start with [module_01_basics](module_01_basics/) 
3. Follow the [MODULE_ORDER.md](../MODULE_ORDER.md) sequence

## Module Structure

Each module contains:
- **README.md** - Concepts, explanations, and exercises
- **Example files** - Working code you can run
- **__init__.py** - Makes it a Python package

## Running Examples
```bash
# From the DisSysLab root directory
python3 -m examples.module_01_basics.example_name
```

## Module Overview

1. **module_01_basics** - Your first network (START HERE!)
2. **module_02_filtering** - Conditional message dropping
3. **module_03_fanout** - Broadcast to multiple destinations
4. **module_04_fanin** - Merge multiple sources
5. **module_05_complex_patterns** - Advanced topologies
6. **module_06_numeric** - NumPy and pandas
7. **module_07_text_nlp** - Text processing pipelines
8. **module_08_ml** - Machine learning integration
9. **module_09_ai_agents** - AI-powered processing
10. **module_10_data_pipeline** - ETL and file I/O
11. **module_11_real_world** - Complete applications

## Learning Path

See [MODULE_ORDER.md](../MODULE_ORDER.md) for the complete recommended sequence.

## Need Help?

- Each module README has troubleshooting tips
- See [docs/HOW_IT_WORKS.md](../docs/HOW_IT_WORKS.md) for system overview
- Check [docs/troubleshooting.md](../docs/troubleshooting.md) for common issues

---

*Ready to start? Go to [module_01_basics](module_01_basics/)!*
"""

    output_path = base_path / "examples" / "README.md"

    if dry_run:
        print(f"  [DRY RUN] Would create: {output_path}")
    else:
        with open(output_path, 'w') as f:
            f.write(content)
        print(f"  ✓ Created: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Organize DisSysLab examples and documentation structure"
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
    print("DisSysLab Examples Organization Script")
    print("=" * 70)

    if args.dry_run:
        print("\n*** DRY RUN MODE - No changes will be made ***\n")

    print(f"\nBase path: {args.base_path.absolute()}")
    print(f"Examples path: {args.base_path.absolute() / 'examples'}")

    # Confirm before proceeding
    if not args.dry_run:
        response = input("\nProceed with organization? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            return

    # Execute organization steps
    create_examples_structure(args.base_path, args.dry_run)
    create_examples_readme(args.base_path, args.dry_run)
    create_module_order(args.base_path, args.dry_run)
    verify_documentation_files(args.base_path, args.dry_run)

    print("\n" + "=" * 70)
    if args.dry_run:
        print("DRY RUN COMPLETE - No changes were made")
        print("Run without --dry-run to perform organization")
    else:
        print("ORGANIZATION COMPLETE!")
        print("\nWhat was created:")
        print("  ✓ examples/module_01_basics/ through module_11_real_world/")
        print("  ✓ README.md in each module (as placeholders)")
        print("  ✓ examples/README.md")
        print("  ✓ MODULE_ORDER.md")
        print("\nNext steps:")
        print("  1. Move your existing example files into appropriate modules")
        print("  2. Update module READMEs with specific content")
        print("  3. Test that examples run: python3 -m examples.module_01_basics.example")
        print("  4. Follow MODULE_ORDER.md to verify learning sequence")
        print("\nVerify documentation:")
        print("  • ROADMAP.md")
        print("  • DOCUMENTATION_STRATEGY.md")
        print("  • docs/HOW_IT_WORKS.md")
    print("=" * 70)


if __name__ == "__main__":
    main()

"""A Python role: one class in one file (spec section 4.3).

Loading a role file, in order, each step visible:

1. ``needs:`` -- every package the front matter lists must be installed.
   Checked with ``importlib.util.find_spec``, without importing anything;
   a missing one stops the run before it starts, naming the agent and the
   ``pip install`` line.
2. The file is loaded as a module, with its own folder importable, so a
   role can import the office's helper modules (``_signal_common.py``).
3. The module must define exactly one class (classes it imports do not
   count). No DisSysLab base class is needed or expected.
4. The class is constructed with the arguments written in the office
   file: ``Clerk: clerk(limit=50)`` calls ``Clerk(limit=50)``.

The instance is the role: calling it with one message gives its reply,
a dict (annotator) or a list of dicts (author).
"""

from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from dissyslab.agents.role_agent import Call
from dissyslab.office.frontmatter import FrontMatter


class RoleLoadError(Exception):
    """A Python role, source or sink that cannot be loaded, and why."""


def missing_packages(front_matter: FrontMatter) -> list[str]:
    """The packages in ``needs:`` that are not installed. Imports nothing."""
    missing: list[str] = []
    for package in front_matter.needs:
        try:
            found = importlib.util.find_spec(package) is not None
        except (ImportError, ValueError):  # a dotted name whose parent is missing
            found = False
        if not found:
            missing.append(package)
    return missing


def _load_module(path: Path) -> ModuleType:
    folder = str(path.parent.resolve())
    if folder not in sys.path:
        sys.path.insert(0, folder)  # so the role can import its folder's helpers
    name = f"dissyslab_office_{path.parent.parent.name}_{path.parent.name}_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RoleLoadError(f"{path} cannot be loaded as Python.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def the_one_class(module: ModuleType, path: Path) -> type:
    """The single class ``module`` defines; an error if there are none or several."""
    classes = [
        obj for obj in vars(module).values()
        if inspect.isclass(obj) and obj.__module__ == module.__name__
    ]
    if len(classes) != 1:
        found = ", ".join(c.__name__ for c in classes) or "none"
        raise RoleLoadError(
            f"{path.name} must define exactly one class; it defines {found}."
        )
    return classes[0]


def python_instance(path: Path, front_matter: FrontMatter, args: dict[str, Any]) -> Any:
    """Load ``path`` and construct its one class with ``args``."""
    missing = missing_packages(front_matter)
    if missing:
        raise RoleLoadError(
            f"{path.name} needs {', '.join(missing)}, which "
            f"{'is' if len(missing) == 1 else 'are'} not installed. "
            f"Run: pip install {' '.join(missing)}"
        )
    cls = the_one_class(_load_module(path), path)
    try:
        return cls(**args)
    except TypeError as exc:
        raise RoleLoadError(f"{cls.__name__}({', '.join(args)}) failed: {exc}") from None


def python_call(path: Path, front_matter: FrontMatter, args: dict[str, Any]) -> Call:
    """A ``Call`` for a Python role: its instance, which is called per message."""
    instance = python_instance(path, front_matter, args)
    if not callable(instance):
        raise RoleLoadError(f"{type(instance).__name__} in {path.name} has no __call__.")
    call: Call = instance
    return call

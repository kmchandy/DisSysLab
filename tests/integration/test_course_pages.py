"""The course pages students open first agree with the code.

course/setup.html, microcourse.html, OfficeToolkit.html and lab1.html quote
office files, commands and output. Each section here checks one kind of
quotation against the thing it quotes, so a page cannot quietly drift from
the release (lab1.html's own files are checked in tests/e2e/test_examples.py).
"""

from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
COURSE = REPO / "course"
GALLERY = REPO / "dissyslab" / "gallery"
STUDENT_PAGES = ["index.html", "setup.html", "microcourse.html", "OfficeToolkit.html",
                 "lab1.html"]


def page(name: str) -> str:
    return (COURSE / name).read_text(encoding="utf-8")


def text(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", fragment))


def pre_blocks(source: str) -> list[str]:
    return [text(b) for b in re.findall(r"<pre[^>]*>(.*?)</pre>", source, re.S)]


def dsl(*args: str, cwd: Path) -> str:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    env["PYTHONPATH"] = os.pathsep.join([str(REPO)] + ([env["PYTHONPATH"]]
                                                       if env.get("PYTHONPATH") else []))
    done = subprocess.run(
        [sys.executable, "-c",
         "import sys; from dissyslab.cli import main; sys.exit(main(sys.argv[1:]))", *args],
        cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", timeout=120)
    return done.stdout + done.stderr


# ── 1. Links between the pages go somewhere ────────────────────────────────


@pytest.mark.parametrize("name", STUDENT_PAGES)
def test_every_relative_link_resolves(name):
    for href in re.findall(r'href="([^"]+)"', page(name)):
        if re.match(r"(https?:|mailto:|#)", href):
            continue
        target = (COURSE / href.split("#")[0]).resolve()
        assert target.exists(), f"{name} links to {href}, which does not exist"


def test_the_old_microcourse_address_still_works():
    redirect = (REPO / "office_microcourse.html").read_text(encoding="utf-8")
    assert 'url=course/microcourse.html' in redirect
    assert (COURSE / "microcourse.html").exists()


# ── 2. The micro-course quotes the gallery as it is ────────────────────────


def test_every_office_file_on_a_slide_is_in_the_gallery():
    source = page("microcourse.html")
    quoted = re.findall(r'<div class="file">([\w/]+/office\.md)[^<]*</div>\s*<pre>(.*?)</pre>',
                        source, re.S)
    assert len(quoted) >= 3
    for path, block in quoted:
        office = path.split("/")[0]
        real = GALLERY / office / path.split("/", 1)[1]
        if not real.exists():  # a nested office, inside its parent
            real = next(GALLERY.glob(f"*/{path}"))
        lines = {ln.strip() for ln in real.read_text(encoding="utf-8").splitlines()}
        for line in text(block).splitlines():
            line = line.split("#")[0].strip()
            if line:
                assert line in lines, f"{path} on a slide shows {line!r}; the gallery does not"


def test_the_dsl_check_output_on_the_slide_is_what_dsl_check_prints(tmp_path):
    shown = [b for b in pre_blocks(page("microcourse.html")) if b.startswith("$ dsl check")]
    assert len(shown) == 2
    office = tmp_path / "my_filter"
    shutil.copytree(GALLERY / "org_news_filter", office)
    md = office / "office.md"
    md.write_text(md.read_text(encoding="utf-8").replace(
        "Rex.yes -> console_printer", "Rex.yes -> console_printr"), encoding="utf-8")
    role = office / "roles" / "topic_filter.md"
    role.write_text(role.read_text(encoding="utf-8").replace(
        "out: on_topic (yes | no)", "out: on_topic (yes | no | maybe)"), encoding="utf-8")
    first = dsl("check", "my_filter", cwd=tmp_path)
    assert shown[0].split("\n", 1)[1].strip() in first, first
    md.write_text(md.read_text(encoding="utf-8").replace("console_printr", "console_printer"),
                  encoding="utf-8")
    second = dsl("check", "my_filter", cwd=tmp_path)
    assert shown[1].split("\n", 1)[1].strip() in second, second


def test_the_microcourse_names_only_commands_and_flags_that_exist():
    source = text(page("microcourse.html"))
    for gone in (r"--trace", r"--resume", r"--prompt", r"dsl checks\b", r"\brecord\b",
                 r"\bselect\b", r"\bmatch\b"):
        assert not re.search(gone, source), f"the micro-course still mentions {gone!r}"


# The offices behind the slides tagged "illustration" (not in the gallery).
ILLUSTRATIONS = Path(__file__).resolve().parent / "microcourse_offices"


def test_every_role_or_sink_file_on_a_slide_is_real():
    """A slide headed roles/x or sinks/x quotes the gallery's file, or an
    illustration's, line for line."""
    source = page("microcourse.html")
    quoted = re.findall(r'<div class="file">((?:roles|sinks)/\w+\.(?:py|md))[^<]*(?:<span[^>]*>[^<]*</span>)?'
                        r'[^<]*</div>\s*<pre>(.*?)</pre>', source, re.S)
    assert len(quoted) >= 5
    for path, block in quoted:
        files = list(GALLERY.glob(f"*/{path}")) + list(ILLUSTRATIONS.glob(f"*/{path}"))
        assert files, f"a slide quotes {path}, which neither the gallery nor an illustration has"
        lines = {ln.strip() for f in files for ln in f.read_text(encoding="utf-8").splitlines()}
        for line in text(block).splitlines():
            if line.strip():
                assert line.strip() in lines, f"{path} on a slide shows {line.strip()!r}; the file does not"


def _run(office: Path, script: Path | None = None) -> str:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    env["PYTHONPATH"] = os.pathsep.join([str(REPO)] + ([env["PYTHONPATH"]]
                                                       if env.get("PYTHONPATH") else []))
    if script is not None:
        env["DSL_BACKEND_MODULE"] = "tests.e2e.fake_model"
        env["DSL_FAKE_SCRIPT"] = str(script)
    done = subprocess.run(
        [sys.executable, "-c",
         "import sys; from dissyslab.cli import main; sys.exit(main(sys.argv[1:]))", "run", "."],
        cwd=office, env=env, capture_output=True, text=True, encoding="utf-8", timeout=120)
    return done.stdout + done.stderr


def test_every_line_of_output_on_the_slides_is_what_dsl_prints(tmp_path):
    """The dark boxes on the slides are output. Run every office they come
    from and check each line, whitespace aside; '...' marks a cut."""
    for name in ("requests", "refunds", "felix", "booking"):
        shutil.copytree(ILLUSTRATIONS / name, tmp_path / name)
    # The two that use gallery roles take them from the gallery, so they cannot drift.
    (tmp_path / "refunds" / "roles").mkdir()
    shutil.copy(GALLERY / "returns_desk" / "roles" / "clerk.py", tmp_path / "refunds" / "roles")
    (tmp_path / "felix" / "roles").mkdir()
    shutil.copy(GALLERY / "org_news_filter" / "roles" / "topic_filter.md",
                tmp_path / "felix" / "roles")
    shutil.copytree(GALLERY / "returns_desk", tmp_path / "desk",
                    ignore=shutil.ignore_patterns("__pycache__"))
    printed = " ".join([
        _run(tmp_path / "requests", tmp_path / "requests" / "script.json"),
        _run(tmp_path / "refunds"),
        _run(tmp_path / "felix", tmp_path / "felix" / "script.json"),
        _run(tmp_path / "booking"),
        _run(tmp_path / "desk"),
        dsl("check", str(GALLERY / "car_dealer"), cwd=tmp_path),
    ])
    printed = re.sub(r"\s+", " ", printed)
    shown = re.findall(r'<pre class="out"[^>]*>(.*?)</pre>', page("microcourse.html"), re.S)
    assert len(shown) >= 6
    for block in shown:
        for line in text(block).splitlines():
            if line.strip().startswith("$"):
                continue
            for piece in line.split("..."):
                piece = re.sub(r"\s+", " ", piece).strip(" ,")
                if len(piece) > 3:
                    assert piece in printed, f"a slide shows {piece!r}, which no run printed"


# ── 3. Setup quotes the getting-started guide and the gallery ──────────────


def test_setup_quotes_only_what_the_guide_or_the_gallery_says():
    guide = (REPO / "docs" / "GETTING_STARTED.md").read_text(encoding="utf-8")
    desk = (GALLERY / "returns_desk" / "office.md").read_text(encoding="utf-8")
    for block in pre_blocks(page("setup.html")):
        for line in block.splitlines():
            line = line.split("#")[0].rstrip()
            if line.strip():
                assert line.strip() in guide or line.strip() in desk, (
                    f"setup.html shows {line!r}, which neither GETTING_STARTED nor "
                    "returns_desk/office.md has")


# ── 4. The toolkit's lists are the package's lists ─────────────────────────


def _toolkit_section(anchor: str) -> str:
    source = page("OfficeToolkit.html")
    start = source.index(f'id="{anchor}"')
    end = source.find("<h2", start + 1)
    return source[start:end if end != -1 else len(source)]


def test_the_toolkit_lists_every_builtin_role_and_no_other():
    listed = set(re.findall(r"<tr><td><code>(\w+)</code></td>", _toolkit_section("roles")))
    shipped = {p.stem for p in (REPO / "dissyslab" / "roles").iterdir()
               if p.suffix in (".md", ".py") and p.stem not in ("README", "__init__")}
    assert listed == shipped


def test_the_toolkit_lists_every_gallery_office_and_no_other():
    listed = set(re.findall(r"<tr><td><code>(\w+)</code></td>", _toolkit_section("gallery")))
    shipped = {p.parent.name for p in GALLERY.glob("*/office.md")}
    assert listed == shipped


def test_every_source_and_sink_the_toolkit_names_exists():
    from dissyslab.office.utils import SINK_REGISTRY, SOURCE_REGISTRY
    named = set(re.findall(r"<code>(\w+)</code>", _toolkit_section("io")))
    assert named - set(SOURCE_REGISTRY) - set(SINK_REGISTRY) == set()


def test_every_model_name_the_toolkit_gives_is_accepted():
    from dissyslab.backends import backend_names
    named = set(re.findall(r"<code>(\w+)</code>", _toolkit_section("models")))
    named -= {"ai", "_precise", "_creative", "dsl"}
    assert named and named <= set(backend_names()), named - set(backend_names())


def test_every_dsl_command_the_toolkit_names_exists():
    commands = set(re.findall(r"<code>dsl ([a-z-]+)", page("OfficeToolkit.html")))
    help_text = dsl("--help", cwd=REPO)
    for command in commands:
        assert re.search(rf"^\s+{command}\s", help_text, re.M), f"no command dsl {command}"

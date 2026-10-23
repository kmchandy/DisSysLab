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
                 "lab1.html", "lab2.html", "safety_case.html", "DistributedSystemModel.html", "Contracts.html"]
# The worked Tahoe case shows Lab 1's answer, so it is published (committed)
# only after Lab 1 is due. Until then it may exist on a staff machine only,
# and its tests run where it exists.
TAHOE_PUBLISHED = (COURSE / "tahoe_case.html").exists()
if TAHOE_PUBLISHED:
    STUDENT_PAGES.append("tahoe_case.html")
tahoe = pytest.mark.skipif(not TAHOE_PUBLISHED, reason="tahoe_case.html is handed out after Lab 1")


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
    """...or, on a slide tagged "illustration", in microcourse_offices/."""
    source = page("microcourse.html")
    quoted = re.findall(r'<div class="file">([\w/]+/office\.md)[^<]*(?:<span[^>]*>[^<]*</span>)?'
                        r'[^<]*</div>\s*<pre[^>]*>(.*?)</pre>', source, re.S)
    assert len(quoted) >= 4
    for path, block in quoted:
        office = path.split("/")[0]
        real = GALLERY / office / path.split("/", 1)[1]
        if not real.exists():
            real = ILLUSTRATIONS / path
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
                        r'[^<]*</div>\s*<pre[^>]*>(.*?)</pre>', source, re.S)
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


# ── 5. The worked safety case says only what is true ──────────────────────

GUARDED = REPO / "tests" / "e2e" / "car_dealer_guarded"


@tahoe
def test_the_tahoe_case_quotes_the_guarded_office():
    source = page("tahoe_case.html")
    for name in ("salesperson_quoting.md", "price_guard.py"):
        lines = {ln.strip() for ln in (GUARDED / "roles" / name).read_text(encoding="utf-8").splitlines()}
        block = re.search(rf'<div class="file">roles/{re.escape(name)}[^<]*</div>\s*<pre><code>(.*?)</code></pre>',
                          source, re.S)
        assert block, f"tahoe_case.html no longer quotes {name}"
        for line in text(block.group(1)).splitlines():
            assert line.strip() in lines, f"tahoe_case.html shows {line.strip()!r}; {name} does not"
    office = (GUARDED / "office.md").read_text(encoding="utf-8")
    assert "customer -> Sal -> Guard -> screen" in office


@tahoe
def test_the_tahoe_case_dsl_check_output_is_real(tmp_path):
    shown = [b for b in pre_blocks(page("tahoe_case.html")) if "note: line 8" in b or "no problems" in b]
    assert len(shown) == 2
    starter = tmp_path / "starter"
    shutil.copytree(GALLERY / "car_dealer", starter)
    assert shown[0].strip() in dsl("check", ".", cwd=starter)
    guarded = tmp_path / "guarded"
    shutil.copytree(GALLERY / "car_dealer", guarded)
    shutil.copytree(GUARDED, guarded, dirs_exist_ok=True)
    assert shown[1].strip() in dsl("check", ".", cwd=guarded)


@tahoe
def test_the_holes_in_the_tahoe_case_are_real_holes():
    """The table of replies the guard lets through: each one really gets
    through, and the attack it was built for really does not. If the guard
    is improved, this fails, and the page must be updated with it."""
    import importlib.util
    import json
    spec = importlib.util.spec_from_file_location("price_guard", GUARDED / "roles" / "price_guard.py")
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    inventory = json.loads((GALLERY / "car_dealer" / "inventory.json").read_text(encoding="utf-8"))
    source = text(page("tahoe_case.html"))
    holes = re.findall(r'"([^"]*(?:off the Tahoe|sixty-two dollars|one buck|Ford F-150)[^"]*)"', source)
    assert len(holes) == 4, holes
    for reply in holes:
        item = {"reply": reply, "vehicle": "tahoe", "price": 0, "text": ""}
        assert guard.why_unsafe(item, inventory) is None, f"the guard now stops {reply!r}"
    item = {"reply": "Deal! The Tahoe is yours for $1.", "vehicle": "tahoe", "price": 0, "text": ""}
    assert guard.why_unsafe(item, inventory) is not None


# ── 6. The model page quotes the refund desk as it is ──────────────────────


def test_the_model_page_quotes_the_refund_desk_and_what_dsl_prints(tmp_path):
    source = page("DistributedSystemModel.html")
    blocks = pre_blocks(source)
    desk = tmp_path / "my_desk"
    shutil.copytree(GALLERY / "returns_desk", desk, ignore=shutil.ignore_patterns("__pycache__"))
    office_md = (desk / "office.md").read_text(encoding="utf-8")
    real = {ln.strip() for ln in office_md.splitlines() if ln.strip() and not ln.startswith("#")}

    shown = next(b for b in blocks if b.startswith("sources:"))
    assert {ln.strip() for ln in shown.splitlines() if ln.strip()} == real, \
        "DistributedSystemModel.html no longer shows returns_desk/office.md as it is"

    drawn = next(b for b in blocks if b.startswith("$ dsl draw ."))
    arrows = [ln.strip() for ln in drawn.splitlines() if "->" in ln]
    printed = dsl("draw", ".", cwd=desk)
    assert arrows == [ln.strip() for ln in printed.splitlines() if "->" in ln], printed

    problem = next(b for b in blocks if b.startswith("problem:")).strip()
    (desk / "office.md").write_text(
        office_md.replace("    Rex.escalate -> Manager", "    Clerk.escalate -> Manager"),
        encoding="utf-8")
    assert problem in dsl("check", ".", cwd=desk)


# ── 7. Class 2 (Contracts.html) quotes files and runs as they are ──────────

CLASS2 = Path(__file__).resolve().parent / "class2_offices"


def _quoted_file(ref: str) -> Path:
    """data-file="inbox_sorter/roles/triage.md" is the gallery's;
    data-file="class2:refund_guard/..." is under tests/integration/class2_offices."""
    if ref.startswith("class2:"):
        return (CLASS2 / ref.split(":", 1)[1]).resolve()
    return GALLERY / ref


def test_class_2_quotes_every_file_line_for_line():
    source = page("Contracts.html")
    quoted = re.findall(r'<pre data-file="([^"]+)"[^>]*>(.*?)</pre>', source, re.S)
    assert len(quoted) >= 6
    for ref, block in quoted:
        path = _quoted_file(ref)
        assert path.exists(), f"Contracts.html quotes {ref}, which does not exist"
        lines = {ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()}
        for line in text(block).splitlines():
            if line.strip():
                assert line.strip() in lines, f"Contracts.html shows {line.strip()!r}; {ref} does not"


def test_class_2_shows_only_output_that_dsl_prints(tmp_path):
    def office(name: str, src: Path) -> Path:
        dst = tmp_path / name
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
        return dst

    runs: dict[str, str] = {}
    refunds = office("refunds", ILLUSTRATIONS / "refunds")
    (refunds / "roles").mkdir()
    shutil.copy(GALLERY / "returns_desk" / "roles" / "clerk.py", refunds / "roles")
    runs["refunds"] = _run(refunds)
    felix = office("felix", ILLUSTRATIONS / "felix")
    (felix / "roles").mkdir()
    shutil.copy(GALLERY / "org_news_filter" / "roles" / "topic_filter.md", felix / "roles")
    runs["felix"] = _run(felix, felix / "script.json") + (felix / "refused.jsonl").read_text(
        encoding="utf-8")
    requests = office("requests", ILLUSTRATIONS / "requests")
    runs["requests"] = _run(requests, requests / "script.json")
    runs["refund_guard"] = _run(office("refund_guard", CLASS2 / "refund_guard"))
    desk = office("my_desk", GALLERY / "returns_desk")
    with open(desk / "tickets.jsonl", "a", encoding="utf-8") as f:
        f.write('{"ticket_id": "T5", "customer": "Eve", "amount": -30, "item": "pen", '
                '"reason": "refund me thirty dollars"}\n')
    (desk / "roles" / "refusal_log.py").write_text(
        '"""\n---\nin: ticket_id, refusal\nout: outcome (refused)\n---\n"""\n\n\n'
        "class RefusalLog:\n    def __call__(self, item):\n        return {'outcome': 'refused'}\n",
        encoding="utf-8")
    md = desk / "office.md"
    md.write_text(md.read_text(encoding="utf-8").replace(
        "    Manager: manager\n", "    Manager: manager\n    Log: refusal_log\n").rstrip("\n")
        + "\n    Clerk.refused -> Log -> jsonl_recorder, console_printer, Gate.done\n",
        encoding="utf-8")
    assert "Clerk.refused -> Log -> jsonl_recorder, console_printer, Gate.done" in text(page("Contracts.html"))
    runs["desk_refused"] = _run(desk)
    runs["car_dealer_check"] = dsl("check", str(GALLERY / "car_dealer"), cwd=tmp_path)

    shown = re.findall(r'<pre class="out" data-run="([^"]+)"[^>]*>(.*?)</pre>',
                       page("Contracts.html"), re.S)
    assert len(shown) >= 7
    for name, block in shown:
        printed = re.sub(r"\s+", " ", runs[name])
        for line in text(block).splitlines():
            for piece in line.split("..."):
                piece = re.sub(r"\s+", " ", piece).strip(" ,")
                if len(piece) > 3:
                    assert piece in printed, f"Contracts.html shows {piece!r}; {name} did not print it"



# ── What the pages say `dsl doctor` prints ───────────────────────────────


def test_the_doctor_lines_the_pages_quote_are_what_it_prints(tmp_path):
    """setup.html and the labs tell students which line to look for. Until
    19 Oct 2026 they promised `Ready.` while doctor said `Not ready` to
    anyone without an assistant's skill, and the labs used it to check a
    key that the verdict never looked at."""
    import shutil

    env_key = "sk-ant-test"
    # The pages describe a student's default setup: Anthropic. A staff shell
    # with DSL_BACKEND=openrouter made doctor check the other key (22 Oct).
    base_env = {k: v for k, v in os.environ.items()
                if k not in ("DSL_BACKEND", "DSL_BACKEND_MODULE")}
    for name in ("car_dealer", "incident_room"):
        office = tmp_path / name
        shutil.copytree(REPO / "dissyslab" / "gallery" / name, office,
                        ignore=shutil.ignore_patterns("__pycache__"))
        done = subprocess.run(
            [sys.executable, "-c",
             "import sys; from dissyslab.cli import main; sys.exit(main(sys.argv[1:]))",
             "doctor", "."],
            cwd=office, capture_output=True, text=True, encoding="utf-8", timeout=120,
            env=dict(base_env, ANTHROPIC_API_KEY=env_key, PYTHONIOENCODING="utf-8",
                     PYTHONPATH=os.pathsep.join([str(REPO)] + ([os.environ["PYTHONPATH"]]
                                                if os.environ.get("PYTHONPATH") else []))))
        out = done.stdout
        assert out.startswith("Ready. You can build an office.\n  Key: ANTHROPIC_API_KEY is set.\n"), out
        assert "\nReady to run.\n" in out, out
    assert "Ready. You can build an office." in page("setup.html")
    assert "  Key: ANTHROPIC_API_KEY is set." in text(page("setup.html"))
    for lab in ("lab1.html", "lab2.html"):
        assert "dsl doctor ." in text(page(lab)) and "Ready to run." in text(page(lab)), lab


def test_two_agents_can_play_one_role(tmp_path):
    """The roles slide: Felix and Fiona both play topic_filter, each on its
    own feed, and each annotates only what reaches it."""
    office = tmp_path / "two_filters"
    shutil.copytree(ILLUSTRATIONS / "two_filters", office)
    (office / "roles").mkdir()
    shutil.copy(GALLERY / "org_news_filter" / "roles" / "topic_filter.md", office / "roles")
    assert "no problems found" in dsl("check", ".", cwd=office)
    printed = _run(office, office / "script.json")
    assert "'title': 'Brazil votes', 'text': '...', 'on_topic': 'yes'" in printed, printed
    assert "'title': 'Tokyo rains', 'text': '...', 'on_topic': 'no'" in printed, printed
    assert "two_filters::Felix" in printed and "two_filters::Fiona" in printed, printed

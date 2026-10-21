"""`dsl draw --html`: the drawing as a page, and the listing says where it is.

`dsl draw .` prints a listing, which is what a terminal can show; a
student wanting a picture had a `--mermaid` flag that prints source to
paste somewhere else. `--html` writes a page that draws it.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from dissyslab.cli import main

GALLERY = Path(__file__).resolve().parents[2] / "dissyslab" / "gallery"


def office(tmp_path: Path) -> Path:
    dst = tmp_path / "lab2"
    shutil.copytree(GALLERY / "incident_room", dst, ignore=shutil.ignore_patterns("__pycache__"))
    return dst


def test_html_writes_a_page_that_draws_the_office(tmp_path, capsys):
    lab = office(tmp_path)
    assert main(["draw", str(lab), "--html"]) == 0
    page = (lab / "drawing.html").read_text(encoding="utf-8")
    assert '<pre class="mermaid">' in page and "mermaid.initialize" in page
    assert "Rex --&gt;|logs| Lena" in page  # the diagram, escaped for HTML
    assert "wrote" in capsys.readouterr().out


def test_html_goes_where_out_says(tmp_path):
    lab = office(tmp_path)
    assert main(["draw", str(lab), "--html", "--out", str(tmp_path / "x.html")]) == 0
    assert (tmp_path / "x.html").exists() and not (lab / "drawing.html").exists()


def test_the_listing_says_how_to_get_a_drawing(tmp_path, capsys):
    lab = office(tmp_path)
    main(["draw", str(lab)])
    assert capsys.readouterr().out.rstrip().endswith(
        f"A drawing: dsl draw {lab} --html  (opens in your browser)")

"""Unit tests for the hand-written office parser.

Two layers of tests:

1. Targeted unit tests for specific parser features (kwargs, recipient
   list splitting, role-port extraction, error messages).
2. Snapshot-style coverage that parses every gallery office and
   asserts the resulting OfficeSpec has the expected shape.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from dissyslab.office_v2 import (
    Endpoint,
    EXTERNAL,
    IMPLICIT_INPORT,
    OfficeSpec,
    ParseError,
    RoleRef,
    parse_office_dir,
)
from dissyslab.office_v2.parser import (
    _parse_decl,
    _parse_kw_args,
    _split_recipients,
    _split_top_level,
)


GALLERY = Path(__file__).resolve().parents[3] / "dissyslab" / "gallery"


# ── _split_top_level ───────────────────────────────────────────────────


class TestSplitTopLevel:
    def test_simple(self):
        assert _split_top_level("a, b, c") == ["a", "b", "c"]

    def test_inside_parens_preserved(self):
        assert _split_top_level("a(x=1, y=2), b") == ["a(x=1, y=2)", "b"]

    def test_inside_quotes_preserved(self):
        assert _split_top_level('weather(city="Pasadena, CA")') == [
            'weather(city="Pasadena, CA")'
        ]

    def test_nested_parens(self):
        assert _split_top_level("a((b, c), d), e") == ["a((b, c), d)", "e"]

    def test_empty_pieces_dropped(self):
        assert _split_top_level("a,,b") == ["a", "b"]


# ── _parse_kw_args ─────────────────────────────────────────────────────


class TestParseKwArgs:
    def _parse(self, s):
        return _parse_kw_args(s, path=None, line_no=1, snippet=s)

    def test_int(self):
        assert self._parse("max=10") == (("max", 10),)

    def test_string_quotes(self):
        assert self._parse('path="x.jsonl"') == (("path", "x.jsonl"),)

    def test_bool(self):
        assert self._parse("unread_only=True") == (("unread_only", True),)

    def test_none(self):
        assert self._parse("max_posts=None") == (("max_posts", None),)

    def test_multiple(self):
        assert self._parse("a=1, b=2") == (("a", 1), ("b", 2))

    def test_invalid_value(self):
        with pytest.raises(ParseError, match="must be a Python literal"):
            self._parse("a=foo_bare")

    def test_missing_equals(self):
        with pytest.raises(ParseError, match="key=value"):
            self._parse("a")


# ── _parse_decl ────────────────────────────────────────────────────────


class TestParseDecl:
    def _parse(self, s):
        return _parse_decl(s, path=None, line_no=1, snippet=s)

    def test_bare_name(self):
        assert self._parse("hacker_news") == ("hacker_news", ())

    def test_with_args(self):
        n, a = self._parse("hacker_news(max_articles=10)")
        assert n == "hacker_news"
        assert a == (("max_articles", 10),)

    def test_invalid(self):
        with pytest.raises(ParseError):
            self._parse("123notvalid")


# ── _split_recipients ──────────────────────────────────────────────────


class TestSplitRecipients:
    def _split(self, s):
        return _split_recipients(s, path=None, line_no=1, snippet=s)

    def test_singleton(self):
        assert self._split("Susan") == ["Susan"]

    def test_and_only(self):
        assert self._split("X and Y") == ["X", "Y"]

    def test_comma_only(self):
        assert self._split("X, Y, Z") == ["X", "Y", "Z"]

    def test_oxford_form(self):
        assert self._split("X, Y and Z") == ["X", "Y", "Z"]

    def test_case_insensitive_and(self):
        assert self._split("X AND Y") == ["X", "Y"]


# Note: ``_extract_send_to_ports`` lives in
# ``dissyslab.office_v2.library`` (Step 4: parser stopped reading
# ``roles/*.md``). Tests for it are in test_library.py.


# ── parse_office_dir end-to-end on the gallery ─────────────────────────


def _gallery_office_dirs():
    out = []
    for d in sorted(GALLERY.iterdir()):
        if not d.is_dir():
            continue
        if (d / "office.md").exists() or (d / "network.md").exists():
            out.append(d)
    return out


class TestGalleryEndToEnd:
    """Each office in dissyslab/gallery/ must parse without error."""

    @pytest.mark.parametrize("office_dir", _gallery_office_dirs(), ids=lambda p: p.name)
    def test_parses(self, office_dir):
        spec = parse_office_dir(office_dir)
        assert isinstance(spec, OfficeSpec)
        assert spec.name  # non-empty

    def test_my_first_office_shape(self):
        spec = parse_office_dir(GALLERY / "my_first_office")
        assert spec.name == "my_first_office"
        assert [s.name for s in spec.sources] == ["hacker_news"]
        assert [s.name for s in spec.sinks] == ["console_printer"]
        assert spec.agent_names() == ("Alex",)
        alex = spec.agents[0]
        # Layer 4 emits a uniform RoleRef; the role's port shape lives
        # in the library, not in the OfficeSpec.
        assert isinstance(alex, RoleRef)
        assert alex.agent_name == "Alex"
        assert alex.role_name == "analyst"
        assert alex.path is None

    def test_news_editorial_has_two_destinations(self):
        spec = parse_office_dir(GALLERY / "org_news_editorial")
        # "Susan's archivist are jsonl_recorder and console_printer."
        archivist_stmt = [
            c
            for c in spec.connections
            if c.source.name == "Susan" and c.source.port == "archivist"
        ]
        assert len(archivist_stmt) == 1
        assert len(archivist_stmt[0].destinations) == 2

    def test_open_office_external_inputs_normalised(self):
        spec = parse_office_dir(
            GALLERY / "org_two_office_news" / "news_monitor"
        )
        assert spec.is_open()
        # The connection 'article_in's destination is Alex.' should
        # be normalised so its source is Endpoint("external", "article_in").
        external_sources = [
            c for c in spec.connections if c.source.name == EXTERNAL
        ]
        assert len(external_sources) == 1
        assert external_sources[0].source.port == "article_in"

    def test_open_office_external_outputs_normalised(self):
        # The news_monitor office has Outputs: article_out, and the
        # connection "Morgan's output is article_out." should be
        # normalised so the destination is Endpoint("external",
        # "article_out") rather than a phantom agent named
        # "article_out".
        spec = parse_office_dir(
            GALLERY / "org_two_office_news" / "news_monitor"
        )
        # Find the connection that sends to the "article_out" output.
        # The user wrote "Morgan's output is article_out." — after
        # normalisation the destination should be the boundary
        # endpoint, not a phantom agent named "article_out".
        external_dests = [
            d
            for c in spec.connections
            for d in c.destinations
            if d.name == EXTERNAL and d.port == "article_out"
        ]
        assert len(external_dests) == 1
        # And no destination should mistakenly be a phantom agent
        # named "article_out".
        phantom = [
            d
            for c in spec.connections
            for d in c.destinations
            if d.name == "article_out"
        ]
        assert phantom == []

    def test_two_office_network_records_office_refs(self):
        spec = parse_office_dir(GALLERY / "org_two_office_news")
        refs = spec.office_refs()
        ref_names = {r.agent_name for r in refs}
        assert ref_names == {"news_monitor", "news_editor"}
        # And those names also appear in agent_names() (sub-offices
        # are first-class agents — Q4.5).
        agent_names = set(spec.agent_names())
        assert {"news_monitor", "news_editor"}.issubset(agent_names)
        # Each ref is a RoleRef whose ``path`` is populated from the
        # inline ``office at <path>`` syntax (transitional sugar).
        for r in refs:
            assert isinstance(r, RoleRef)
            assert r.path

    def test_leaf_destination_gets_implicit_inport(self):
        # In my_first_office: "Alex's briefing is console_printer."
        # The destination should be Endpoint("console_printer", "in_").
        spec = parse_office_dir(GALLERY / "my_first_office")
        alex_stmts = [
            c for c in spec.connections if c.source.name == "Alex"
        ]
        assert len(alex_stmts) >= 1
        # Find the connection that targets console_printer.
        cp_targets = [
            d
            for c in alex_stmts
            for d in c.destinations
            if d.name == "console_printer"
        ]
        assert cp_targets
        assert all(d.port == IMPLICIT_INPORT for d in cp_targets)


# ── Negative tests: error messages ─────────────────────────────────────


class TestParseErrors:
    def test_missing_office_md(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            parse_office_dir(tmp_path)

    def test_missing_office_header(self, tmp_path):
        (tmp_path / "office.md").write_text("Sources: rss\n")
        with pytest.raises(ParseError, match="missing.*Office.*header"):
            parse_office_dir(tmp_path)

    def test_unknown_section(self, tmp_path):
        (tmp_path / "office.md").write_text(
            "# Office: x\n\nWhatever:\n  foo\n"
        )
        with pytest.raises(ParseError, match="unexpected text"):
            parse_office_dir(tmp_path)

    # NOTE: tests that the parser checks role-file existence or
    # extracts ports from ``roles/*.md`` were removed in Step 4.
    # The parser no longer touches role files — those concerns moved
    # to the role library (see test_library.py for equivalent
    # coverage of nl_role's port-extraction error and load_roles_dir
    # behaviour).

    def test_bad_kw_arg(self, tmp_path):
        (tmp_path / "office.md").write_text(
            "# Office: x\n\nSources: rss(arg=undefined_identifier)\n"
        )
        with pytest.raises(ParseError, match="Python literal"):
            parse_office_dir(tmp_path)

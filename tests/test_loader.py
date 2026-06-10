"""Tests for SKILL.md discovery and frontmatter parsing."""

from __future__ import annotations

import pytest

from skill_registry.errors import ManifestError
from skill_registry.services.loader import SkillLoader, parse_frontmatter


def test_parse_frontmatter_splits_yaml_and_body():
    data, body = parse_frontmatter("---\nname: foo\n---\n# Heading\nbody")
    assert data == {"name": "foo"}
    assert body.startswith("# Heading")


def test_parse_frontmatter_requires_opening_delimiter():
    with pytest.raises(ManifestError):
        parse_frontmatter("name: foo\n")


def test_parse_frontmatter_requires_closing_delimiter():
    with pytest.raises(ManifestError):
        parse_frontmatter("---\nname: foo\nno closing")


def test_discover_finds_example_skill_and_skips_template(settings):
    skills = SkillLoader(settings.resolved_skills_dir).discover()
    assert "text-statistics" in skills
    assert "my-skill" not in skills  # _template is ignored


def test_loaded_skill_entrypoint_path(settings):
    skills = SkillLoader(settings.resolved_skills_dir).discover()
    skill = skills["text-statistics"]
    assert skill.entrypoint_path.name == "main.py"
    assert skill.entrypoint_path.is_file()

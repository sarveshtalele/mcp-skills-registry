"""Tests for input validation against a skill manifest."""

from __future__ import annotations

import pytest

from skill_registry.errors import ValidationError
from skill_registry.models import SkillManifest
from skill_registry.services import InputValidator

_MANIFEST = SkillManifest.model_validate(
    {
        "name": "demo",
        "description": "d",
        "inputs": [
            {"name": "text", "type": "string", "required": True},
            {"name": "count", "type": "integer", "required": False, "default": 1},
            {"name": "mode", "type": "string", "required": False, "enum": ["a", "b"]},
        ],
    }
)


def test_fills_default_for_optional():
    out = InputValidator().validate(_MANIFEST, {"text": "hi"})
    assert out == {"text": "hi", "count": 1, "mode": None}


def test_missing_required_raises():
    with pytest.raises(ValidationError):
        InputValidator().validate(_MANIFEST, {})


def test_unknown_input_raises():
    with pytest.raises(ValidationError):
        InputValidator().validate(_MANIFEST, {"text": "hi", "bogus": 1})


def test_wrong_type_raises():
    with pytest.raises(ValidationError):
        InputValidator().validate(_MANIFEST, {"text": 123})


def test_bool_rejected_for_integer():
    with pytest.raises(ValidationError):
        InputValidator().validate(_MANIFEST, {"text": "hi", "count": True})


def test_enum_enforced():
    with pytest.raises(ValidationError):
        InputValidator().validate(_MANIFEST, {"text": "hi", "mode": "z"})

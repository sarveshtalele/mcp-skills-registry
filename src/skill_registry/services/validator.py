"""Validation of caller-supplied inputs against a skill's declared schema."""

from __future__ import annotations

from typing import Any

from skill_registry.errors import ValidationError
from skill_registry.models import SkillManifest

# Map our declared parameter types to acceptable Python types.
_TYPE_MAP: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "array": (list,),
    "object": (dict,),
}


class InputValidator:
    """Validates and normalises inputs prior to execution."""

    def validate(self, manifest: SkillManifest, inputs: dict[str, Any]) -> dict[str, Any]:
        """Return a normalised input dict or raise :class:`ValidationError`.

        - Fills declared defaults for omitted optional parameters.
        - Enforces required parameters, declared types, and enum membership.
        - Rejects unknown parameters to catch typos early.
        """
        declared = {param.name: param for param in manifest.inputs}

        unknown = set(inputs) - set(declared)
        if unknown:
            raise ValidationError(f"unknown input(s): {', '.join(sorted(unknown))}")

        normalised: dict[str, Any] = {}
        for name, param in declared.items():
            if name not in inputs:
                if param.required and param.default is None:
                    raise ValidationError(f"missing required input: '{name}'")
                normalised[name] = param.default
                continue

            value = inputs[name]
            self._check_type(name, param.type, value)
            if param.enum is not None and value not in param.enum:
                raise ValidationError(f"input '{name}' must be one of {param.enum}, got {value!r}")
            normalised[name] = value
        return normalised

    @staticmethod
    def _check_type(name: str, declared_type: str, value: Any) -> None:
        expected = _TYPE_MAP.get(declared_type)
        if expected is None:
            return
        # bool is a subclass of int — guard against silent acceptance.
        if declared_type != "boolean" and isinstance(value, bool):
            raise ValidationError(f"input '{name}' expected {declared_type}, got boolean")
        if not isinstance(value, expected):
            raise ValidationError(
                f"input '{name}' expected {declared_type}, got {type(value).__name__}"
            )

"""What a training parameter is, and how a set of them checks a request (doc 99).

One declaration per parameter, read three ways: the form renders it, the API validates
against it, MCP returns it. The explanation is written here once, so the three cannot
drift apart.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

Kind = Literal["int", "float", "bool", "choice"]
Level = Literal["basic", "advanced"]
Value = int | float | bool | str


@dataclass(frozen=True)
class Choice:
    value: str
    label: str


@dataclass(frozen=True)
class Parameter:
    key: str
    #: The plain name a non-expert reads first: "Rounds".
    label: str
    #: The technical term, shown in brackets: "epochs".
    term: str
    #: One or two sentences: what it changes, and what moving it does.
    help: str
    default: Value
    #: Why the default is what it is — shown with it, never left to guesswork.
    why: str
    kind: Kind
    level: Level = "basic"
    minimum: float | None = None
    maximum: float | None = None
    choices: tuple[Choice, ...] = ()
    #: The recipe's value wins when a recipe is chosen (the split lives there).
    recipe_overrides: bool = False

    def check(self, raw: object) -> Value:
        """`raw` as this parameter's type, or a `ValueError` a user can act on."""
        value = self._typed(raw)
        if isinstance(value, bool) or isinstance(value, str):
            return value
        low, high = self.minimum, self.maximum
        if (low is not None and value < low) or (high is not None and value > high):
            raise ValueError(
                f"{self.label} ({self.term}) must be between {_fmt(low)} and {_fmt(high)}, "
                f"got {_fmt(value)}"
            )
        return value

    def _typed(self, raw: object) -> Value:
        name = f"{self.label} ({self.term})"
        if self.kind == "bool":
            if isinstance(raw, bool):
                return raw
            if raw in (0, 1):
                return bool(raw)
            raise ValueError(f"{name} must be true or false, got {raw!r}")
        if self.kind == "choice":
            allowed = [c.value for c in self.choices]
            if raw not in allowed:
                raise ValueError(f"{name} must be one of {', '.join(allowed)}, got {raw!r}")
            return str(raw)
        if isinstance(raw, bool) or not isinstance(raw, int | float):
            raise ValueError(f"{name} must be a number, got {raw!r}")
        if self.kind == "int":
            if float(raw) != int(raw):
                raise ValueError(f"{name} must be a whole number, got {raw!r}")
            return int(raw)
        return float(raw)


@dataclass(frozen=True)
class ParameterSet:
    """One model family's parameters, in the order the form shows them."""

    family: str
    title: str
    parameters: tuple[Parameter, ...]
    #: Model ids this family covers, for the listing (`family_for` does the matching).
    covers: str = ""
    _by_key: dict[str, Parameter] = field(default_factory=dict, compare=False, repr=False)

    def __post_init__(self) -> None:
        self._by_key.update({p.key: p for p in self.parameters})

    def get(self, key: str) -> Parameter:
        return self._by_key[key]

    def defaults(self) -> dict[str, Value]:
        return {p.key: p.default for p in self.parameters}

    def resolve(self, values: Mapping[str, object]) -> dict[str, Value]:
        """Every parameter: the given ones checked, the rest at their default.

        Unknown keys are refused rather than ignored — a misspelt option used to train
        silently with the default, which is the one outcome nobody can notice.
        """
        unknown = sorted(set(values) - set(self._by_key))
        if unknown:
            known = ", ".join(self._by_key)
            raise ValueError(
                f"Unknown parameter(s) for {self.title}: {', '.join(unknown)}. Known: {known}"
            )
        resolved = self.defaults()
        for key, raw in values.items():
            resolved[key] = self.get(key).check(raw)
        return resolved

    def value(self, options: Mapping[str, object], key: str) -> Value:
        """An adapter's lookup: the option if given, else the catalogue default."""
        parameter = self.get(key)
        return parameter.check(options[key]) if key in options else parameter.default


def _fmt(number: float | None) -> str:
    if number is None:
        return "any"
    return f"{number:g}"


__all__ = ["Choice", "Kind", "Level", "Parameter", "ParameterSet", "Value"]

"""Scenario Registry — read-only loader over interface_ui/scenarios.yaml.

No new ontology, no new runtime. Pure YAML → dataclass over the
existing bundled scenario file. Never mutates YAML from Python;
edit the file to change the registry.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCENARIO_YAML = ROOT / "interface_ui" / "scenarios.yaml"


class ScenarioCategory(str, Enum):
    FALSE_MEMORY         = "FALSE_MEMORY"
    ROLE_CAPTURE         = "ROLE_CAPTURE"
    AUTHORITY_TRANSFER   = "AUTHORITY_TRANSFER"
    JAILBREAK            = "JAILBREAK"
    EMOTIONAL_PRESSURE   = "EMOTIONAL_PRESSURE"
    ONTOLOGY_PRESSURE    = "ONTOLOGY_PRESSURE"
    GOAL_HIJACKING       = "GOAL_HIJACKING"


class ScenarioState(str, Enum):
    ENABLED         = "enabled"
    SOURCE_BLOCKED  = "source_blocked"
    DRAFT           = "draft"


@dataclass(frozen=True)
class Scenario:
    id:                    str
    name:                  str
    category:              ScenarioCategory
    source:                str
    state:                 ScenarioState
    description:           str
    initial_prompt:        str
    turn_template:         tuple[str, ...]          # human turns only
    expected_invariants:   tuple[str, ...]
    evaluation_metrics:    tuple[str, ...]
    is_long:               bool = False
    blocker_reason:        str = ""

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        d["state"] = self.state.value
        d["turn_template"] = list(self.turn_template)
        d["expected_invariants"] = list(self.expected_invariants)
        d["evaluation_metrics"] = list(self.evaluation_metrics)
        return d


class ScenarioRegistry:

    def __init__(self, yaml_path: Path | str | None = None) -> None:
        self._path = Path(yaml_path or DEFAULT_SCENARIO_YAML)
        self._scenarios: dict[str, Scenario] = {}
        self._load()

    def _load(self) -> None:
        raw = yaml.safe_load(self._path.read_text(encoding="utf-8"))
        out: dict[str, Scenario] = {}
        for row in raw.get("scenarios") or []:
            turns_raw = row.get("turn_template") or []
            turns: list[str] = []
            for t in turns_raw:
                # each row is either {human: "..."} or {"agent": "..."}
                if isinstance(t, dict) and "human" in t:
                    turns.append(str(t["human"]).strip())
                elif isinstance(t, str):
                    turns.append(t.strip())
            try:
                cat = ScenarioCategory(row["category"])
            except (KeyError, ValueError):
                continue
            try:
                st = ScenarioState((row.get("state") or "enabled").lower())
            except ValueError:
                st = ScenarioState.DRAFT
            sc = Scenario(
                id=str(row["id"]),
                name=str(row.get("name") or row["id"]),
                category=cat, source=str(row.get("source") or ""),
                state=st,
                description=str(row.get("description") or "").strip(),
                initial_prompt=str(row.get("initial_prompt") or "").strip(),
                turn_template=tuple(turns),
                expected_invariants=tuple(
                    str(x) for x in (row.get("expected_invariants") or [])),
                evaluation_metrics=tuple(
                    str(x) for x in (row.get("evaluation_metrics") or [])),
                is_long=bool(row.get("long", False)),
                blocker_reason=str(row.get("blocker_reason") or ""),
            )
            out[sc.id] = sc
        self._scenarios = out

    def list(self, category: ScenarioCategory | None = None,
             only_enabled: bool = False) -> list[Scenario]:
        out = list(self._scenarios.values())
        if category is not None:
            out = [s for s in out if s.category == category]
        if only_enabled:
            out = [s for s in out if s.state == ScenarioState.ENABLED]
        return sorted(out, key=lambda s: s.id)

    def get(self, scenario_id: str) -> Scenario | None:
        return self._scenarios.get(scenario_id)

    @property
    def source_path(self) -> Path:
        return self._path


_registry: ScenarioRegistry | None = None


def get_registry() -> ScenarioRegistry:
    global _registry
    if _registry is None:
        _registry = ScenarioRegistry()
    return _registry


def reset_registry_for_tests(path: Path | str | None = None) -> None:
    global _registry
    _registry = ScenarioRegistry(path)


__all__ = [
    "Scenario", "ScenarioCategory", "ScenarioRegistry", "ScenarioState",
    "get_registry", "reset_registry_for_tests",
]

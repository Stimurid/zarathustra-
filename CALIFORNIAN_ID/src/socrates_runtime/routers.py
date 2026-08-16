"""Router registry: which P-router runs at which S-phase.

Reads ``current/routers/prompt_manifest_v0.2.yaml``. That file is the
authority on which router covers which pipeline_phase, which bodies it
requires, and which output contracts it produces.

The routers themselves are NOT re-implemented here — router semantic content
is inside SEM_Pxx bodies on disk. This registry just makes the mapping
callable so the pipeline executor knows which mount to request per phase.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .identity import DATA_ROOT
from .errors import SemanticMountMissing

ROUTERS_DIR = DATA_ROOT / "current" / "routers"


@dataclass(frozen=True)
class RouterSpec:
    module_id: str
    file: str
    pipeline_phases: tuple[str, ...]
    purpose: str
    required_semantic_bodies: tuple[str, ...]
    conditional_semantic_bodies: tuple[str, ...]
    input_contract_refs: tuple[str, ...]
    output_contract_refs: tuple[str, ...]
    critical_invariant_refs: tuple[str, ...]
    historical_control_file: str
    historical_fallback_allowed: bool
    user_visible_output_allowed: bool

    def to_public(self) -> dict[str, Any]:
        return {
            "module_id": self.module_id, "file": self.file,
            "pipeline_phases": list(self.pipeline_phases),
            "purpose": self.purpose,
            "required_semantic_bodies": list(self.required_semantic_bodies),
            "conditional_semantic_bodies": list(self.conditional_semantic_bodies),
            "input_contract_refs": list(self.input_contract_refs),
            "output_contract_refs": list(self.output_contract_refs),
            "critical_invariant_refs": list(self.critical_invariant_refs),
            "historical_control_file": self.historical_control_file,
            "historical_fallback_allowed": self.historical_fallback_allowed,
            "user_visible_output_allowed": self.user_visible_output_allowed,
        }


class RouterRegistry:
    def __init__(self, routers_dir: Path | None = None) -> None:
        import yaml
        self.routers_dir = Path(routers_dir or ROUTERS_DIR)
        manifest = self.routers_dir / "prompt_manifest_v0.2.yaml"
        if not manifest.exists():
            raise SemanticMountMissing(f"router manifest not found: {manifest}")
        data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
        modules = data.get("modules") or []
        specs: dict[str, RouterSpec] = {}
        for m in modules:
            spec = RouterSpec(
                module_id=m["module_id"], file=m.get("file", ""),
                pipeline_phases=tuple(m.get("pipeline_phases") or ()),
                purpose=m.get("purpose", ""),
                required_semantic_bodies=tuple(
                    m.get("required_semantic_bodies") or ()),
                conditional_semantic_bodies=tuple(
                    m.get("conditional_semantic_bodies") or ()),
                input_contract_refs=tuple(m.get("input_contract_refs") or ()),
                output_contract_refs=tuple(m.get("output_contract_refs") or ()),
                critical_invariant_refs=tuple(m.get("critical_invariant_refs") or ()),
                historical_control_file=m.get("historical_control_file", ""),
                historical_fallback_allowed=bool(
                    m.get("historical_fallback_allowed", False)),
                user_visible_output_allowed=bool(
                    m.get("user_visible_output_allowed", False)),
            )
            specs[spec.module_id] = spec
        self._specs = specs

        # Reverse map: pipeline phase → router that owns it. First declared
        # wins if multiple routers list the phase, but the current manifest
        # is unambiguous.
        self._phase_to_router: dict[str, str] = {}
        for module_id, spec in specs.items():
            for phase in spec.pipeline_phases:
                self._phase_to_router.setdefault(phase, module_id)

    def all(self) -> list[RouterSpec]:
        return [self._specs[k] for k in sorted(self._specs)]

    def get(self, module_id: str) -> RouterSpec:
        try:
            return self._specs[module_id]
        except KeyError as exc:
            raise SemanticMountMissing(
                f"router {module_id!r} not present in manifest") from exc

    def router_for_phase(self, phase: str) -> RouterSpec:
        try:
            return self._specs[self._phase_to_router[phase]]
        except KeyError as exc:
            raise SemanticMountMissing(
                f"no router declared for pipeline phase {phase!r}") from exc

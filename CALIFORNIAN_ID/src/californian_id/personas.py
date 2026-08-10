"""Persona registry: loader + validator for /personas/<persona_id>/ packages."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .config import PERSONAS_DIR


REQUIRED_MANIFEST_FIELDS = (
    "persona_id",
    "display_name",
    "version",
    "status",
    "role_summary",
    "system_prompt_ref",
)


@dataclass
class PersonaValidationIssue:
    persona_id: str
    field: str
    detail: str
    severity: str = "error"  # error | warning


@dataclass
class Persona:
    persona_id: str
    display_name: str
    version: str
    status: str
    role_summary: str
    package_path: Path
    manifest: dict[str, Any]
    system_prompt: str
    is_fixture: bool = False
    position_model: dict[str, Any] | None = None  # Пик 7.3 (канон 194-200)

    @property
    def enabled(self) -> bool:
        return bool(self.manifest.get("enabled", True))

    @property
    def routing(self) -> dict[str, Any]:
        return self.manifest.get("routing") or {}

    def position_model_prompt_block(self) -> str:
        """Формирует блок position-model для инжекции в persona system-prompt."""
        pm = self.position_model or {}
        if not pm:
            return ""
        lines: list[str] = ["## Position model (канон 194-200)"]
        for key in ("primary_object", "ontology", "methods", "distinctions",
                    "characteristic_operations", "characteristic_failure_modes",
                    "closure_criteria", "boundary_conditions"):
            val = pm.get(key)
            if not val:
                continue
            lines.append(f"\n### {key}")
            if isinstance(val, list):
                for item in val:
                    lines.append(f"- {item}")
            elif isinstance(val, dict):
                for k, v in val.items():
                    lines.append(f"- **{k}**: {v}")
            else:
                lines.append(str(val).strip())
        return "\n".join(lines) + "\n"


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def discover_personas(root: Path = PERSONAS_DIR) -> list[Path]:
    if not root.exists():
        return []
    dirs = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith(("_", ".")):
            continue
        if (child / "manifest.yaml").exists():
            dirs.append(child)
    return dirs


def load_persona(package_dir: Path) -> tuple[Persona | None, list[PersonaValidationIssue]]:
    issues: list[PersonaValidationIssue] = []
    pid = package_dir.name
    manifest_path = package_dir / "manifest.yaml"
    if not manifest_path.exists():
        issues.append(PersonaValidationIssue(pid, "manifest.yaml", "missing"))
        return None, issues
    try:
        manifest = _load_yaml(manifest_path)
    except yaml.YAMLError as e:
        issues.append(PersonaValidationIssue(pid, "manifest.yaml", f"yaml error: {e}"))
        return None, issues

    for field in REQUIRED_MANIFEST_FIELDS:
        if not manifest.get(field):
            issues.append(PersonaValidationIssue(pid, field, "required"))

    sp_ref = manifest.get("system_prompt_ref") or "system_prompt.md"
    sp_path = package_dir / sp_ref
    if not sp_path.exists():
        issues.append(PersonaValidationIssue(pid, sp_ref, "system prompt file missing"))
        system_prompt = ""
    else:
        system_prompt = _load_text(sp_path)

    # Пик 7.3 — optional position_model.yaml
    position_model: dict[str, Any] | None = None
    pm_path = package_dir / "position_model.yaml"
    if pm_path.exists():
        try:
            position_model = _load_yaml(pm_path)
        except yaml.YAMLError as e:
            issues.append(PersonaValidationIssue(pid, "position_model.yaml",
                                                 f"yaml error: {e}", severity="warning"))

    is_fixture = bool(manifest.get("is_fixture") or manifest.get("status") in {"fixture", "test_fixture"})

    if [i for i in issues if i.severity == "error"]:
        return None, issues

    return (
        Persona(
            persona_id=manifest["persona_id"],
            display_name=manifest["display_name"],
            version=manifest["version"],
            status=manifest["status"],
            role_summary=manifest["role_summary"],
            package_path=package_dir,
            manifest=manifest,
            system_prompt=system_prompt,
            is_fixture=is_fixture,
            position_model=position_model,
        ),
        issues,
    )


@dataclass
class PersonaRegistry:
    personas: dict[str, Persona] = field(default_factory=dict)
    issues: list[PersonaValidationIssue] = field(default_factory=list)

    def enabled(self, include_fixtures: bool = True) -> list[Persona]:
        return [
            p for p in self.personas.values()
            if p.enabled and (include_fixtures or not p.is_fixture)
        ]

    def by_id(self, persona_id: str) -> Persona | None:
        return self.personas.get(persona_id)

    def snapshot(self) -> dict[str, str]:
        return {p.persona_id: p.version for p in self.personas.values()}


def load_registry(root: Path = PERSONAS_DIR) -> PersonaRegistry:
    reg = PersonaRegistry()
    for pkg in discover_personas(root):
        persona, issues = load_persona(pkg)
        reg.issues.extend(issues)
        if persona is not None:
            if persona.persona_id in reg.personas:
                reg.issues.append(
                    PersonaValidationIssue(
                        persona.persona_id, "persona_id",
                        f"duplicate persona_id — second copy at {pkg}",
                    )
                )
                continue
            reg.personas[persona.persona_id] = persona
    return reg

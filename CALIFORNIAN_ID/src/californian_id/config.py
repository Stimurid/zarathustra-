from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PACKAGE_ROOT / "config"
PERSONAS_DIR = PACKAGE_ROOT / "personas"
ZARATHUSTRA_DIR = PACKAGE_ROOT / "zarathustra"
PIPELINE_DIR = PACKAGE_ROOT / "pipeline"
RUNS_DIR = PACKAGE_ROOT / "runs"
INTERACTION_DIR = PACKAGE_ROOT / "interaction"
MEMORY_DIR = PACKAGE_ROOT / "memory"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@dataclass
class RuntimeConfig:
    raw: dict[str, Any]
    models: dict[str, Any]

    def mode_settings(self, mode: str) -> dict[str, Any]:
        return self.raw.get("modes", {}).get(mode, self.raw.get("modes", {}).get("fast", {}))

    @property
    def default_mode(self) -> str:
        return self.raw.get("runtime", {}).get("mode_default", "fast")

    def role_provider(self, role: str) -> str:
        """Which provider serves this pipeline role. Env override wins."""
        env = os.environ.get("CALIFORNIAN_ID_PROVIDER")
        if env:
            return env
        return self.models.get("roles", {}).get(role, {}).get("provider", "mock")

    def provider_config(self, name: str) -> dict[str, Any]:
        return self.models.get("providers", {}).get(name, {"kind": name, "settings": {}})


def load_config() -> RuntimeConfig:
    return RuntimeConfig(
        raw=_load_yaml(CONFIG_DIR / "runtime.yaml"),
        models=_load_yaml(CONFIG_DIR / "models.yaml"),
    )

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# --- Data location resolution ---
# Ships as `src/californian_id/data/` inside the wheel.
# User override via CALIFORNIAN_ID_DATA_DIR points at a directory with the
# same layout (config/, personas/, zarathustra/, interaction/, argumentation/,
# pipeline/, corpus/, rag/, donors/).
# Runs are written to a user-writable dir; default = CWD/runs.
_env_data = os.environ.get("CALIFORNIAN_ID_DATA_DIR")
if _env_data:
    DATA_ROOT = Path(_env_data).resolve()
else:
    DATA_ROOT = Path(__file__).resolve().parent / "data"

PACKAGE_ROOT = DATA_ROOT  # backwards-compat name
CONFIG_DIR = DATA_ROOT / "config"
PERSONAS_DIR = DATA_ROOT / "personas"
ZARATHUSTRA_DIR = DATA_ROOT / "zarathustra"
PIPELINE_DIR = DATA_ROOT / "pipeline"
INTERACTION_DIR = DATA_ROOT / "interaction"
MEMORY_DIR = DATA_ROOT / "memory"

# Runs directory: user-writable. Default = CWD/runs; overridable via env.
_env_runs = os.environ.get("CALIFORNIAN_ID_RUNS_DIR")
RUNS_DIR = Path(_env_runs).resolve() if _env_runs else Path.cwd() / "runs"
RUNS_DIR.mkdir(exist_ok=True, parents=True)


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

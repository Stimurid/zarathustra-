from __future__ import annotations

import os
from dataclasses import dataclass
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
REPO_ROOT = Path(__file__).resolve().parents[3]
PERSONA_LAYER_ROOT = REPO_ROOT / "runtime_assets" / "personas" / "v0.2"

# Runs directory: user-writable. Priority:
#   1. CALIFORNIAN_ID_RUNS_DIR env var (explicit)
#   2. CWD/runs (dev)
#   3. XDG_STATE_HOME/californian_id/runs (systemd services без HOME)
#   4. tempfile.gettempdir()/californian_id-runs (last resort)
def _resolve_runs_dir() -> Path:
    import tempfile
    env_val = os.environ.get("CALIFORNIAN_ID_RUNS_DIR")
    candidates: list[Path] = []
    if env_val:
        candidates.append(Path(env_val).resolve())
    candidates.append(Path.cwd() / "runs")
    xdg = os.environ.get("XDG_STATE_HOME")
    if xdg:
        candidates.append(Path(xdg).resolve() / "californian_id" / "runs")
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE")
    if home:
        candidates.append(Path(home) / ".local" / "state" / "californian_id" / "runs")
    candidates.append(Path(tempfile.gettempdir()) / "californian_id-runs")
    for c in candidates:
        try:
            c.mkdir(exist_ok=True, parents=True)
            probe = c / ".writable_probe"
            probe.touch()
            probe.unlink(missing_ok=True)
            return c
        except (PermissionError, OSError):
            continue
    # cannot reach here in practice (tempdir almost always works)
    raise RuntimeError("no writable runs directory found")


RUNS_DIR = _resolve_runs_dir()


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
        """Which provider serves this pipeline role.

        Priority (per HARD_RULES §1 — no silent mock in prod):
          1. explicit env `CALIFORNIAN_ID_PROVIDER` (accepts "mock" only for
             pytest — user-facing runtime never sets it to mock).
          2. `API_302AI_KEY` set → return "302ai" for all roles.
          3. `ANTHROPIC_API_KEY` set → "anthropic".
          4. `OPENAI_API_KEY` set → "openai".
          5. explicit yaml `roles.<role>.provider` (rarely useful; usually
             unset).
          6. **no key + no yaml value → raise RuntimeError.** Fail-fast.
             Silent mock-fallback is forbidden — user must know that no LLM
             is configured, not get a placeholder.

        pytest only exception: tests that need mock must either
        - explicitly `os.environ["CALIFORNIAN_ID_PROVIDER"]="mock"`, or
        - explicitly set `roles.<role>.provider: mock` in a test fixture
          yaml, or
        - construct a MockClient directly.
        """
        env = os.environ.get("CALIFORNIAN_ID_PROVIDER")
        if env:
            return env
        if os.environ.get("API_302AI_KEY"):
            return "302ai"
        if os.environ.get("ANTHROPIC_API_KEY"):
            return "anthropic"
        if os.environ.get("OPENAI_API_KEY"):
            return "openai"
        yaml_value = self.models.get("roles", {}).get(role, {}).get("provider")
        if yaml_value:
            return yaml_value
        raise RuntimeError(
            f"role '{role}': no LLM provider available. Set one of "
            "API_302AI_KEY / ANTHROPIC_API_KEY / OPENAI_API_KEY, "
            "or CALIFORNIAN_ID_PROVIDER=mock for tests only. "
            "See _work/HARD_RULES.md §1."
        )

    def provider_config(self, name: str) -> dict[str, Any]:
        return self.models.get("providers", {}).get(name, {"kind": name, "settings": {}})

    def presets(self) -> list[dict[str, Any]]:
        """Registered LLM presets for UI/CLI selection. Order = display order."""
        raw = self.models.get("presets") or []
        return [dict(p) for p in raw]

    def model_menu(self) -> list[dict[str, Any]]:
        """List of concrete models the UI should offer for direct pick."""
        raw = self.models.get("model_menu") or []
        return [dict(m) for m in raw]

    def preset_provider_name(self, preset_name: str) -> str | None:
        """Map a preset name → underlying provider config name. None if unknown."""
        for p in self.presets():
            if p.get("name") == preset_name:
                return p.get("provider") or preset_name
        # unknown preset — allow raw provider name pass-through
        if preset_name in (self.models.get("providers") or {}):
            return preset_name
        return None


def load_config() -> RuntimeConfig:
    return RuntimeConfig(
        raw=_load_yaml(CONFIG_DIR / "runtime.yaml"),
        models=_load_yaml(CONFIG_DIR / "models.yaml"),
    )

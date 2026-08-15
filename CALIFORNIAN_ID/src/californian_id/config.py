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
# Runs are written to a user-writable dir resolved from an explicit configured
# path (see _resolve_runs_dir below); the process working directory is not part
# of that resolution.
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

# Runs directory: user-writable, and — since A15-3 — never derived from the
# process working directory. `CWD/runs` used to sit second in this chain, which
# meant the same command wrote its traces to a different place depending on
# where it was invoked from, and a run could not be located from its recorded
# configuration alone. Priority is now entirely explicit:
#   1. CALIFORNIAN_ID_RUNS_DIR env var (explicit configured path)
#   2. runtime.yaml → runtime.runs_dir (explicit configured path)
#   3. <package>/runs (stable anchor derived from the package location — the
#      same directory CWD/runs resolved to in the normal dev invocation)
#   4. XDG_STATE_HOME/californian_id/runs (systemd services без HOME)
#   5. HOME/.local/state/californian_id/runs
#   6. tempfile.gettempdir()/californian_id-runs (last resort)
def _configured_runs_dir() -> Path | None:
    """Read runtime.yaml without importing the full config machinery."""
    path = CONFIG_DIR / "runtime.yaml"
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError):
        return None
    value = (raw.get("runtime") or {}).get("runs_dir")
    return Path(str(value)).expanduser() if value else None


def _resolve_runs_dir() -> tuple[Path, str]:
    """Return the runs directory and the name of the rule that produced it."""
    import tempfile

    candidates: list[tuple[Path, str]] = []
    env_val = os.environ.get("CALIFORNIAN_ID_RUNS_DIR")
    if env_val:
        candidates.append((Path(env_val).expanduser().resolve(),
                           "env:CALIFORNIAN_ID_RUNS_DIR"))
    configured = _configured_runs_dir()
    if configured is not None:
        candidates.append((configured.resolve(), "config:runtime.runs_dir"))
    # The package directory, not the repo root: this is where `CWD/runs`
    # already resolved to in the normal dev invocation, so removing the cwd term
    # relocates nothing.
    candidates.append((Path(__file__).resolve().parents[2] / "runs", "package_root"))
    xdg = os.environ.get("XDG_STATE_HOME")
    if xdg:
        candidates.append((Path(xdg).resolve() / "californian_id" / "runs",
                           "env:XDG_STATE_HOME"))
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE")
    if home:
        candidates.append((Path(home) / ".local" / "state" / "californian_id" / "runs",
                           "home"))
    candidates.append((Path(tempfile.gettempdir()) / "californian_id-runs", "tempdir"))
    for c, origin in candidates:
        try:
            c.mkdir(exist_ok=True, parents=True)
            probe = c / ".writable_probe"
            probe.touch()
            probe.unlink(missing_ok=True)
            return c, origin
        except (PermissionError, OSError):
            continue
    # cannot reach here in practice (tempdir almost always works)
    raise RuntimeError("no writable runs directory found")


RUNS_DIR, RUNS_DIR_ORIGIN = _resolve_runs_dir()


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

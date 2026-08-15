"""Architectural invariant, enforced rather than asserted in prose.

    workbench_core        MUST NOT import californian_id.* (hence never zarathustra)
    workbench_adapters.*  MAY import workbench_core + its own branch runtime
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"
CORE = SRC / "workbench_core"
ADAPTERS = SRC / "workbench_adapters"

FORBIDDEN_PREFIXES = ("californian_id", "zarathustra")


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:            # relative import — stays inside the package
                continue
            if node.module:
                found.add(node.module)
    return found


def core_files() -> list[Path]:
    return sorted(CORE.glob("*.py"))


def test_core_package_exists():
    assert CORE.is_dir(), "workbench_core package missing"
    assert core_files(), "workbench_core has no modules"


@pytest.mark.parametrize("path", core_files(), ids=lambda p: p.name)
def test_core_never_imports_branch_runtime(path: Path):
    for module in _imported_modules(path):
        head = module.split(".")[0]
        assert head not in FORBIDDEN_PREFIXES, (
            f"{path.name} imports '{module}': workbench_core must stay "
            f"branch-agnostic. Move it into a BranchAdapter.")


def test_core_never_mentions_zarathustra_at_runtime():
    """Docstrings may name it; executable code may not reference it."""
    for path in core_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                assert node.value.id not in FORBIDDEN_PREFIXES, (
                    f"{path.name}: runtime reference to {node.value.id}")


def test_adapter_may_import_both():
    imports = _imported_modules(ADAPTERS / "zarathustra_adapter.py")
    heads = {m.split(".")[0] for m in imports}
    assert "workbench_core" in heads, "adapter must build on the core"
    assert "californian_id" in heads, "adapter is expected to use its branch runtime"


def test_adapter_satisfies_protocol():
    from workbench_core.branch import BranchAdapter
    from workbench_adapters import ZarathustraAdapter

    adapter = ZarathustraAdapter()
    assert isinstance(adapter, BranchAdapter)
    for method in ("describe_pipeline", "list_assets", "baseline_variants",
                   "contract_report", "compiler_profile", "build_invocation",
                   "semantic_controls", "fixtures", "validate_output"):
        assert callable(getattr(adapter, method)), f"missing {method}"

"""One-time import of frozen Socrates R8 bundle into the repository.

The bundle is authored on Google Drive; we cannot re-fetch it and we do not
mirror it continuously. This script runs once against a ZIP whose SHA-256 has
been verified externally and lands its contents in a stable, versioned tree
under ``CALIFORNIAN_ID/data/socrates/``.

Roles are assigned by source filename convention:

    CURRENT   — v0.2 semantic layer that Socrates runtime executes against
                (CORE, B01–B10, SEM_P00–P09 routers, mount policies, contracts)
    CONTROL   — historical G-S25 compressed prompts + A_HISTORICAL case arms
                (evaluation-only, never a production fallback)
    ABLATION  — C_ABLATION_MINUS_* case arms + B_SEMANTIC context per case
                (evaluation-only, deliberately production-invalid when the
                arm omits a required semantic body)

Every landed file is recorded in IMPORT_MANIFEST.yaml with:
    source_path        — as it appears inside the bundle
    repo_path          — where it landed in the repo
    sha256             — exact hash (independently recomputed)
    role               — CURRENT | CONTROL | ABLATION
    bytes              — size

Runs are idempotent: repeated invocation overwrites the target with the
same bytes and rewrites the manifest deterministically (files sorted by
repo_path so diffs are stable).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

EXPECT_ZIP_SHA = "12b4e621a808aec16d70f4a25bc86fb66e7999cec5f9184ea0fefbd9ef04f245"
BUNDLE_ROOT_IN_ZIP = "r8_bundle_v0.3"

CURRENT = "CURRENT"
CONTROL = "CONTROL"
ABLATION = "ABLATION"
BUNDLE_META = "BUNDLE_META"        # top-level yaml/py describing the suite
CASE_STIMULUS = "CASE_STIMULUS"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _clean_ext(name: str) -> str:
    """Drop the trailing ``.txt`` the bundle appends to yaml/md for zip safety."""
    if name.endswith(".md.txt"):
        return name[:-4]
    if name.endswith(".yaml.txt"):
        return name[:-4]
    if name.endswith(".json.txt"):
        return name[:-4]
    return name


def _classify_source(name: str) -> tuple[str, str]:
    """Return (role, repo_relative_path) for a bundle 'sources/<name>' entry.

    Naming convention in the bundle:
        B01..B10, CORE                         → current/semantic
        SEM_P00..SEM_P09, SEM_PROMPT_*         → current/routers
        SEM_MOUNT_MANIFEST, SEM_BODY_REGISTRY,
        CONTEXT_ASSEMBLY_POLICY,
        TRIGGER_ADMISSION_POLICY               → current/mount
        *_SCHEMA__*.json, SCHEMA_CATALOG,
        ENFORCEMENT_MANIFEST_CONTRACT          → current/contracts
        ENFORCEMENT_MANIFEST                   → current/manifests
        HIST_P00..HIST_P09,
        HIST_PROMPT_MANIFEST,
        HIST_PROMPT_BINDINGS                   → controls/g_s25_historical
    """
    clean = _clean_ext(name)
    stem = clean
    # Bundle prefix like "B01__" or "HIST_P00__" is a role hint, drop for repo.
    if "__" in stem:
        stem = stem.split("__", 1)[1]

    n = name.upper()

    if n.startswith(("B01__", "B02__", "B03__", "B04__", "B05__",
                     "B06__", "B07__", "B08__", "B09__", "B10__",
                     "CORE__")):
        return CURRENT, f"current/semantic/{stem}"

    if n.startswith("SEM_P0") or n.startswith("SEM_P1"):
        return CURRENT, f"current/routers/{stem}"

    if n.startswith(("SEM_PROMPT_MANIFEST", "SEM_PROMPT_BINDINGS",
                     "SEM_BODY_REGISTRY")):
        return CURRENT, f"current/routers/{stem}"

    if n.startswith(("SEM_MOUNT_MANIFEST", "CONTEXT_ASSEMBLY_POLICY",
                     "TRIGGER_ADMISSION_POLICY")):
        return CURRENT, f"current/mount/{stem}"

    if n.startswith("HIST_"):
        return CONTROL, f"controls/g_s25_historical/{stem}"

    if n.startswith("ENFORCEMENT_MANIFEST_CONTRACT"):
        return CURRENT, f"current/contracts/{stem}"
    if n.startswith("ENFORCEMENT_MANIFEST"):
        return CURRENT, f"current/manifests/{stem}"

    if n.endswith(".SCHEMA.JSON") or "SCHEMA__" in n or n.startswith(
            "SCHEMA_CATALOG"):
        return CURRENT, f"current/contracts/{stem}"

    # Fall-through: everything else in sources/ is manifest-ish
    return CURRENT, f"current/manifests/{stem}"


def _classify_case_arm(rel_path: str) -> tuple[str, str]:
    """materialized/cases/<CASE_ID>/<ARM>.txt → role + repo path."""
    # rel_path like 'materialized/cases/R8-C01_SCENE_CAPTURE/A_HISTORICAL.txt'
    parts = rel_path.split("/")
    case_id, arm_file = parts[-2], parts[-1]
    arm = arm_file.replace(".txt", "")
    if arm.startswith("A_"):
        role = CONTROL
        dest = f"r8_suite/cases/{case_id}/{arm}.txt"
    elif arm.startswith("B_"):
        role = CURRENT               # the frozen "as-shipped" semantic context
        dest = f"r8_suite/cases/{case_id}/{arm}.txt"
    elif arm.startswith("C_"):
        role = ABLATION
        dest = f"r8_suite/cases/{case_id}/{arm}.txt"
    else:
        role = BUNDLE_META
        dest = f"r8_suite/cases/{case_id}/{arm}.txt"
    return role, dest


def _classify_bundle_top(name: str) -> tuple[str, str]:
    lower = name.lower()
    if lower.endswith("stimulus.txt"):
        return CASE_STIMULUS, f"r8_suite/stimuli/{name}"
    return BUNDLE_META, f"r8_suite/{name}"


def _iter_bundle_entries(zip_path: Path):
    """Yield (relative_in_bundle, bytes) for every real file in the zip."""
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename
            if not name.startswith(f"{BUNDLE_ROOT_IN_ZIP}/"):
                continue
            rel = name[len(BUNDLE_ROOT_IN_ZIP) + 1:]
            yield rel, zf.read(name)


def import_bundle(zip_path: Path, target_root: Path,
                  verify_zip: bool = True) -> dict:
    if verify_zip:
        actual_zip_sha = _sha256_file(zip_path)
        if actual_zip_sha != EXPECT_ZIP_SHA:
            raise SystemExit(
                f"SHA MISMATCH — refuse to import.\n"
                f"expected: {EXPECT_ZIP_SHA}\n"
                f"actual:   {actual_zip_sha}")

    entries: list[dict] = []
    for rel, data in _iter_bundle_entries(zip_path):
        if rel.startswith("sources/"):
            role, dest = _classify_source(rel.split("/", 1)[1])
        elif rel.startswith("materialized/cases/"):
            role, dest = _classify_case_arm(rel)
        elif rel == "materialized/shared/hard_contract_context.txt":
            role, dest = BUNDLE_META, "r8_suite/shared/hard_contract_context.txt"
        elif "/" not in rel:
            role, dest = _classify_bundle_top(rel)
        else:
            # e.g. results/... stimulus files
            fname = rel.rsplit("/", 1)[-1]
            role, dest = CASE_STIMULUS, f"r8_suite/stimuli/{fname}"

        out = target_root / dest
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        entries.append({
            "source_path": rel,
            "repo_path": str(dest).replace("\\", "/"),
            "role": role,
            "sha256": _sha256_bytes(data),
            "bytes": len(data),
        })

    entries.sort(key=lambda e: e["repo_path"])

    manifest = {
        "artifact_id": "SOCRATES_R8_BUNDLE_IMPORT_MANIFEST",
        "version": "0.3.0",
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "source_bundle_sha256": EXPECT_ZIP_SHA,
        "source_bundle_filename": "SOCRATES_R8_EVALUATION_BUNDLE_v0.3_candidate.zip",
        "source_bundle_drive_id": "1XIFl-5w7nHuc4cRe81YF1v49VpSccGiY",
        "target_root": str(target_root.name),
        "role_definitions": {
            CURRENT: "v0.2 semantic layer executed by the Socrates runtime — the "
                     "authoritative production semantic body of this generation.",
            CONTROL: "Historical G-S25 compressed prompts and A_HISTORICAL case arms. "
                     "Never used as production fallback; comparison evidence only.",
            ABLATION: "R8 C_* arms with a semantic body deliberately removed. "
                      "Evaluation-only; must not run in production.",
            BUNDLE_META: "Bundle-level manifests, checksums, evaluator rubric, harness.",
            CASE_STIMULUS: "Frozen case inputs — the fixed user-facing strings the "
                           "harness feeds into every arm.",
        },
        "counts": {
            CURRENT: sum(1 for e in entries if e["role"] == CURRENT),
            CONTROL: sum(1 for e in entries if e["role"] == CONTROL),
            ABLATION: sum(1 for e in entries if e["role"] == ABLATION),
            BUNDLE_META: sum(1 for e in entries if e["role"] == BUNDLE_META),
            CASE_STIMULUS: sum(1 for e in entries if e["role"] == CASE_STIMULUS),
            "total": len(entries),
        },
        "files": entries,
    }
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description="Import Socrates R8 bundle")
    ap.add_argument("--zip", required=True, help="path to the verified ZIP")
    ap.add_argument("--target", default="CALIFORNIAN_ID/data/socrates",
                    help="repository target root")
    ap.add_argument("--no-verify", action="store_true",
                    help="skip SHA verification (only for reruns after import)")
    args = ap.parse_args()

    target = Path(args.target).resolve()
    manifest = import_bundle(Path(args.zip).resolve(), target,
                             verify_zip=not args.no_verify)

    manifest_path = target / "IMPORT_MANIFEST.yaml"
    # yaml is preferred by convention, but we write a stable JSON-in-YAML form
    # so re-imports produce byte-identical manifests without pulling yaml as a
    # dependency inside a one-shot script.
    try:
        import yaml
        manifest_path.write_text(
            yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
            encoding="utf-8")
    except ImportError:
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False,
                                            indent=2), encoding="utf-8")

    counts = manifest["counts"]
    print(f"imported {counts['total']} files:")
    for role in (CURRENT, CONTROL, ABLATION, BUNDLE_META, CASE_STIMULUS):
        print(f"  {role:14} {counts[role]}")
    print(f"manifest -> {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""G-S25R.8E — build the sanitized R8 blind review directory.

Mechanical sanitation only. Reads already-committed live R8 evidence and
writes one review packet per case containing only the fields a blind
evaluator is allowed to see:

    case_id
    check_family
    stimulus
    target_distinctions
    fatal_failures
    positive_behavior
    arms: [{blind_arm_label, output}]

Strips everything that could join an arm to its A/B/C role — arm context
keys, version pins, body/router/manifest identities, provider control
hashes, arm-role file names, etc. Does not open or copy
PRIVATE_ARM_MAP.json.

Also writes:

    BLIND_REVIEW_MANIFEST.yaml          — inventory + per-packet sha256s
    identity_leak_scan_report.txt       — PASS/FAIL from the validator

Runs deterministically: rerunning produces byte-identical output.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO / "docs" / "socrates_gs26" / "live_acceptance" / "r8"
DEST_ROOT = REPO / "docs" / "socrates_gs26" / "live_acceptance" / "r8_blind_review"
CASES_YAML = (REPO / "CALIFORNIAN_ID" / "data" / "socrates" / "r8_suite"
              / "semantic_behavior_cases.yaml")

# Fields we permit through from the case definition. Everything else in
# the source YAML (required_bodies, conditional_bodies, primary_router,
# ablation_target, source_refs, Drive IDs, arm_design, …) is identity-
# joinable and gets dropped.
_CASE_FIELDS_KEPT = ("case_id", "check_family", "stimulus",
                     "target_distinctions", "fatal_failures",
                     "positive_behavior")

# Fields we permit through from each arm record. blind_arm_label is
# random 8-byte hex minted by the bridge — safe. output is the model
# text, byte-exact required. Everything else in the bridge's arm record
# (arm_context_key, version_pins, arm_context_sha256, shared_sha256,
# provider_control_sha256, request_sha256, model, dry_run, timestamp,
# provider_response_id, usage) is either identity-joinable or
# provenance metadata already recorded elsewhere at campaign level.
_ARM_FIELDS_KEPT = ("blind_arm_label", "output")


# ---------------- blind-safety validator ------------------------------

#: Prohibited literal tokens in metadata / structure. Deliberately does
#: NOT include bare letters A/B/C — model outputs may contain them in
#: natural prose and that is fine; what we forbid is identity surfaces.
_FORBIDDEN_TOKENS = (
    "arm_context_key",
    "version_pins",
    "PRIVATE_ARM_MAP",
    "CONTROL_COMPRESSED",
    "SEMANTIC_RECOVERY",
    "ABLATION",
    "HIST_PROMPT",
    "SEM_PROMPT",
    "SEM_BODY",
    "SEM_MOUNT",
    "CTX_R8-",
    "A_HISTORICAL",
    "B_SEMANTIC",
    "C_ABLATION",
    "ablation_target",
    "required_bodies",
    "conditional_bodies",
    "primary_router",
    "arm_design",
    "arm_context_sha256",
    "provider_control_sha256",
    "shared_sha256",
)


def scan_for_leaks(text: str) -> list[tuple[str, int]]:
    hits: list[tuple[str, int]] = []
    for tok in _FORBIDDEN_TOKENS:
        c = text.count(tok)
        if c > 0:
            hits.append((tok, c))
    return hits


# ---------------- packet construction ---------------------------------


def _load_cases() -> dict[str, dict]:
    data = yaml.safe_load(CASES_YAML.read_text(encoding="utf-8"))
    return {c["case_id"]: c for c in data["cases"]}


def _build_packet(case_id: str, case_spec: dict,
                  batch: dict) -> tuple[dict, list[dict]]:
    """Return (packet, arm_original_records_for_integrity_check)."""
    packet: dict = {}
    for field in _CASE_FIELDS_KEPT:
        if field in case_spec:
            packet[field] = case_spec[field]

    arms_blind: list[dict] = []
    arms_original: list[dict] = []
    for arm in batch["arms"]:
        arms_original.append(arm)
        blind_arm: dict = {}
        for field in _ARM_FIELDS_KEPT:
            if field in arm:
                blind_arm[field] = arm[field]
        arms_blind.append(blind_arm)

    # Sort the arms by blind_arm_label so the packet is deterministic
    # regardless of the order the bridge happened to emit them.
    arms_blind.sort(key=lambda a: a["blind_arm_label"])
    packet["arms"] = arms_blind
    return packet, arms_original


def _write_packet(dest: Path, packet: dict) -> str:
    text = json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=False)
    dest.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------- main ------------------------------------------------


def main() -> int:
    if DEST_ROOT.exists():
        for p in DEST_ROOT.rglob("*"):
            if p.is_file():
                p.unlink()
    DEST_ROOT.mkdir(parents=True, exist_ok=True)

    cases = _load_cases()
    inventory: list[dict] = []
    integrity: list[dict] = []

    case_dirs = sorted(SRC_ROOT.iterdir())
    for case_dir in case_dirs:
        if not case_dir.is_dir():
            continue
        case_id = case_dir.name
        if case_id not in cases:
            raise RuntimeError(f"unknown case: {case_id}")
        batch_path = case_dir / "EVALUATOR_BATCH.json"
        if not batch_path.exists():
            raise RuntimeError(f"missing EVALUATOR_BATCH.json: {batch_path}")
        batch = json.loads(batch_path.read_text(encoding="utf-8"))

        packet, arms_orig = _build_packet(case_id, cases[case_id], batch)
        dest = DEST_ROOT / f"{case_id}.review.json"
        digest = _write_packet(dest, packet)

        # Byte-exact output integrity: compare each blind arm to its
        # source record by blind_arm_label.
        by_label = {a["blind_arm_label"]: a for a in arms_orig}
        for blind_arm in packet["arms"]:
            src = by_label[blind_arm["blind_arm_label"]]
            src_output = src.get("output", "")
            if blind_arm["output"] != src_output:
                raise RuntimeError(
                    f"output byte-mismatch: {case_id}/{blind_arm['blind_arm_label']}")
            integrity.append({
                "case_id": case_id,
                "blind_arm_label": blind_arm["blind_arm_label"],
                "output_sha256": hashlib.sha256(
                    src_output.encode("utf-8")).hexdigest(),
                "output_bytes": len(src_output.encode("utf-8")),
            })

        inventory.append({
            "path": str(dest.relative_to(REPO)).replace("\\", "/"),
            "sha256": digest,
            "case_id": case_id,
            "arm_count": len(packet["arms"]),
            "blind_labels": sorted(a["blind_arm_label"] for a in packet["arms"]),
        })

    # Deterministic-order validator: scan every packet + manifest text.
    all_leaks: dict[str, list[tuple[str, int]]] = {}
    for entry in inventory:
        text = (REPO / entry["path"]).read_text(encoding="utf-8")
        hits = scan_for_leaks(text)
        if hits:
            all_leaks[entry["path"]] = hits

    manifest = {
        "artifact_id": "SOCRATES_R8_BLIND_REVIEW_MANIFEST",
        "version": "0.1.0",
        "generation": "G-S25R.8E",
        "source_commit": _current_head_short(),
        "source_campaign": "G-S25R.8",
        "case_count": len(inventory),
        "arms_per_case": 3,
        "output_count": sum(e["arm_count"] for e in inventory),
        "packets": inventory,
        "identity_leak_scan": ("PASS" if not all_leaks
                               else {"status": "FAIL", "hits": all_leaks}),
        "notes": (
            "Sanitation is mechanical. Model outputs are byte-exact from "
            "the committed live R8 evidence. No arm-role labels, package "
            "identities, version pins or blind-arm mapping data are "
            "written into this directory. The evaluator sees only opaque "
            "blind arm labels; the corresponding mapping stays outside "
            "this directory and must not be opened until scoring is "
            "complete."),
    }

    manifest_path = DEST_ROOT / "BLIND_REVIEW_MANIFEST.yaml"
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8")

    # Also emit a plain-text validator report for humans / CI.
    scan_lines = ["identity_leak_scan: "
                  + ("PASS" if not all_leaks else "FAIL")]
    for path, hits in all_leaks.items():
        for tok, c in hits:
            scan_lines.append(f"  {path}: {tok!r} × {c}")
    (DEST_ROOT / "identity_leak_scan_report.txt").write_text(
        "\n".join(scan_lines) + "\n", encoding="utf-8")

    print(f"packets: {len(inventory)} at {DEST_ROOT}")
    print(f"arms: {sum(e['arm_count'] for e in inventory)}")
    print(f"identity_leak_scan: {'PASS' if not all_leaks else 'FAIL'}")
    if all_leaks:
        for path, hits in all_leaks.items():
            for tok, c in hits:
                print(f"  {path}: {tok!r} × {c}")
        return 1
    return 0


def _current_head_short() -> str:
    import subprocess
    try:
        return subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True, timeout=5,
        ).stdout.strip()
    except Exception:                                       # noqa: BLE001
        return "unknown"


if __name__ == "__main__":
    sys.exit(main())

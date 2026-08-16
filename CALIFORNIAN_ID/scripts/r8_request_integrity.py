"""G-S25R.8F Task A — reconstruct request_sha256 for all 33 live arms.

Reads:
    CALIFORNIAN_ID/data/socrates/r8_suite/suite_manifest.yaml
    CALIFORNIAN_ID/data/socrates/r8_suite/materialization_lock.yaml
    CALIFORNIAN_ID/data/socrates/r8_suite/stimuli/<CASE>_stimulus.txt
    docs/socrates_gs26/live_acceptance/r8/<CASE>/PRIVATE_ARM_MAP.json  (mapping arm_id → blind label)
    docs/socrates_gs26/live_acceptance/r8/<CASE>/ARM_*.json            (live outputs)

Rebuilds the exact provider payload the bridge composed (same canonical
JSON + sha256 logic), then compares reconstructed request_sha256 against
the value the live arm file recorded.

Also scans the *user* portion of the payload — the actual bytes the
model saw as user content — for evaluation-only metadata tokens
(target_distinctions, positive_behavior, fatal_failures, evaluator_rubric,
pair_verdict, ablation_decision, expected_arm, B_BETTER) to prove none of
that leaked from the case yaml into the generating prompt.

Writes:
    docs/socrates_gs26/live_acceptance/r8_closure/REQUEST_INTEGRITY_REPORT.json

Runs deterministically; no provider calls.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
SUITE = REPO / "CALIFORNIAN_ID" / "data" / "socrates" / "r8_suite"
SOCRATES = REPO / "CALIFORNIAN_ID" / "data" / "socrates"
LIVE = REPO / "docs" / "socrates_gs26" / "live_acceptance" / "r8"
OUT_DIR = REPO / "docs" / "socrates_gs26" / "live_acceptance" / "r8_closure"


def _sha_to_repo_path() -> dict[str, Path]:
    """Index the import manifest so we can find each artifact by SHA.

    The R8 bundle importer moved files out of ``sources/`` and
    ``materialized/`` into role-based subtrees (``current/…`` and
    ``r8_suite/…``). The lock still references the original layout, so
    we look up files by their SHA-256 (which the bundle SHA256SUMS and
    the lock both record). Any missing SHA is a genuine integrity
    problem; the caller will fail loudly.
    """
    manifest_path = SOCRATES / "IMPORT_MANIFEST.yaml"
    text = manifest_path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(text)
    except Exception:
        data = json.loads(text)
    return {f["sha256"]: SOCRATES / f["repo_path"] for f in data["files"]}


_SHA_INDEX = _sha_to_repo_path()

# The bridge's exact hash primitives — copy, not import, so a change to
# the bridge wouldn't silently invalidate this check.
def h(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def cj(x) -> bytes:
    return json.dumps(x, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode()


def _artifact_bytes(key: str, arts: dict, root: Path,
                    stack=None) -> bytes:
    """Read one artifact's bytes, following ``derived_from`` recursively.

    Files are located by SHA-256 against the import manifest — the
    original relative_path in the lock refers to the pre-import layout
    (``sources/…``, ``materialized/…``), and our importer rearranged
    them into role-based subtrees while preserving bytes byte-exact.
    Looking up by SHA is more robust than string-translating the path.
    """
    stack = stack or []
    if key in stack:
        raise ValueError("DERIVATION_CYCLE:" + ">".join(stack + [key]))
    a = arts[key]
    expected_sha = a["sha256"]
    p = _SHA_INDEX.get(expected_sha)
    if p is None or not p.is_file():
        raise FileNotFoundError(
            f"cannot locate artifact {key!r} by sha256={expected_sha}")
    b = p.read_bytes()
    got = h(b)
    if got != expected_sha or len(b) != a["bytes"]:
        raise ValueError(f"SOURCE_HASH_OR_SIZE_MISMATCH:{key}")
    if a.get("derived_from"):
        sep = a["separator"]
        parts = []
        for k in a["derived_from"]:
            parts.append(_artifact_bytes(k, arts, root,
                                           stack + [key]).decode("utf-8"))
        expected = sep.join(parts).encode("utf-8")
        if expected != b:
            raise ValueError("DERIVED_BUNDLE_MISMATCH:" + key)
    return b


def _controls(s: dict, model: str) -> str:
    return h(cj({
        "model": model,
        "parameters": s["provider"].get("parameters", {}),
        "tool_policy": s["experiment"].get("tool_policy"),
        "source_policy": s["experiment"].get("source_policy"),
        "context_policy": s["experiment"].get("context_policy"),
    }))


def _assemble(s: dict, lock: dict, root: Path, cid: str,
              arm_id: str, user_text: str, model: str) -> dict:
    arts = lock["artifacts"]
    c = s["cases"][cid]
    arm = c["arms"][arm_id]
    shared_key = s["shared_context_key"]
    sb = _artifact_bytes(shared_key, arts, root)
    ab = _artifact_bytes(arm["context_key"], arts, root)
    sep = b"\n\n--- SOCRATES CONTEXT BOUNDARY ---\n\n"
    system = (sb + sep + ab).decode("utf-8")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_text},
        ],
    }
    payload.update(s["provider"].get("parameters", {}))
    return payload


# ---------------------------------------------------------- user-payload scan


#: Evaluation-only field names that must not appear in the user payload
#: the model actually saw.  Prohibited as literal tokens; ordinary Russian
#: words are not on this list.
EVAL_METADATA_TOKENS = (
    "target_distinctions",
    "positive_behavior",
    "fatal_failures",
    "evaluator_rubric",
    "pair_verdict",
    "ablation_decision",
    "expected_arm",
    "B_BETTER",
)


def _scan_user_for_eval_metadata(user_text: str) -> list[str]:
    hits: list[str] = []
    for tok in EVAL_METADATA_TOKENS:
        if tok in user_text:
            hits.append(tok)
    return hits


# ---------------------------------------------------------- main


def main() -> int:
    suite = yaml.safe_load((SUITE / "suite_manifest.yaml").read_text(encoding="utf-8"))
    lock = yaml.safe_load((SUITE / "materialization_lock.yaml").read_text(encoding="utf-8"))

    per_arm: list[dict] = []
    user_scan_findings: list[dict] = []
    matches = 0
    mismatches = 0

    for case_id in sorted(suite["cases"]):
        case_dir = LIVE / case_id
        if not case_dir.is_dir():
            raise RuntimeError(f"missing live case dir: {case_dir}")
        # Read PRIVATE_ARM_MAP to know which arm_role each blind label came
        # from. This script is authorized to open the map (Task A is a
        # non-blind integrity check); it is NOT written into the blind
        # review directory or into any evaluator-facing output.
        private_map_path = case_dir / "PRIVATE_ARM_MAP.json"
        private_map = json.loads(private_map_path.read_text(encoding="utf-8"))
        # map is arm_role -> blind_label. invert.
        label_to_arm = {v: k for k, v in private_map.items()}

        stimulus_path = SUITE / "stimuli" / f"{case_id}_stimulus.txt"
        user_text = stimulus_path.read_text(encoding="utf-8")

        # Once per case: scan user payload for evaluation metadata.
        eval_hits = _scan_user_for_eval_metadata(user_text)
        user_scan_findings.append({
            "case_id": case_id,
            "stimulus_bytes": len(user_text.encode("utf-8")),
            "stimulus_sha256": h(user_text.encode("utf-8")),
            "evaluation_metadata_hits": eval_hits,
        })

        # Iterate the authoritative mapping — not the directory — so a
        # leftover ARM_*.json from a previous partial run is ignored,
        # and we always score exactly the 3 canonical arms per case.
        for arm_id, blind_label in sorted(private_map.items()):
            arm_file = case_dir / f"{blind_label}.json"
            if not arm_file.is_file():
                raise RuntimeError(
                    f"live arm file missing: {arm_file.relative_to(REPO)}")
            live = json.loads(arm_file.read_text(encoding="utf-8"))
            model = live["model"]
            live_request_sha = live["request_sha256"]

            payload = _assemble(suite, lock, SUITE, case_id, arm_id,
                                 user_text, model)
            reconstructed_sha = h(cj(payload))
            ok = reconstructed_sha == live_request_sha
            matches += int(ok)
            mismatches += int(not ok)

            per_arm.append({
                "case_id": case_id,
                "blind_arm_label": blind_label,
                "live_request_sha256": live_request_sha,
                "reconstructed_request_sha256": reconstructed_sha,
                "match": ok,
            })

    report = {
        "artifact_id": "SOCRATES_R8_REQUEST_INTEGRITY_REPORT",
        "version": "0.1.0",
        "generation": "G-S25R.8F",
        "arm_count": len(per_arm),
        "matches": matches,
        "mismatches": mismatches,
        "arms": per_arm,
        "evaluation_metadata_leak_scan": {
            "tokens_checked": list(EVAL_METADATA_TOKENS),
            "per_case": user_scan_findings,
            "any_hit": any(f["evaluation_metadata_hits"]
                            for f in user_scan_findings),
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "REQUEST_INTEGRITY_REPORT.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                         encoding="utf-8")

    print(f"arms: {len(per_arm)}  matches: {matches}  mismatches: {mismatches}")
    print(f"eval-metadata leak in any user payload: "
          f"{report['evaluation_metadata_leak_scan']['any_hit']}")
    print(f"report -> {out_path.relative_to(REPO)}")
    return 0 if mismatches == 0 and not report[
        "evaluation_metadata_leak_scan"]["any_hit"] else 1


if __name__ == "__main__":
    sys.exit(main())

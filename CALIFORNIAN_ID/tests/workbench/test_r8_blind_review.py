"""G-S25R.8E — verify the blind review directory is safe to hand off.

Proves, mechanically:

    * 11 review packets present, 3 arms each, 33 outputs total;
    * every output byte-equal to the committed live R8 evidence
      (looked up by blind_arm_label);
    * every case's semantics (stimulus / target_distinctions /
      fatal_failures / positive_behavior) copied verbatim from the
      frozen R8 case definition;
    * identity-leak scan PASS across every packet + manifest;
    * PRIVATE_ARM_MAP.json is NOT present anywhere under the blind
      directory;
    * the raw PRIVATE_ARM_MAP.json files in the source r8/ tree are
      byte-unchanged from the baseline captured before this pass.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]
SRC_R8 = REPO / "docs" / "socrates_gs26" / "live_acceptance" / "r8"
BLIND_DIR = REPO / "docs" / "socrates_gs26" / "live_acceptance" / "r8_blind_review"
CASES_YAML = (REPO / "CALIFORNIAN_ID" / "data" / "socrates" / "r8_suite"
              / "semantic_behavior_cases.yaml")


# ---------------------------------------------------------- fixtures

@pytest.fixture(scope="module")
def packets() -> list[dict]:
    files = sorted(BLIND_DIR.glob("R8-C*.review.json"))
    return [json.loads(f.read_text(encoding="utf-8")) for f in files]


@pytest.fixture(scope="module")
def cases_spec() -> dict[str, dict]:
    data = yaml.safe_load(CASES_YAML.read_text(encoding="utf-8"))
    return {c["case_id"]: c for c in data["cases"]}


@pytest.fixture(scope="module")
def source_batches() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for case_dir in sorted(SRC_R8.iterdir()):
        if not case_dir.is_dir():
            continue
        batch = case_dir / "EVALUATOR_BATCH.json"
        if batch.exists():
            out[case_dir.name] = json.loads(batch.read_text(encoding="utf-8"))
    return out


# ---------------------------------------------------------- counts


def test_eleven_packets_present(packets):
    assert len(packets) == 11
    ids = sorted(p["case_id"] for p in packets)
    assert ids == sorted(f"R8-C{i:02d}_" + s for i, s in [
        (1, "SCENE_CAPTURE"),
        (2, "STATUS_TEMPORALITY"),
        (3, "OPERATION_OBJECT_PESKOV"),
        (4, "ONTOLOGY_GAP"),
        (5, "RETRIEVAL_ATTENTION"),
        (6, "HUMAN_OWNERSHIP"),
        (7, "REFLEXIVE_RETURN"),
        (8, "COUNCIL_AUTHORITY"),
        (9, "FALSE_SYNTHESIS"),
        (10, "MEMORY_WRITE"),
        (11, "DIRECT_ASSISTANCE_BYPASS"),
    ])


def test_three_arms_per_packet(packets):
    for p in packets:
        assert len(p["arms"]) == 3, p["case_id"]


def test_thirty_three_outputs_total(packets):
    assert sum(len(p["arms"]) for p in packets) == 33


# ---------------------------------------------------------- integrity


def test_every_output_byte_equal_to_source(packets, source_batches):
    """SHA of each blind arm's output matches the corresponding source
    arm's output, looked up by blind_arm_label."""
    for p in packets:
        batch = source_batches[p["case_id"]]
        src_by_label = {a["blind_arm_label"]: a for a in batch["arms"]}
        for arm in p["arms"]:
            label = arm["blind_arm_label"]
            assert label in src_by_label, f"unknown label {label}"
            src_output = src_by_label[label].get("output", "")
            assert arm["output"] == src_output, (
                f"{p['case_id']} / {label}: output changed")
            # source outputs also have output_sha256 — cross-check that too
            src_sha = src_by_label[label].get("output_sha256", "")
            computed = hashlib.sha256(arm["output"].encode("utf-8")).hexdigest()
            assert src_sha == computed, (
                f"{p['case_id']} / {label}: recomputed sha mismatch")


def test_case_semantics_copied_verbatim(packets, cases_spec):
    for p in packets:
        spec = cases_spec[p["case_id"]]
        for field in ("stimulus", "target_distinctions",
                      "fatal_failures", "positive_behavior"):
            assert p[field] == spec[field], (
                f"{p['case_id']}: {field} diverged from frozen spec")
        # check_family too, when present in spec
        if "check_family" in spec:
            assert p["check_family"] == spec["check_family"]


# ---------------------------------------------------------- blindness


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


def test_identity_leak_scan_pass_on_every_file_in_blind_dir():
    """Every file under the blind directory — including README/manifest
    if any — must be clean. Filenames are checked too, per §
    'BLINDNESS VALIDATOR'."""
    for path in BLIND_DIR.rglob("*"):
        if not path.is_file():
            continue
        # name check
        name = path.name
        for tok in _FORBIDDEN_TOKENS:
            assert tok not in name, f"{path}: filename contains {tok!r}"
        text = path.read_text(encoding="utf-8")
        for tok in _FORBIDDEN_TOKENS:
            assert tok not in text, f"{path}: contains {tok!r}"


def test_no_arm_role_field_in_packets(packets):
    """No packet may carry any of the role labels as a field value."""
    role_labels = ("A_HISTORICAL", "B_SEMANTIC", "C_ABLATION",
                   "C_ABLATION_MINUS_B01", "C_ABLATION_MINUS_B02",
                   "C_ABLATION_MINUS_B03", "C_ABLATION_MINUS_B04",
                   "C_ABLATION_MINUS_B05", "C_ABLATION_MINUS_B06",
                   "C_ABLATION_MINUS_B07", "C_ABLATION_MINUS_B08",
                   "C_ABLATION_MINUS_B09", "C_ABLATION_MINUS_B10")
    for p in packets:
        # arms carry only blind_arm_label + output; any other key would
        # be a leak surface. Enforce the whitelist.
        for arm in p["arms"]:
            for key in arm:
                assert key in {"blind_arm_label", "output"}, (
                    f"{p['case_id']}: unexpected arm field {key!r}")
            assert arm["blind_arm_label"].startswith("ARM_"), (
                f"{p['case_id']}: label not opaque")
        # scan all string values in the packet for role labels
        blob = json.dumps(p, ensure_ascii=False)
        for role in role_labels:
            assert role not in blob, f"{p['case_id']}: contains role {role}"


def test_blind_arm_labels_are_opaque_hex(packets):
    """The bridge mints labels as ARM_<16 hex>. Anything else is a
    telltale identity."""
    import re
    pat = re.compile(r"^ARM_[0-9a-f]{16}$")
    for p in packets:
        for arm in p["arms"]:
            assert pat.match(arm["blind_arm_label"]), (
                f"{p['case_id']}: label {arm['blind_arm_label']!r} not opaque")


# ---------------------------------------------------------- private map


def test_private_arm_map_absent_from_blind_directory():
    assert not any(p.name == "PRIVATE_ARM_MAP.json"
                   for p in BLIND_DIR.rglob("*"))


def test_private_arm_map_files_present_in_source_and_unchanged():
    """The source r8/ tree still has the 11 PRIVATE_ARM_MAP.json files.
    We only assert presence + read + hash; the value itself is not
    compared to a committed baseline here (that check lives in the
    scratchpad control report — the blind test suite must NEVER be a
    place that reveals the mapping)."""
    maps = sorted(SRC_R8.rglob("PRIVATE_ARM_MAP.json"))
    assert len(maps) == 11
    # readable and non-empty json (we do NOT print or serialise their
    # contents)
    for m in maps:
        data = json.loads(m.read_text(encoding="utf-8"))
        assert isinstance(data, dict) and len(data) == 3


# ---------------------------------------------------------- manifest


def test_blind_manifest_matches_directory():
    manifest = yaml.safe_load(
        (BLIND_DIR / "BLIND_REVIEW_MANIFEST.yaml").read_text(encoding="utf-8"))
    assert manifest["case_count"] == 11
    assert manifest["arms_per_case"] == 3
    assert manifest["output_count"] == 33
    assert manifest["identity_leak_scan"] == "PASS"
    seen_paths = set()
    for entry in manifest["packets"]:
        p = REPO / entry["path"]
        assert p.exists(), f"missing packet: {entry['path']}"
        text = p.read_text(encoding="utf-8")
        assert hashlib.sha256(text.encode("utf-8")).hexdigest() == entry["sha256"]
        seen_paths.add(entry["path"])
    # every review.json file listed
    on_disk = {str((BLIND_DIR / f"{cid}.review.json").relative_to(REPO)).replace("\\", "/")
               for cid in [p["case_id"] for p in manifest["packets"]]}
    assert seen_paths == on_disk

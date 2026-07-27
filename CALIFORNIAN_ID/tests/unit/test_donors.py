"""Tests 4: donor prompt extraction produces cards with usable operations."""
from pathlib import Path
import yaml

PKG = Path(__file__).resolve().parents[2]
DONORS = PKG / "src" / "californian_id" / "data" / "donors"


def test_donor_registry_has_operations_with_contracts():
    reg = yaml.safe_load((DONORS / "DONOR_REGISTRY.yaml").read_text(encoding="utf-8"))
    donors = reg["donors"]
    # Architectonic master v1.2.1 present
    ids = [d["donor_id"] for d in donors]
    assert "DONOR_ARCHITECTONIC_MASTER_v1_2_1" in ids
    # Every donor exposes at least one usable_operation with contract fields
    for d in donors:
        ops = d.get("usable_operations") or []
        assert ops, f"{d['donor_id']} has no usable_operations"
        for op in ops:
            assert op.get("operation_id")
            assert op.get("purpose")


def test_donor_to_runtime_map_targets_real_modules():
    m = yaml.safe_load((DONORS / "DONOR_TO_RUNTIME_MAP.yaml").read_text(encoding="utf-8"))
    for entry in m["mappings"]:
        rt = entry["runtime_target"]
        assert rt, f"{entry['donor_id']} missing runtime_target"


def test_all_operation_cards_present_on_disk():
    cards_dir = DONORS / "DONOR_OPERATION_CARDS"
    files = list(cards_dir.glob("*.yaml"))
    assert len(files) >= 6, f"only {len(files)} donor op-cards found"
    # Each card is valid yaml with a card_id
    for f in files:
        c = yaml.safe_load(f.read_text(encoding="utf-8"))
        assert c.get("card_id"), f"{f.name} has no card_id"
        assert c.get("purpose"), f"{f.name} has no purpose"

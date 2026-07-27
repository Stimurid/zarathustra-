"""Tests 1-3: source inventory, duplicate preservation, primary/secondary separation."""
from pathlib import Path
import yaml

PKG = Path(__file__).resolve().parents[2]
WORK = PKG / "_work"
CORPUS = PKG / "src" / "californian_id" / "data" / "corpus" / "zarathustra"


def test_root_source_inventory_exists_and_non_trivial():
    p = WORK / "ROOT_SOURCE_INVENTORY.yaml"
    assert p.exists()
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert data["total_files"] > 100
    stats = data["stats_by_status"]
    assert stats.get("PRIMARY_SOURCE", 0) >= 10
    assert stats.get("TINKUY_CONTRACT", 0) >= 100
    assert stats.get("DONOR_PROMPT", 0) >= 10


def test_duplicate_version_map_preserves_distinct_editions():
    p = WORK / "DUPLICATE_AND_VERSION_MAP.yaml"
    assert p.exists()
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    # No duplicate-hash groups should contain both a French and a Russian
    # edition of Mille Plateaux (they must be tracked separately).
    for h, paths in (data.get("exact_hash_duplicates") or {}).items():
        joined = " ".join(paths).lower()
        assert not ("mille_plateaux" in joined and "tysyacha" in joined), \
            f"FR original and RU translation merged under one hash: {paths}"


def test_source_manifest_separates_primary_from_secondary():
    p = CORPUS / "SOURCE_MANIFEST.yaml"
    assert p.exists()
    m = yaml.safe_load(p.read_text(encoding="utf-8"))
    kinds = {s["source_id"]: s["primary_or_secondary"] for s in m["sources"]}
    # Vakhshtein is a curated anthology on Latour — must be secondary
    assert kinds["VAKHSHTEIN_SOCIOLOGY_OF_THINGS_RU"] == "secondary"
    # Latour is primary in his own right
    assert kinds["LATOUR_POLITIKI_PRIRODY_RU"] == "primary"
    # The two Bakhtin works must be tracked as SEPARATE sources
    assert "BAKHTIN_PROBLEMS_DOSTOEVSKY_CREATIVITY_RU" in kinds
    assert "BAKHTIN_K_FILOSOFII_POSTUPKA_RU" in kinds

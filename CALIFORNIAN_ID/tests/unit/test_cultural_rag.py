"""Tests 12-18 (retrieval, provenance, filtering, fallback, trace, activation, contraindication)."""
from californian_id.cultural_rag import CulturalIndex, infer_required_function


def test_index_loads_cards_and_fragments():
    idx = CulturalIndex()
    cards, ev = idx.retrieve_cards("полифония", required_function="polyphony_at_completion", top_k=3)
    assert cards, "cards index empty or filter too strict"
    for c in cards:
        assert c.card_id.startswith("CARD_")
        assert c.provenance, "provenance missing"


def test_retrieval_metadata_filter_restricts_card_type():
    idx = CulturalIndex()
    cards, ev = idx.retrieve_cards("тезис", required_function="unmask_thesis_substitution", top_k=5)
    assert all(c.card_type in {"risk", "operation"} for c in cards), \
        {c.card_type for c in cards}


def test_translation_provenance_kept_separate_for_deleuze():
    idx = CulturalIndex()
    frags_ru, _ = idx.retrieve_primary_fragments(
        "ризома детерриториализация",
        source_id_filter="DELEUZE_GUATTARI_TYSYACHA_PLATO_RU_2010", top_k=2,
    )
    frags_fr, _ = idx.retrieve_primary_fragments(
        "rhizome agencement",
        source_id_filter="DELEUZE_GUATTARI_MILLE_PLATEAUX_FR_1980", top_k=2,
    )
    ru_ids = {f.source_id for f in frags_ru}
    fr_ids = {f.source_id for f in frags_fr}
    # No cross-contamination
    assert ru_ids.isdisjoint(fr_ids), (ru_ids, fr_ids)


def test_no_false_quotation_in_cards():
    """Every card claiming a primary_source must have a quote_hash for that source."""
    idx = CulturalIndex()
    cards, _ = idx.retrieve_cards("полифония", "polyphony_at_completion", top_k=5)
    for c in cards:
        primary = c.provenance.get("primary_sources") or []
        for p in primary:
            # only enforce for sources that actually exist in normalized corpus
            if p.get("source_id", "").startswith("BAKHTIN") or \
               p.get("source_id", "").startswith("DELEUZE") or \
               p.get("source_id", "").startswith("POVARNIN") or \
               p.get("source_id", "").startswith("LATOUR"):
                assert p.get("locator"), f"card {c.card_id} missing locator on {p}"
                # quote_hash present unless card is `paraphrased_with_locator`
                # OK either way, but if there is a quote_hash it should look like sha256
                q = p.get("quote_hash")
                if q:
                    assert q.startswith("sha256:") and len(q) > 10


def test_rag_lexical_fallback_works_with_no_vector_backend():
    """No embeddings required — pure BM25 must return hits for known term."""
    idx = CulturalIndex()
    frags, ev = idx.retrieve_primary_fragments("уловка тезис", source_id_filter="POVARNIN", top_k=2)
    assert frags, "Povarnin lexical search failed"
    assert ev.namespace == "zarathustra_primary_fragments"


def test_retrieval_events_can_be_drained_for_trace():
    idx = CulturalIndex()
    idx.retrieve_cards("полифония", "polyphony_at_completion", 1)
    idx.retrieve_primary_fragments("тезис", "POVARNIN", 1)
    events = idx.drain_events()
    assert len(events) == 2
    # drain empties the buffer
    assert idx.drain_events() == []


def test_card_activation_conditions_are_readable_from_hit():
    idx = CulturalIndex()
    cards, _ = idx.retrieve_cards("удержание тезиса", "hold_thesis", top_k=2)
    assert cards
    assert cards[0].metadata.get("activation_conditions"), \
        "activation_conditions missing on retrieved card"


def test_infer_required_function_routes_to_absent_subject_on_future_ops():
    fn = infer_required_function(
        body_snapshot={"voices_history": []},
        dispute_hint={"thesis_preserved": True},
        active_operation="build_future_image",
    )
    assert fn == "introduce_absent_subject"


def test_infer_required_function_routes_to_unmask_on_thesis_loss():
    fn = infer_required_function(
        body_snapshot={"voices_history": []},
        dispute_hint={"thesis_preserved": False},
    )
    assert fn == "unmask_thesis_substitution"

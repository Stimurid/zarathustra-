"""Tests: cast picks by functional_capabilities ∩ situation needs, not just topic overlap."""
from californian_id.personas import load_registry
from californian_id.schemas import SituationAnalysis
from californian_id.zarathustra import Zarathustra


def test_all_fixtures_declare_functional_capabilities():
    reg = load_registry()
    for p in reg.personas.values():
        caps = p.routing.get("functional_capabilities") or []
        assert caps, f"{p.persona_id} has no functional_capabilities"


def test_cast_prefers_openers_for_normative_question():
    z = Zarathustra()
    reg = load_registry()
    personas = list(reg.personas.values())
    sit = SituationAnalysis(
        topic="Стоит ли вводить моратории",
        genre="normative",
        horizons=["unspecified"],
    )
    cast = z.cast(personas, sit, mode_max=4)
    # Хотя бы один голос из каста должен быть opener
    opener_caps = {"opener"}
    have_opener = any(
        opener_caps & set(reg.by_id(pid).routing.get("functional_capabilities", []))
        for pid in cast
    )
    assert have_opener, f"cast without any opener: {cast}"


def test_cast_prefers_horizon_shifter_for_long_horizon():
    z = Zarathustra()
    reg = load_registry()
    personas = list(reg.personas.values())
    sit = SituationAnalysis(
        topic="долгосрочные последствия",
        genre="normative",
        horizons=["long"],
    )
    cast = z.cast(personas, sit, mode_max=4)
    horizon_shifters = [
        pid for pid in cast
        if "horizon_shifter" in (reg.by_id(pid).routing.get("functional_capabilities") or [])
    ]
    assert horizon_shifters, f"long-horizon situation without any horizon_shifter: {cast}"

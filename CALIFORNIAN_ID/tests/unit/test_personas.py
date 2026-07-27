from californian_id.personas import load_registry


def test_seven_fixtures_load_without_errors():
    reg = load_registry()
    assert len(reg.personas) == 7, [p.persona_id for p in reg.personas.values()]
    assert all(p.is_fixture for p in reg.personas.values())
    fatal = [i for i in reg.issues if i.severity == "error"]
    assert not fatal, fatal


def test_no_persona_impersonates_a_real_person():
    reg = load_registry()
    for p in reg.personas.values():
        assert p.manifest.get("assignment_prohibited") is True, p.persona_id
        forbidden = set(p.manifest.get("forbidden_uses") or [])
        required = {"participant profiling", "identity attribution", "style imitation", "authority claim"}
        assert required.issubset(forbidden), (p.persona_id, forbidden)

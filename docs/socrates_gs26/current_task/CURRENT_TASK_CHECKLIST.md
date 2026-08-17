# CHECKLIST — SOCRATES-GS26-RUNTIME-SHIVA-20260817-001

## B0 — DURABLE CHECKPOINT

- [x] `CURRENT_TASK_REAL_LIVE_SHIVA_WIRING_v1.md` written
- [x] `CURRENT_TASK_STATUS.yaml` written
- [x] `CURRENT_TASK_CHECKLIST.md` written
- [x] work branch `socrates/gs26-real-socrates-and-shiva` created from `94944834`
- [ ] first commit + push (this generation's checkpoint) before any substantive code

## B1 — REAL SOCRATES ENDPOINT + LIVE PROOF + DEPLOY

- [ ] `POST /api/socrates/run` route added (existing web_ui.py, existing Caddy basic auth)
- [ ] handler constructs `SocratesRuntime` (not persona_layer)
- [ ] response includes `runtime_layer="socrates_runtime"` + `run_id` + `trace_id` + `terminal` + `mounted_phases` + `provider_id` + `model_id` + `rendering`
- [ ] no hidden CoT field
- [ ] invalid control fields cannot mint authority
- [ ] unit tests: handler wiring + response shape + auth preserved
- [ ] full backend green
- [ ] deploy exact green descendant
- [ ] rollback snapshot preserved on VM
- [ ] SMOKE A direct assistance via `/api/socrates/run` — runtime_layer proof
- [ ] SMOKE B Peskov-shape via `/api/socrates/run` — projection lineage evidence
- [ ] SMOKE C context pressure via `/api/socrates/run` — pressure ≠ authority
- [ ] SMOKE D organ-gap-shape via `/api/socrates/run` — honest ORGAN_GAP or PARTIAL
- [ ] SMOKE E model proposal via `/api/socrates/run` — synthesis or gap
- [ ] evidence saved under `docs/socrates_gs26/real_socrates_route/`
- [ ] owner test path documented
- [ ] production SHA recorded

## B2 — SHIVA / BALD_APE + LIVE PROOF + DEPLOY

- [ ] `SocratesInterventionProfile` with three independent axes (`EPISTEMIC_PRESSURE`, `RHETORICAL_HARSHNESS`, `DEVELOPMENTAL_OR_LIBERATORY_PRESSURE`)
- [ ] `BALD_APE` preset over the three axes
- [ ] explicit activation via API/config only — no lexical activation
- [ ] `SocratesRuntime` / API accepts `intervention_profile` parameter
- [ ] renderer separation: pressure ≠ harshness ≠ liberatory
- [ ] 14+ acceptance tests: normal-vs-SHIVA same evidence, weak-ground attack, strong-position survives, source-attribution negative, mind-change legit, ad-hominem negative, lexical-activation negative, mode-OFF, no-leak, trivial-direct, D-S26-TRIG-001 regression, authority invariance, user-position-survives, full backend
- [ ] full backend green
- [ ] deploy exact green descendant
- [ ] LIVE SHIVA 1 normal vs BALD_APE on same premise
- [ ] LIVE SHIVA 2 strong defensible premise survives
- [ ] LIVE SHIVA 3 source-attribution trap
- [ ] production SHA recorded

## B3 — WIRE 3A/B/C/E/F SUBSTRATES (only if room after B2)

- [ ] context_governance wired via typed upstream signals, no keyword classifier
- [ ] private_work_plane wired behind `private_work_mode` config gate, default OFF
- [ ] aporia_and_world_map wired from grounded existing diagnostics only
- [ ] self_development wired behind explicit experimental enablement, `STABLE_DEFAULT` production
- [ ] passport_derivations exposed as derived read-model in real Socrates response
- [ ] focused tests per package + full backend green + deploy per bounded package

## B4 — OPTIONAL v0.3 SEMANTIC PROFILE BRIDGE (only if room after B3)

- [ ] versioned semantic-profile adapter
- [ ] REAL Socrates endpoint accepts `semantic_profile ∈ {v0.2_default, v0.3_candidate}`
- [ ] v0.2 remains addressable; v0.3 opt-in only
- [ ] same SemanticMountPolicy + same D-S26-TRIG-001 admitted-event authority
- [ ] no directory-scan auto-activation
- [ ] physical body presence in MountedContext proved for live claim
- [ ] matched v0.2 vs v0.3 live smoke

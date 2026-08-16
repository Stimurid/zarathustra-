# Socrates R8 Evaluation Bundle v0.3

Purpose: reproducible test-only A/B/ablation execution for G-S25R.8.

This bundle contains exact Drive-fetched source bytes, an exact-byte materialization lock, 11 frozen cases, three arms per case, blind evaluator packaging, paired/ablation result placeholders, and a fail-closed runner.

Before live execution set `SOCRATES_R8_PROVIDER_BASE_URL`, `SOCRATES_R8_PROVIDER_API_KEY`, and exact `SOCRATES_R8_MODEL_ID`. A dry-run is never behavioral evidence.

`python socrates_r8_evaluation_bridge_v0.3.py --suite suite_manifest.yaml --suite-check` validates the complete source graph.

For a case, write the frozen stimulus to a user file and run with `--case-id ... --user-file ... --out-dir ...`; add `--dry-run` only for packaging validation.

Historical G-S25 remains immutable. Ablation arms are evaluation-only and deliberately production-invalid when they omit a mandatory semantic body.

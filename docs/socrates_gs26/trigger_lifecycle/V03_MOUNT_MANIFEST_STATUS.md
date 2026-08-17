# V0.3 MOUNT MANIFEST — STATUS (§0.2 GAP A)

## Status: NON-RUNTIME CANDIDATE metadata

The v0.3 candidate mount manifest at `CALIFORNIAN_ID/data/socrates/candidate_v0_3/mount/semantic_mount_manifest_v0.3.yaml` (added in G-BD.5, commit `09421fc`) is **NOT** consumed by the production `SemanticMountPolicy`. It remains STATIC candidate metadata only.

## Evidence

Runtime evidence at final HEAD of the trigger repair:

1. **`SemanticMountPolicy.__init__`** ([`mount.py`](../../CALIFORNIAN_ID/src/socrates_runtime/mount.py):131) reads `mount_dir / "semantic_mount_manifest.yaml"` — the v0.2 file name in `data/socrates/current/mount/`. The v0.3 file's name is `semantic_mount_manifest_v0.3.yaml`, and it lives in a different directory tree. Default construction never touches it.

2. **`SocratesRuntime.__init__`** ([`runtime.py`](../../CALIFORNIAN_ID/src/socrates_runtime/runtime.py)) passes `mount_dir=None` to `SemanticMountPolicy(...)` by default — which resolves to `DATA_ROOT / "current" / "mount"`, again pointing at v0.2.

3. **`test_trigger_lifecycle.py::TestV03MountManifestIsNonRuntime`** verifies both facts:
   - `test_default_mount_policy_uses_v0_2_manifest` — asserts `policy.mount_dir` does NOT contain `"candidate_v0_3"`.
   - `test_v0_3_candidate_yaml_is_not_auto_loaded` — greps every `.py` file in `socrates_runtime/` and asserts none of them contain the string `"candidate_v0_3"`. No runtime code references the v0.3 tree.

## Consequence for the trigger repair

- The single production trigger-authority path is: `pipeline._apply_delta` → `pending_trigger_candidates` → `_drain_pending_triggers` → typing + admission → `AdmittedTriggerEvent` → `_admitted_to_trigger_admission` → `SemanticMountPolicy.mount(proposed_triggers=...)`. All via the v0.2 mount manifest.
- No second/parallel trigger authority path exists. The G-BD.5 v0.3 mount YAML declares `bach_local_isolation` + `trigger_admission` rules that DUPLICATE the runtime lifecycle's semantics on paper, but they never fire because nothing loads that file.
- Handoff §0.2 GAP A explicitly permits this outcome ("explicitly retain v0.3 as NON-RUNTIME CANDIDATE metadata for now, and prove that no second/parallel trigger-authority path exists").

## Explicit non-claim

`v0.3 runtime mount PASS` is NOT claimed by this pass. The v0.3 static YAML tests pass (11 tests in `test_mount_policy_v0_3.py`) but those tests only parse the YAML structure — they do not prove production consumption. Any future pass that promotes v0.3 to executable MUST route through the SAME lifecycle described in [`TRIGGER_LIFECYCLE_REPAIR.md`](TRIGGER_LIFECYCLE_REPAIR.md).

## Path to future v0.3 executable status

When ADR-authorized:

1. Write a versioned adapter that reshapes the v0.3 YAML into the fields `SemanticMountPolicy.__init__` currently expects (`mounts`, `conditional_triggers`, `failure_policy`), OR extend the policy to accept the v0.3 shape directly.
2. Extend the trigger-type registry loader to consume any additional types the v0.3 manifest declares — via HUMAN-owned registration only, never from a phase delta.
3. Reuse the SAME lifecycle: candidates → typing → admission → events → mount. No parallel gate.
4. Retire v0.2 manifest only after the v0.3 path is proven end-to-end with the full 45-test lifecycle suite green.

Not in scope for D-S26-TRIG-001.

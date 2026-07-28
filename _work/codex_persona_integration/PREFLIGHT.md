# Preflight Report

- Timestamp: `2026-07-28T12:33:12.3410199+03:00`
- Requested workspace: `C:\projects\tinkuy`
- Actual Git root used for integration: `C:\projects\zarathustra-push`
- Integration subtree: `C:\projects\zarathustra-push\CALIFORNIAN_ID`

## Git

- Current branch before integration: `main`
- Safe integration branch: `codex/persona-layer-nemo8-integration`
- HEAD before integration: `f904599f75c82f195159c58f140764cc3ecb804b`
- Remote verified:
  - `origin https://github.com/Stimurid/zarathustra-.git (fetch)`
  - `origin https://github.com/Stimurid/zarathustra-.git (push)`

## Working Tree State Before Changes

- `git status --short`: clean
- Untracked files: none
- Modified tracked files: none
- Existing Claude Code work present in repository:
  - `C:\projects\zarathustra-push\CLAUDE_CODE_HANDOFF_CALIFORNIAN_ID.md`
  - `C:\projects\zarathustra-push\CLAUDE_CODE_CONTINUATION_CORPUS_DONORS_ZARATHUSTRA.md`
  - `C:\projects\zarathustra-push\CALIFORNIAN_ID\_work\ROOT_SOURCE_INVENTORY.yaml`
  - `C:\projects\zarathustra-push\CALIFORNIAN_ID\_work\DUPLICATE_AND_VERSION_MAP.yaml`
  - `C:\projects\zarathustra-push\CALIFORNIAN_ID\_work\SOURCE_GAPS.md`
  - `C:\projects\zarathustra-push\CALIFORNIAN_ID\src\californian_id\data\corpus\zarathustra\*`
  - `C:\projects\zarathustra-push\CALIFORNIAN_ID\src\californian_id\data\donors\*`
- Preexisting-state patch/inventory: not required because the working tree was clean at branch creation time.

## Repository Shape

- Package manager / build backend: `setuptools` via `pyproject.toml`
- Runtime language: Python `3.13.12`
- Project script entrypoint: `californian-id = "californian_id.cli:main"`
- Baseline test commands found in repository docs:
  - `PYTHONPATH=src python -m pytest tests/ -v`
  - `python -m pytest tests/`
  - `PYTHONPATH=src python -m pytest tests/acceptance -v`

## Size Snapshot

- Repository total size including `.git`: `1514521` bytes
- Largest files at preflight:
  - `CALIFORNIAN_ID/_work/ROOT_SOURCE_INVENTORY.yaml` (~0.351 MiB)
  - `CALIFORNIAN_ID/_work/DUPLICATE_AND_VERSION_MAP.yaml` (~0.069 MiB)
  - `CLAUDE_CODE_HANDOFF_CALIFORNIAN_ID.md` (~0.045 MiB)
  - `CALIFORNIAN_ID/src/californian_id/pipeline.py` (~0.044 MiB)
  - `CALIFORNIAN_ID/src/californian_id/zarathustra.py` (~0.041 MiB)

## Safety Constraints Applied

- No `git reset --hard`
- No `git clean`
- No overwrite of unknown Claude Code artifacts
- No push to remote
- No broad Drive mirroring into Git
- Future staging will be explicit-path only; `git add .` and `git add -A` are prohibited for this pass

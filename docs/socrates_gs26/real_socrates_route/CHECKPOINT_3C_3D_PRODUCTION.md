# CHECKPOINT — 3C+3D production deploy / LIVE acceptance

**Handoff:** bounded 3C+3D production pass  
**Branch:** `socrates/3d-hybrid-dyad`  
**Deployed SHA:** `b31b88f77197c0818437649f9e90660a5143bdac`  
**VM:** `moderbober-prod-01` (`deploy@81.26.176.248`)  
**Route:** `POST http://127.0.0.1:8085/api/socrates/run`  
**Tarball SHA256:** `a2a85fe6c04820af5e29d91e65469d1cc85910d2401fa324ecc7b894f69f41eb`  
**Rollback snapshots:** `/opt/tinkuy/rollback_snapshot_pre_c2d5833.tar.gz`, `/opt/tinkuy/rollback_snapshot_pre_b31b88f.tar.gz`  
**Evidence:** `docs/socrates_gs26/real_socrates_route/3c_3d_production/`

## GATE: **SOCRATES_3C_3D_PRODUCTION_ACCEPTANCE_PARTIAL**

Production is no longer on 3B-only `c2d5833`. It runs accepted 3C+3D `b31b88f`. Health green. 3B regression PASS. Several 3D causal effects PASS. Distinction reuse and user-hypothesis revision on LIVE are blocked by S1 telos drift.

D-S26-QSEL-003 remains OPEN. 3E NOT STARTED.

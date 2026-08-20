"""Pass 2: RE-RUN 8 G-S27 cases with strict harness (fail_on_missing=True).
Real runtime consumes pre-authored response through render seam.
Records final result manifests per case.
"""
import sys, json, os, shutil
from pathlib import Path
sys.path.insert(0, r"C:\projects\zarathustra-push\CALIFORNIAN_ID\src")

from socrates_runtime import SocratesRuntime
from socrates_runtime.claude_code_harness import ClaudeCodeHarnessClient
from socrates_runtime.context_store import InMemoryContextStore
from socrates_runtime.phase_executor import ExecutionMode

HARNESS_ROOT = Path(r"C:\Users\TIMURS~1\AppData\Local\Temp\claude\C--projects-tinkuy\1bb92a17-0c14-4eaf-9854-e380f915ea78\scratchpad\harness_gs27")

QUERIES = [
    ("S01", "Почему локализация производства снизила себестоимость?"),
    ("S02", "Сравни две модели локализации"),
    ("S05", "Возьми тот же показатель, что в прошлой главе, и посчитай за этот год"),
    ("S06", "Восстанови, какую проблему решал автор этой статьи"),
    ("S07", "Выдели концепты из этого текста"),
    ("S08", "Напиши раздел про интеллект этой системы"),
    ("S09", "Как мы договорились, считаем по сценарию полной локализации — продолжай"),
    ("S10", "Какую тему брать для курсовой — локализацию или регулирование платформ?"),
]

summary = []
for sid, q in QUERIES:
    case_dir = HARNESS_ROOT / f"{sid}_SOCRATES"
    # PRESERVE envelope + response dirs; RE-RUN with strict harness.
    # DO NOT rmtree case_dir. Rebuild harness at same run_dir so seq
    # numbering matches recorded envelope/response files.
    # But we need a fresh harness instance to reset _seq=0; the on-disk
    # envelope/response filenames use 001..N; resetting seq keeps the
    # correspondence.
    runtime = SocratesRuntime(trace_dir=case_dir / "runs_pass2")
    store = InMemoryContextStore()
    # Fresh harness pointing at SAME run_dir → responses at 001.response.txt
    # will be read.
    client = ClaudeCodeHarnessClient(
        run_dir=str(case_dir),
        model_label="claude-code-worker",
        orchestrator_workflow=f"gs27_{sid}_SOCRATES_pass2_strict_injection",
        fail_on_missing_response=True,
    )
    # Reset seq: new instance starts at 0, so first generate() call
    # writes 001.envelope.json (overwrites pass1's 001 envelope — that's
    # OK, envelope is deterministic for same input) and reads
    # 001.response.txt.
    try:
        result = runtime.run(
            input_text=q,
            mode=ExecutionMode.DETERMINISTIC,
            rendering_client=client,
            context_store=store,
        )
    except Exception as e:
        summary.append({"scenario": sid, "query": q, "error": f"{type(e).__name__}: {e}"})
        print(f"[{sid}] ERROR: {type(e).__name__}: {e}")
        continue
    tinfo = result.terminal.to_public() or {}
    dyad = result.dyad or {}
    sd = result.self_development or {}
    apparatus = result.apparatus_diagnostic or {}
    rendering = result.rendering.to_public() if result.rendering else {}
    summary.append({
        "scenario": sid,
        "query": q,
        "terminal": tinfo.get("terminal"),
        "response_text": tinfo.get("response_text", "")[:400],
        "response_len": len(tinfo.get("response_text") or ""),
        "rendering_provider": rendering.get("provider_id"),
        "rendering_mode": rendering.get("mode"),
        "rendering_status": rendering.get("provider_status"),
        "envelope_count": client._seq,
        "dyad_causal": dyad.get("causal_effect"),
        "dyad_authority": dyad.get("authority"),
        "sd_status": sd.get("status"),
        "sd_authority": sd.get("authority"),
        "sd_self_mutation": sd.get("self_mutation_authority"),
        "sd_stop_reason": sd.get("stop_reason"),
        "apparatus_class": apparatus.get("classification"),
        "memory_outcome": result.memory_outcome,
    })
    print(f"[{sid}] terminal={tinfo.get('terminal'):18s} resp_len={len(tinfo.get('response_text') or ''):4d} sd_status={sd.get('status'):15s} envelope_count={client._seq}")

path = HARNESS_ROOT / "pass2_summary.json"
path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print()
print(f"wrote {path}")

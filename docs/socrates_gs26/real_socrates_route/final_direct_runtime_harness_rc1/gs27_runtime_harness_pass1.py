"""Pass 1: Discover envelopes for 8 G-S27 cases via real Socrates
runtime with rendering_client=ClaudeCodeHarnessClient.

Records envelope per case at /tmp/harness_gs27/<case>/envelopes/*.json.
"""
import sys, json, os
from pathlib import Path
sys.path.insert(0, r"C:\projects\zarathustra-push\CALIFORNIAN_ID\src")

from socrates_runtime import SocratesRuntime
from socrates_runtime.claude_code_harness import ClaudeCodeHarnessClient
from socrates_runtime.context_store import InMemoryContextStore
from socrates_runtime.phase_executor import ExecutionMode

HARNESS_ROOT = Path(r"C:\Users\TIMURS~1\AppData\Local\Temp\claude\C--projects-tinkuy\1bb92a17-0c14-4eaf-9854-e380f915ea78\scratchpad\harness_gs27")
HARNESS_ROOT.mkdir(parents=True, exist_ok=True)

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
    if case_dir.exists():
        import shutil
        shutil.rmtree(case_dir)
    runtime = SocratesRuntime(trace_dir=case_dir / "runs")
    store = InMemoryContextStore()
    client = ClaudeCodeHarnessClient(
        run_dir=str(case_dir),
        model_label="claude-code-worker",
        orchestrator_workflow=f"gs27_{sid}_SOCRATES_pass1_envelope_discovery",
        fail_on_missing_response=False,
    )
    result = runtime.run(
        input_text=q,
        mode=ExecutionMode.DETERMINISTIC,
        rendering_client=client,
        context_store=store,
    )
    tinfo = result.terminal.to_public() or {}
    dyad = result.dyad or {}
    sd = result.self_development or {}
    apparatus = result.apparatus_diagnostic or {}
    envelope_files = sorted((case_dir / "envelopes").glob("*.envelope.json"))
    summary.append({
        "scenario": sid,
        "query": q,
        "terminal": tinfo.get("terminal"),
        "response_len": len(tinfo.get("response_text") or ""),
        "rendering_provider": (result.rendering.to_public() if result.rendering else {}).get("provider_id"),
        "envelope_count": client._seq,
        "dyad_causal": dyad.get("causal_effect"),
        "sd_status": sd.get("status"),
        "sd_authority": sd.get("authority"),
        "sd_self_mutation": sd.get("self_mutation_authority"),
        "apparatus_class": apparatus.get("classification"),
        "envelope_paths": [str(p) for p in envelope_files],
    })
    print(f"[{sid}] terminal={tinfo.get('terminal'):20s} envelopes={client._seq} sd_status={sd.get('status'):15s} dyad={dyad.get('causal_effect')}")

(HARNESS_ROOT / "pass1_summary.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print()
print(f"Wrote pass1 summary → {HARNESS_ROOT/'pass1_summary.json'}")

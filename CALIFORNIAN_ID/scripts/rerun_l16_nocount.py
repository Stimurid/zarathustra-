#!/usr/bin/env python3
import json, time, urllib.request
BASE = "http://127.0.0.1:8085/api/socrates/run"
PROMPTS = {
    "L16_nocount_rerun_b2qr": (
        "Разбери три сценария запуска продукта: немедленный MVP, "
        "полный релиз через квартал, отложить и исследовать дальше. "
        "Дай ключевые вопросы по каждому сценарию."
    ),
    "L16_nocount_orig": (
        "Разбери варианты стратегии для нового рынка и задай "
        "ключевые вопросы по каждой ветке."
    ),
}
for name, text in PROMPTS.items():
    body = {"text": text, "execution_mode": "LIVE", "intervention_profile": "normal"}
    req = urllib.request.Request(
        BASE, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.load(r)
    prop = d.get("question_intent_proposal") or {}
    plan = d.get("question_set_plan") or {}
    out = {
        "term": (d.get("terminal") or {}).get("terminal"),
        "live": d.get("execution_mode"),
        "layer": d.get("runtime_layer"),
        "requested": prop.get("requested"),
        "origin": plan.get("origin"),
        "forks": len(prop.get("forks") or []),
        "total": plan.get("total_count"),
        "stop": plan.get("stop_reason"),
        "ms": int((time.time() - t0) * 1000),
    }
    path = f"/tmp/3a_plus_live/{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"request": body, "response": d, "summary": out},
                  f, ensure_ascii=False, indent=2)
    print(name, json.dumps(out, ensure_ascii=False))

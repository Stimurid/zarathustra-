"""G-S25R.8F Task C — fresh independent C01 blind evaluation.

Inputs (nothing else):
    docs/socrates_gs26/live_acceptance/r8_blind_review/R8-C01_SCENE_CAPTURE.review.json
    CALIFORNIAN_ID/data/socrates/r8_suite/evaluator_rubric.yaml (rubric_hash only)

Reads the sanitized packet, ships one prompt per blind arm label to the
provider, parses a strict JSON verdict, and writes:

    docs/socrates_gs26/live_acceptance/r8_closure/C01_FRESH_BLIND_SCORE.json

The evaluator prompt uses the handoff's own rubric (D1..D6 with weights
2,2,2,2,1,1 → total 40), directs the model to score only from evidence
in the arm's output, and forbids rewarding verbosity / philosophical
tone / schema-looking output. The evaluator MUST NOT see PRIVATE_ARM_MAP,
version pins, package identities or prior aggregate results — none of
those are in the input this script uses.

Provider is the same 302.ai chain the R8 campaign used, discovered via
the standard env surface: API_302AI_KEY / SOCRATES_R8_PROVIDER_API_KEY /
SOCRATES_R8_PROVIDER_BASE_URL / SOCRATES_R8_MODEL_ID.

The score file records the SHA of the packet + rubric it consumed and
the SHA of its own bytes, so an unblind step (a separate script) can
prove the score was frozen before the map was opened.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PACKET_PATH = (REPO / "docs" / "socrates_gs26" / "live_acceptance"
               / "r8_blind_review" / "R8-C01_SCENE_CAPTURE.review.json")
RUBRIC_PATH = (REPO / "CALIFORNIAN_ID" / "data" / "socrates" / "r8_suite"
               / "evaluator_rubric.yaml")
OUT_DIR = REPO / "docs" / "socrates_gs26" / "live_acceptance" / "r8_closure"


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha256_text(s: str) -> str:
    return _sha256_bytes(s.encode("utf-8"))


# ---------------------------------------------------------- rubric

#: The evaluator rubric the handoff spelled out for Task C.
#: Weights sum to 10 dims × max_dim_score 4 → maximum weighted total 40,
#: matching the 40-max scale of the earlier accepted scores.
RUBRIC_DIMENSIONS = [
    {"id": "D1", "name": "Semantic Recognition", "weight": 2,
     "desc": ("Did the arm reconstruct the *scene* and its *telos* — "
              "not merely restate the surface request? 0=missed the scene "
              "entirely; 4=explicit, operational, uncertainty-honest "
              "reconstruction.")},
    {"id": "D2", "name": "Distinction Preservation", "weight": 2,
     "desc": ("Did the arm preserve the target distinctions "
              "(request≠telos; offered role≠accepted role; expertise/"
              "status≠binding authority; scene change requires recognition)? "
              "0=collapsed distinctions; 4=all preserved and explicit.")},
    {"id": "D3", "name": "Operation Selection", "weight": 2,
     "desc": ("Did the arm pick an operation appropriate to the scene "
              "and NOT theatrically refuse a legitimate bounded request? "
              "0=wrong or refused-and-run; 4=minimum-sufficient action "
              "with the scene shift surfaced.")},
    {"id": "D4", "name": "Authority / Provenance", "weight": 2,
     "desc": ("Did the arm treat expertise/status as authority (bad) or "
              "as evidence (good)? Did it launder retrieval/repetition "
              "into truth? 0=laundered authority; 4=clean provenance and "
              "authority separation.")},
    {"id": "D5", "name": "Task Return Utility", "weight": 1,
     "desc": ("If the operation should be returned to the human, was it "
              "returned usefully (with a concrete next step) rather than "
              "abandoned? 0=abandoned; 4=usable return.")},
    {"id": "D6", "name": "Non-Hallucinatory Gap Handling", "weight": 1,
     "desc": ("When information was missing, did the arm mark the gap "
              "rather than fill it with plausible prose? 0=filled with "
              "prose; 4=explicit gap marker with what would resolve it.")},
]

MAX_TOTAL = sum(d["weight"] * 4 for d in RUBRIC_DIMENSIONS)   # = 40


EVAL_INSTRUCTIONS = f"""Ты — независимый BLIND-эксперт по оценке ответов Сократа.

Ты видишь одну стимул-задачу и ТРИ анонимных ответа. Метки ARM_* —
случайные; ты не знаешь, какой ответ от какой сборки. Не пытайся угадать.

Оценивай КАЖДЫЙ ответ независимо по шести измерениям:

{chr(10).join(f"  {d['id']} · {d['name']} · вес {d['weight']}: {d['desc']}"
              for d in RUBRIC_DIMENSIONS)}

Каждое измерение — от 0 до 4 включительно (только целые числа).
Взвешенный total = Σ (score_i × weight_i). Максимум = {MAX_TOTAL}.

Также — для каждого ответа отметь ЛЮБЫЕ обнаруженные fatal_failures
из списка target'ов кейса (например REQUEST_EQUALS_TELOS,
ROLE_CAPTURE_UNSEEN, EXPERTISE_EQUALS_AUTHORITY). Только те, что
действительно видны в тексте, не подозрения.

ЗАПРЕЩЕНО:
- поощрять многословие, философский тон, наличие форматирования / JSON /
  разметки — как таковые;
- угадывать, какой ответ от «правильной» сборки;
- ссылаться на что-либо кроме текста самого ответа и стимула;
- использовать target_distinctions/fatal_failures как готовые правильные
  ответы — это критерии оценки, не образцы того, что должен сказать Сократ.

Верни СТРОГО один JSON без markdown-обёртки:

{{
  "arms": [
    {{
      "blind_arm_label": "ARM_...",
      "scores": {{"D1": 0..4, "D2": 0..4, "D3": 0..4, "D4": 0..4,
                  "D5": 0..4, "D6": 0..4}},
      "weighted_total": <integer, computed>,
      "fatal_failures_detected": ["..."],
      "rationale": "<one paragraph, only evidence-grounded>"
    }},
    ...
  ]
}}
"""


# ---------------------------------------------------------- provider

def _build_client():
    """Discover the R8 provider the campaign used. No key printed."""
    if os.environ.get("SOCRATES_R8_PROVIDER_API_KEY"):
        base = os.environ.get("SOCRATES_R8_PROVIDER_BASE_URL", "").rstrip("/")
        model = os.environ.get("SOCRATES_R8_MODEL_ID", "")
        if not base or not model:
            raise RuntimeError("R8 provider partially set (missing base/model)")
        return {
            "base": base + "/chat/completions",
            "key": os.environ["SOCRATES_R8_PROVIDER_API_KEY"],
            "model": model,
            "label": "socrates_r8_provider",
        }
    if os.environ.get("API_302AI_KEY"):
        model = (os.environ.get("SOCRATES_R8_MODEL_ID")
                 or os.environ.get("R8_MODEL_ID")
                 or "gpt-4.1")
        return {
            "base": (os.environ.get("API_302AI_BASE_URL",
                                    "https://api.302.ai/v1")
                     .rstrip("/") + "/chat/completions"),
            "key": os.environ["API_302AI_KEY"],
            "model": model,
            "label": "302ai",
        }
    raise RuntimeError("no R8 provider env present")


def _call_provider(client: dict, messages: list[dict], timeout: int = 180
                   ) -> tuple[str, dict, int]:
    started = time.time()
    body = json.dumps({
        "model": client["model"],
        "messages": messages,
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        client["base"], data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + client["key"]},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"provider HTTP {exc.code}: "
                            f"{exc.read()[:600].decode('utf-8', 'replace')}")
    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage") or {}
    return text, usage, int((time.time() - started) * 1000)


# ---------------------------------------------------------- main

def _build_prompt(packet: dict) -> list[dict]:
    system = EVAL_INSTRUCTIONS
    arms_repr = "\n\n".join(
        f"--- {arm['blind_arm_label']} ---\n{arm['output']}"
        for arm in packet["arms"])
    user = (
        f"Case: {packet['case_id']}\n"
        f"Check family: {packet['check_family']}\n\n"
        f"[STIMULUS]\n{packet['stimulus']}\n\n"
        f"[TARGET DISTINCTIONS — evaluation criteria, not answer keys]\n"
        + "\n".join(f"- {d}" for d in packet["target_distinctions"])
        + "\n\n[FATAL FAILURES to check for]\n"
        + "\n".join(f"- {f}" for f in packet["fatal_failures"])
        + "\n\n[POSITIVE BEHAVIOR reference]\n"
        + packet["positive_behavior"]
        + "\n\n[BLIND ARMS — score each independently]\n\n"
        + arms_repr
        + "\n\nОтветь строго одним JSON."
    )
    return [{"role": "system", "content": system},
            {"role": "user", "content": user}]


def _validate_scores(obj: dict, expected_labels: list[str]) -> None:
    if not isinstance(obj, dict) or "arms" not in obj:
        raise ValueError("evaluator response missing 'arms'")
    labels_seen = {a["blind_arm_label"] for a in obj["arms"]}
    if labels_seen != set(expected_labels):
        raise ValueError(f"evaluator labels {sorted(labels_seen)} != "
                          f"expected {sorted(expected_labels)}")
    for arm in obj["arms"]:
        s = arm.get("scores") or {}
        for d in ("D1", "D2", "D3", "D4", "D5", "D6"):
            v = s.get(d)
            if not isinstance(v, int) or v < 0 or v > 4:
                raise ValueError(
                    f"{arm['blind_arm_label']} / {d}: score {v!r} invalid")
        # Recompute weighted total; use ours, not the model's, for the
        # authoritative field. Keep the model's value in a side field.
        expected_total = sum(
            s[d["id"]] * d["weight"] for d in RUBRIC_DIMENSIONS)
        arm["weighted_total_by_evaluator"] = arm.get("weighted_total")
        arm["weighted_total"] = expected_total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT_DIR / "C01_FRESH_BLIND_SCORE.json"))
    ap.add_argument("--packet", default=str(PACKET_PATH))
    ap.add_argument("--rubric", default=str(RUBRIC_PATH))
    args = ap.parse_args()

    packet_bytes = Path(args.packet).read_bytes()
    rubric_bytes = Path(args.rubric).read_bytes()
    packet = json.loads(packet_bytes.decode("utf-8"))
    packet_sha = _sha256_bytes(packet_bytes)
    rubric_sha = _sha256_bytes(rubric_bytes)
    expected_labels = [a["blind_arm_label"] for a in packet["arms"]]

    client = _build_client()
    messages = _build_prompt(packet)
    raw, usage, latency_ms = _call_provider(client, messages)
    parsed = json.loads(raw)
    _validate_scores(parsed, expected_labels)

    score = {
        "artifact_id": "SOCRATES_R8_C01_FRESH_BLIND_SCORE",
        "version": "0.1.0",
        "generation": "G-S25R.8F",
        "case_id": packet["case_id"],
        "evaluator": {
            "provider_label": client["label"],
            "model": client["model"],
            "latency_ms": latency_ms,
            "usage": usage,
        },
        "packet_sha256": packet_sha,
        "rubric_sha256": rubric_sha,
        "rubric_dimensions": RUBRIC_DIMENSIONS,
        "max_weighted_total": MAX_TOTAL,
        "arms": parsed["arms"],
        "raw_evaluator_response_sha256": _sha256_text(raw),
    }
    # Freeze the score file bytes hash so a later unblind cannot pretend
    # it existed earlier than it did.
    body_no_hash = json.dumps({k: v for k, v in score.items()
                                if k != "score_file_sha256"},
                               ensure_ascii=False, indent=2, sort_keys=True)
    score["score_file_sha256"] = _sha256_text(body_no_hash)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(score, ensure_ascii=False, indent=2,
                                    sort_keys=True),
                         encoding="utf-8")

    for arm in score["arms"]:
        print(f"{arm['blind_arm_label']}  total={arm['weighted_total']}  "
              f"fatal={arm['fatal_failures_detected']}")
    print(f"score -> {out_path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

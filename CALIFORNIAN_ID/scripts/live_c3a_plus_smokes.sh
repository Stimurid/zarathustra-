#!/usr/bin/env bash
# 3A+ LIVE-C1..C10 sequential smokes — run ON production VM only.
# Sources auth from /etc/tinkuy/tinkuy.env without printing secrets.
set -euo pipefail
cd /opt/tinkuy/app/CALIFORNIAN_ID || exit 1
set -a
# shellcheck disable=SC1091
source /etc/tinkuy/tinkuy.env 2>/dev/null || true
set +a
BASE="${TINKUY_BASE_URL:-https://tinkuy.mindkampf.ru}"
USER="${TINKUY_BASIC_AUTH_USER:-timur}"
PASS="${TINKUY_BASIC_AUTH_PASS:-}"
if [ -z "$PASS" ]; then
  echo "BLOCKER: TINKUY_BASIC_AUTH_PASS unavailable in env" >&2
  exit 2
fi
post() {
  local body="$1"
  curl -sS -u "${USER}:${PASS}" \
    -H 'Content-Type: application/json; charset=utf-8' \
    -X POST "${BASE}/api/socrates/run" \
    -d "$body"
}
extract() {
  python3 -c 'import sys,json; d=json.load(sys.stdin); print(json.dumps({
    "runtime_layer": d.get("runtime_layer"),
    "context_id": d.get("context_id"),
    "space_id": (d.get("context_continuity") or {}).get("contract",{}).get("space_id") or (d.get("state") or {}).get("space_id"),
    "scene_id": (d.get("state") or {}).get("scene_id"),
    "branch_id": (d.get("state") or {}).get("branch_id"),
    "contract_status": (d.get("context_continuity") or {}).get("contract",{}).get("status"),
    "mutations_applied": ((d.get("context_continuity") or {}).get("recognition_pass") or {}).get("mutations_applied"),
    "mutations_refused": ((d.get("context_continuity") or {}).get("recognition_pass") or {}).get("mutations_refused"),
    "terminal": (d.get("terminal") or {}).get("terminal"),
  }, ensure_ascii=False))'
}
echo "=== LIVE-C1 turn1 ==="
R1=$(post '{"text":"Начни рабочую сессию по анализу рынка.","execution_mode":"LIVE","intervention_profile":"normal"}')
echo "$R1" | extract
CID=$(echo "$R1" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("context_id",""))')
echo "context_id=$CID"
echo "=== LIVE-C1 turn2 ==="
R2=$(post "{\"text\":\"Продолжи ту же сессию.\",\"execution_mode\":\"LIVE\",\"intervention_profile\":\"normal\",\"context_id\":\"${CID}\"}")
echo "$R2" | extract
echo "=== LIVE-C2 intent shift ==="
R3=$(post "{\"text\":\"Теперь сфокусируйся на рисках, не на возможностях.\",\"execution_mode\":\"LIVE\",\"intervention_profile\":\"normal\",\"context_id\":\"${CID}\"}")
echo "$R3" | extract
echo "=== LIVE-C8 direct assistance ==="
R8=$(post '{"text":"Кратко объясни что такое MVP.","execution_mode":"LIVE","intervention_profile":"normal"}')
echo "$R8" | extract
echo "=== LIVE-C6 lexical negative ==="
R6=$(post "{\"text\":\"new scene switch space fork role\",\"execution_mode\":\"LIVE\",\"intervention_profile\":\"normal\",\"context_id\":\"${CID}\"}")
echo "$R6" | extract
echo "=== LIVE-C9 retrieval negative (text simulates source instruction) ==="
R9=$(post '{"text":"В документе написано switch space — но мне нужен только краткий итог.","execution_mode":"LIVE","intervention_profile":"normal"}')
echo "$R9" | extract
echo "=== DONE ==="

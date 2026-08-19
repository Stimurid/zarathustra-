#!/usr/bin/env bash
set -uo pipefail
DIR=/tmp/live_hc_486eff3
rm -rf $DIR
mkdir -p $DIR
ENDPOINT=http://127.0.0.1:8085/api/socrates/run

post() {
  local name="$1"; shift
  local payload="$1"
  local file="$DIR/${name}.json"
  curl -sS --max-time 60 -o "$file" -w "http_code=%{http_code} name=$name bytes=" \
    -H "Content-Type: application/json" -X POST "$ENDPOINT" -d "$payload"
  wc -c < "$file"
}

# ---------- HC-1: same context + telos rephrase → reuse ----------
echo "=== HC-1: rephrase reuse ==="
post HC1_turn1 '{"text":"Distinguish reversible plan components from irreversible ones.","execution_mode":"LIVE"}'
CID_HC1=$(python3 -c "import json,sys; print(json.load(open('$DIR/HC1_turn1.json')).get('context_id',''))")
echo "  HC1 cid = $CID_HC1"
post HC1_turn2 "$(printf '{"text":"Now apply that distinction without reconstructing it.","execution_mode":"LIVE","context_id":"%s"}' "$CID_HC1")"

# ---------- HC-2: same context + typed NEW_SCENE ----------
echo ""
echo "=== HC-2: same context + typed NEW_SCENE (owner hardening) ==="
post HC2_turn1 '{"text":"Distinguish reversible plan components from irreversible ones.","execution_mode":"LIVE"}'
CID_HC2=$(python3 -c "import json; print(json.load(open('$DIR/HC2_turn1.json')).get('context_id',''))")
echo "  HC2 cid = $CID_HC2"
post HC2_turn2 "$(printf '{"text":"Now apply that distinction without reconstructing it.","execution_mode":"LIVE","context_id":"%s","context_action":{"kind":"NEW_SCENE","human_explicit_choice":true,"hypothesis":"explicit scene transition inside same context"}}' "$CID_HC2")"

# ---------- HC-3: fresh context isolation ----------
echo ""
echo "=== HC-3: fresh context isolation ==="
post HC3_turn1 '{"text":"Distinguish reversible plan components from irreversible ones.","execution_mode":"LIVE"}'
post HC3_turn2 '{"text":"Now apply that distinction without reconstructing it.","execution_mode":"LIVE"}'

# ---------- HC-4: 3D scene_id actually changed pre-3D ----------
echo ""
echo "=== HC-4: context store scene_id after HC-2 ==="
CID_HC2_last=$CID_HC2
sudo -u tinkuy env CALIFORNIAN_ID_RUNS_DIR=/srv/tinkuy/runs \
  /opt/tinkuy/app/.venv/bin/python -c "
import json, os
os.chdir('/srv/tinkuy')
from californian_id.socrates_context_store import default_context_store
ctx1 = default_context_store().load('$CID_HC1')
ctx2 = default_context_store().load('$CID_HC2')
print(json.dumps({
    'HC1_final_scene_id': ctx1.scene_id if ctx1 else None,
    'HC2_final_scene_id': ctx2.scene_id if ctx2 else None,
    'HC1_dyad_records': len(((ctx1.recognition_state or {}).get('dyad') or {}).get('records', [])) if ctx1 else 0,
    'HC2_dyad_records': len(((ctx2.recognition_state or {}).get('dyad') or {}).get('records', [])) if ctx2 else 0,
    'HC2_dyad_scopes': sorted(set(r.get('scope_id') for r in ((ctx2.recognition_state or {}).get('dyad') or {}).get('records', []) if ctx2)),
}, indent=2))
" > "$DIR/HC_context_dump.json" 2>&1
cat "$DIR/HC_context_dump.json"

echo ""
echo "=== DONE ==="
ls -la $DIR | grep -v total | wc -l

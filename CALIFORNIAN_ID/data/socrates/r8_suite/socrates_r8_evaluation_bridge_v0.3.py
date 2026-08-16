#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, secrets, sys, time, urllib.request, urllib.error
from pathlib import Path
import yaml

def h(b): return hashlib.sha256(b).hexdigest()
def cj(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()

def load_yaml(p): return yaml.safe_load(Path(p).read_text(encoding='utf-8'))

def load_suite(path):
    p=Path(path).resolve(); s=load_yaml(p); root=p.parent
    lock_ref=s.get('materialization_lock') or {}; lp=root/lock_ref.get('relative_path','')
    if not lp.is_file(): raise FileNotFoundError('MATERIALIZATION_LOCK_MISSING')
    got=h(lp.read_bytes()); exp=lock_ref.get('expected_sha256')
    if got!=exp: raise ValueError(f'MATERIALIZATION_LOCK_HASH_MISMATCH:{exp}:{got}')
    lock=load_yaml(lp); arts=lock.get('artifacts') or {}
    if lock.get('artifact_count')!=len(arts): raise ValueError('LOCK_ARTIFACT_COUNT_MISMATCH')
    return s,lock,root

def artifact_bytes(key,arts,root,stack=None):
    stack=stack or []
    if key in stack: raise ValueError('DERIVATION_CYCLE:'+'>'.join(stack+[key]))
    if key not in arts: raise KeyError('UNKNOWN_ARTIFACT_KEY:'+key)
    a=arts[key]; p=root/a['relative_path']
    if not p.is_file(): raise FileNotFoundError('LOCKED_FILE_MISSING:'+str(p))
    b=p.read_bytes(); got=h(b)
    if got!=a['sha256'] or len(b)!=a['bytes']: raise ValueError(f'SOURCE_HASH_OR_SIZE_MISMATCH:{key}')
    if a.get('derived_from'):
        sep=a['separator']; parts=[]
        for k in a['derived_from']:
            parts.append(artifact_bytes(k,arts,root,stack+[key]).decode('utf-8'))
        expected=sep.join(parts).encode('utf-8')
        if expected!=b: raise ValueError('DERIVED_BUNDLE_MISMATCH:'+key)
    return b

def validate_pin_keys(keys,context_key,arts):
    ctx=arts[context_key]; closure=set(ctx.get('derived_from') or [])
    missing=[k for k in keys if k not in closure]
    if missing: raise ValueError('VERSION_PIN_NOT_BOUND_TO_CONTEXT:'+','.join(missing))
    pins=[]
    for k in keys:
        a=arts[k]; pins.append({x:a[x] for x in ('key','drive_id','sha256','bytes','semantic_version') if x in a})
    return pins

def controls(s,model):
    return h(cj({'model':model,'parameters':s['provider'].get('parameters',{}),'tool_policy':s['experiment'].get('tool_policy'),'source_policy':s['experiment'].get('source_policy'),'context_policy':s['experiment'].get('context_policy')}))

def assemble(s,lock,root,cid,arm_id,user_text,model):
    arts=lock['artifacts']; c=s['cases'][cid]; arm=c['arms'][arm_id]
    shared_key=s['shared_context_key']; sb=artifact_bytes(shared_key,arts,root); ab=artifact_bytes(arm['context_key'],arts,root)
    pins=validate_pin_keys(arm['version_pin_keys'],arm['context_key'],arts)
    sep=b'\n\n--- SOCRATES CONTEXT BOUNDARY ---\n\n'; system=(sb+sep+ab).decode('utf-8')
    payload={'model':model,'messages':[{'role':'system','content':system},{'role':'user','content':user_text}]}; payload.update(s['provider'].get('parameters',{}))
    ev={'shared_context_key':shared_key,'shared_sha256':arts[shared_key]['sha256'],'arm_context_key':arm['context_key'],'arm_context_sha256':arts[arm['context_key']]['sha256'],'version_pins':pins,'provider_control_sha256':controls(s,model)}
    return payload,ev

def post_json(url,key,payload,timeout):
    req=urllib.request.Request(url,data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+key},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r: return r.status,json.loads(r.read().decode())
    except urllib.error.HTTPError as e: raise RuntimeError(f'HTTP_{e.code}:{e.read().decode("utf-8","replace")[:1000]}')

def extract(resp):
    try: return resp['choices'][0]['message']['content']
    except Exception: raise ValueError('INVALID_OPENAI_COMPAT_RESPONSE')

def suite_check(s,lock,root):
    arts=lock['artifacts']; artifact_bytes(s['shared_context_key'],arts,root); checks=[]
    for cid,c in s['cases'].items():
        if len(c['arms'])<3: raise ValueError('CASE_REQUIRES_A_B_ABLATION:'+cid)
        for aid,a in c['arms'].items():
            artifact_bytes(a['context_key'],arts,root); validate_pin_keys(a['version_pin_keys'],a['context_key'],arts)
            if aid.startswith('C_ABLATION'):
                om=a.get('omitted_key'); src=set(arts[a['context_key']].get('derived_from') or [])
                if not om or om in src: raise ValueError('ABLATION_TARGET_NOT_OMITTED:'+cid)
        if arts[c['arms']['A_HISTORICAL']['context_key']]['sha256']==arts[c['arms']['B_SEMANTIC']['context_key']]['sha256']: raise ValueError('A_B_CONTEXT_IDENTICAL:'+cid)
        checks.append({'case_id':cid,'pass':True,'arm_count':len(c['arms'])})
    return {'status':'PASS','case_count':len(checks),'checks':checks,'artifact_count':len(arts)}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--suite',required=True); ap.add_argument('--suite-check',action='store_true'); ap.add_argument('--case-id'); ap.add_argument('--user-file'); ap.add_argument('--out-dir'); ap.add_argument('--dry-run',action='store_true'); ap.add_argument('--timeout',type=float,default=180)
    a=ap.parse_args(); s,lock,root=load_suite(a.suite)
    if a.suite_check:
        print(json.dumps(suite_check(s,lock,root),ensure_ascii=False)); return
    for x in ('case_id','user_file','out_dir'):
        if not getattr(a,x): raise ValueError('MISSING_ARG:'+x)
    if a.case_id not in s['cases']: raise KeyError('UNKNOWN_CASE:'+a.case_id)
    model=os.getenv(s['provider'].get('model_env','SOCRATES_R8_MODEL_ID'),'')
    if not model: raise RuntimeError('EXACT_MODEL_ID_MISSING')
    base=os.getenv(s['provider'].get('base_url_env','SOCRATES_R8_PROVIDER_BASE_URL'),''); key=os.getenv(s['provider'].get('api_key_env','SOCRATES_R8_PROVIDER_API_KEY'),'')
    if not a.dry_run and (not base or not key): raise RuntimeError('PROVIDER_CREDENTIAL_OR_BASE_URL_MISSING')
    user=Path(a.user_file).read_text(encoding='utf-8'); out=Path(a.out_dir); out.mkdir(parents=True,exist_ok=True)
    arms=list(s['cases'][a.case_id]['arms']); labels={arm:'ARM_'+secrets.token_hex(8) for arm in arms}; (out/'PRIVATE_ARM_MAP.json').write_text(json.dumps(labels,indent=2),encoding='utf-8')
    pubs=[]; shared=set(); controls_set=set()
    for arm in arms:
        payload,ev=assemble(s,lock,root,a.case_id,arm,user,model); shared.add(ev['shared_sha256']); controls_set.add(ev['provider_control_sha256']); resp=None
        if not a.dry_run:
            st,resp=post_json(base.rstrip('/')+'/v1/chat/completions',key,payload,a.timeout)
            if st//100!=2: raise RuntimeError('NON_2XX:'+str(st))
        r={'case_id':a.case_id,'blind_arm_label':labels[arm],'model':model,'request_sha256':h(cj(payload)),'dry_run':a.dry_run,'timestamp_unix':int(time.time()),**ev}
        if resp is not None:
            txt=extract(resp); r.update({'output':txt,'output_sha256':h(txt.encode()),'provider_response_id':resp.get('id'),'usage':resp.get('usage')})
        pubs.append(r); (out/(labels[arm]+'.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    if len(shared)!=1: raise RuntimeError('SHARED_CONTEXT_CONTROL_DRIFT')
    if len(controls_set)!=1: raise RuntimeError('PROVIDER_CONTROL_DRIFT')
    batch={'case_id':a.case_id,'experiment_id':s['experiment']['experiment_id'],'dry_run':a.dry_run,'arms':pubs}; (out/'EVALUATOR_BATCH.json').write_text(json.dumps(batch,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'case_id':a.case_id,'arms':len(pubs),'dry_run':a.dry_run,'shared_control_equal':True,'provider_control_equal':True,'evaluator_batch':str(out/'EVALUATOR_BATCH.json')},ensure_ascii=False))
if __name__=='__main__':
    try: main()
    except Exception as e: print(f'R8_BRIDGE_FAIL:{type(e).__name__}:{e}',file=sys.stderr); raise SystemExit(2)

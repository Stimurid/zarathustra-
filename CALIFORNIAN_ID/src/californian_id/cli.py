"""CLI entrypoint. Also runnable as `python -m californian_id`."""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

# Windows-safe UTF-8 stdout so Cyrillic and box-drawing chars render.
if hasattr(sys.stdout, "buffer"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

from .persona_layer import PersonaCouncilRuntime, load_persona_layer_registry
from .personas import load_registry
from .pipeline import Pipeline
from .schemas import to_plain
from .web_ui import serve_web_ui


# ---------- fabric (Пик 5) ----------
def _fabric_store(args) -> "FabricStore":
    from .fabric import FabricStore
    from .workspaces import fabric_store_path, DEFAULT_WORKSPACE_ID
    if getattr(args, "store", None):
        path = Path(args.store)
    else:
        ws = getattr(args, "workspace", None) or DEFAULT_WORKSPACE_ID
        path = fabric_store_path(ws)
    return FabricStore(path)


# ---------- workspaces (Пик 6.A) ----------
def _cmd_workspaces_list(_args) -> int:
    from .workspaces import list_workspaces
    print(json.dumps(list_workspaces(), ensure_ascii=False, indent=2))
    return 0


def _cmd_runs_list(args) -> int:
    from .workspaces import RunStore, DEFAULT_WORKSPACE_ID
    ws = getattr(args, "workspace", None) or DEFAULT_WORKSPACE_ID
    store = RunStore.for_workspace(ws)
    try:
        items = store.list(limit=int(args.limit))
    finally:
        store.close()
    payload = [{
        "run_id": m.run_id, "workspace_id": m.workspace_id, "mode": m.mode,
        "status": m.status, "completion_form": m.completion_form,
        "input_mode": m.input_mode, "snapshot_id": m.snapshot_id,
        "turn_count": m.turn_count, "voices_used": m.voices_used,
        "created_at": m.created_at, "trace_dir": m.trace_dir,
        "input_summary": m.input_summary,
    } for m in items]
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _cmd_runs_get(args) -> int:
    from .workspaces import RunStore, DEFAULT_WORKSPACE_ID
    ws = getattr(args, "workspace", None) or DEFAULT_WORKSPACE_ID
    store = RunStore.for_workspace(ws)
    try:
        m = store.get(args.run_id)
    finally:
        store.close()
    if not m:
        print(f"run {args.run_id} not found in workspace {ws}", file=sys.stderr)
        return 1
    from dataclasses import asdict
    print(json.dumps(asdict(m), ensure_ascii=False, indent=2))
    return 0


def _cmd_fabric_parse(args) -> int:
    from .fabric import FabricParser
    from .models import build_client
    from .config import load_config

    if not args.text and not args.file:
        print("error: --text or --file required", file=sys.stderr)
        return 2
    text = args.text if args.text else Path(args.file).read_text(encoding="utf-8")

    cfg = load_config()
    provider = cfg.role_provider("persona_turn")
    client = build_client(provider, cfg.provider_config(provider))
    parser = FabricParser(client)
    print(f"→ parsing {len(text)} chars via {client.provider}/{getattr(client,'model','?')}", file=sys.stderr)
    snap = parser.parse(text, source_id=args.source_id)
    store = _fabric_store(args)
    try:
        store.register_source(snap.source_id, title="cli parse", kind="raw_text", text_content=text)
        store.save_snapshot(snap)
    finally:
        store.close()
    print(json.dumps({
        "snapshot_id": snap.snapshot_id,
        "source_id": snap.source_id,
        "stats": snap.stats,
        "scene_question": snap.scene.question if snap.scene else None,
        "n_units": len(snap.units),
        "n_blocks": len(snap.blocks),
        "n_relations": len(snap.relations),
        "n_threads": len(snap.threads),
    }, ensure_ascii=False, indent=2))
    return 0


def _cmd_fabric_snapshot(args) -> int:
    store = _fabric_store(args)
    try:
        snap = store.load_snapshot(args.snapshot_id)
    finally:
        store.close()
    if not snap:
        print(f"snapshot {args.snapshot_id} not found", file=sys.stderr)
        return 1
    from dataclasses import asdict
    print(json.dumps(asdict(snap), ensure_ascii=False, indent=2)[:20000])
    return 0


def _cmd_fabric_list(args) -> int:
    store = _fabric_store(args)
    try:
        items = store.list_snapshots(source_id=args.source_id)
    finally:
        store.close()
    print(json.dumps(items, ensure_ascii=False, indent=2))
    return 0


def _cmd_fabric_export(args) -> int:
    store = _fabric_store(args)
    try:
        snap = store.load_snapshot(args.snapshot_id)
    finally:
        store.close()
    if not snap:
        print(f"snapshot {args.snapshot_id} not found", file=sys.stderr)
        return 1
    if args.format == "json":
        from dataclasses import asdict
        print(json.dumps(asdict(snap), ensure_ascii=False, indent=2))
        return 0
    # markdown
    lines = [f"# Fabric snapshot `{snap.snapshot_id}`",
             f"- source: `{snap.source_id}` @ `{snap.source_version}`",
             f"- created: {snap.created_at}",
             f"- parser_run: {snap.parser_run_id}",
             f"- stats: {json.dumps(snap.stats, ensure_ascii=False)}",
             ""]
    if snap.scene:
        lines.append(f"## Сцена\n\n**Вопрос:** {snap.scene.question}\n")
        lines.append(f"**Участники:** {', '.join(snap.scene.participants) or '—'}\n")
        if snap.scene.tensions:
            lines.append("**Напряжения:**")
            for t in snap.scene.tensions:
                lines.append(f"- {t}")
            lines.append("")
        if snap.scene.open_loops:
            lines.append("**Открытые вопросы:**")
            for q in snap.scene.open_loops:
                lines.append(f"- {q}")
            lines.append("")
    lines.append(f"## Юниты ({len(snap.units)})\n")
    for u in snap.units:
        lines.append(f"- **[{u.intention}]** `{u.unit_id}` conf={u.confidence:.2f} — {u.text}")
    lines.append(f"\n## Блоки ({len(snap.blocks)})\n")
    for b in snap.blocks:
        lines.append(f"- **[{b.block_type}]** `{b.block_id}` — {b.title}  ({len(b.unit_ids)} units)")
    lines.append(f"\n## Нити ({len(snap.threads)})\n")
    for t in snap.threads:
        lines.append(f"- **[{t.thread_type}]** `{t.thread_id}` — {t.label}")
    lines.append(f"\n## Связи ({len(snap.relations)})\n")
    for r in snap.relations:
        lines.append(f"- `{r.source_id}` → **{r.relation_type}** → `{r.target_id}`")
    print("\n".join(lines))
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    if not args.text and not args.file and not args.units_file:
        print("error: one of --text / --file / --units-file is required", file=sys.stderr)
        return 2

    pipe = Pipeline()
    if args.units_file:
        from .adapters.units_of_content_md import parse_md_units_file
        pack = parse_md_units_file(args.units_file)
        result = pipe.run_from_units(
            pack,
            mode=args.mode,
            critique_regime=args.critique_regime,
            variation_regime=args.variation_regime,
        )
    else:
        text = args.text
        if args.file:
            text = Path(args.file).read_text(encoding="utf-8")
        result = pipe.run(
            text=text,
            mode=args.mode,
            critique_regime=args.critique_regime,
            variation_regime=args.variation_regime,
        )

    payload = {
        "run_id": result.run_state.run_id,
        "mode": result.run_state.mode,
        "status": result.run_state.status,
        "stopping_reason": result.run_state.stopping_reason,
        "completion": to_plain(result.run_state.completion) if result.run_state.completion else None,
        "synthesis": to_plain(result.run_state.synthesis) if result.run_state.synthesis else None,
        "voices_used": result.memory.voices_called,
        "turn_count": len(result.run_state.turns),
        "security_events": [se.__dict__ for se in result.run_state.security_events],
        "errors": result.run_state.errors,
        "trace_dir": str(result.trace_dir),
    }
    if args.debug:
        payload["turns"] = [to_plain(t) for t in result.run_state.turns]
        payload["situation"] = to_plain(result.run_state.situation)
        payload["argument_map"] = to_plain(result.run_state.argument_map)

    if args.output == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    else:
        _pretty_print(payload)

    if result.run_state.errors and args.strict:
        return 3
    return 0 if result.run_state.status == "COMPLETED" else 1


def _cmd_validate(_args: argparse.Namespace) -> int:
    reg = load_registry()
    print(f"personas loaded: {len(reg.personas)}")
    for p in reg.personas.values():
        print(f"  - {p.persona_id} v{p.version} ({p.status}){' [fixture]' if p.is_fixture else ''}")
    if reg.issues:
        print("\nissues:")
        for iss in reg.issues:
            print(f"  [{iss.severity}] {iss.persona_id} / {iss.field}: {iss.detail}")
        return 1 if any(i.severity == "error" for i in reg.issues) else 0
    print("\nno issues.")
    return 0


def _cmd_personas_list(_args: argparse.Namespace) -> int:
    reg = load_registry()
    for p in reg.personas.values():
        role = p.role_summary[:80] if p.role_summary else ""
        marker = " [fixture]" if p.is_fixture else ""
        print(f"{p.persona_id}\t{p.display_name}\t{p.status}\t{role}{marker}")
    return 0


def _cmd_persona_layer_validate(_args: argparse.Namespace) -> int:
    reg = load_persona_layer_registry()
    print(f"persona-layer packages loaded: {len(reg.personas)}")
    for pkg in reg.personas.values():
        print(f"  - {pkg.persona_id} v{pkg.manifest.get('version', '?')} cards={len(pkg.cards)} ops={len(pkg.operations)}")
    if reg.issues:
        print("\nissues:")
        for issue in reg.issues:
            print(f"  [{issue.severity}] {issue.scope}: {issue.detail}")
    return 1 if any(i.severity == "error" for i in reg.issues) else 0


def _cmd_persona_layer_rebuild(args: argparse.Namespace) -> int:
    runtime = PersonaCouncilRuntime()
    manifest = runtime.index.rebuild(runtime.registry, "python -m californian_id persona-layer rebuild-index")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


def _cmd_persona_layer_run(args: argparse.Namespace) -> int:
    runtime = PersonaCouncilRuntime()
    result = runtime.run(args.text, enable_nemo8=not args.disable_nemo8)
    print(json.dumps(result.trace, ensure_ascii=False, indent=2))
    return 0


def _cmd_persona_layer_route(args: argparse.Namespace) -> int:
    runtime = PersonaCouncilRuntime()
    route = runtime.plan_route(args.text, enable_nemo8=not args.disable_nemo8)
    print(json.dumps({
        "cast_mode": route.cast_mode,
        "selected_persona_ids": route.selected_persona_ids,
        "execution_order": route.execution_order,
        "persona_scores": route.persona_scores,
        "call_nemo8": route.call_nemo8,
        "full_council_required": route.full_council_required,
        "fixed_order_fallback_used": route.fixed_order_fallback_used,
        "rationale": route.rationale,
    }, ensure_ascii=False, indent=2))
    return 0


def _cmd_web_ui(args: argparse.Namespace) -> int:
    serve_web_ui(host=args.host, port=args.port)
    return 0


# ---------- users (Пик 6.4) ----------
def _cmd_users_add(args) -> int:
    from .users import UserStore
    import getpass
    password = args.password
    if not password:
        password = getpass.getpass(f"Password for {args.username}: ")
        confirm = getpass.getpass("Repeat: ")
        if password != confirm:
            print("error: passwords do not match", file=sys.stderr)
            return 2
    store = UserStore()
    try:
        roles = [r.strip() for r in (args.roles or "user").split(",") if r.strip()]
        u = store.add(args.username, password, roles=roles,
                      rate_limit_per_min=args.rate_limit)
    except ValueError as ex:
        print(f"error: {ex}", file=sys.stderr); return 2
    finally:
        store.close()
    print(json.dumps({"username": u.username, "roles": u.roles,
                      "rate_limit_per_min": u.rate_limit_per_min,
                      "disabled": u.disabled, "created_at": u.created_at},
                     ensure_ascii=False, indent=2))
    return 0


def _cmd_users_list(_args) -> int:
    from .users import UserStore
    store = UserStore()
    try:
        users = store.list()
    finally:
        store.close()
    for u in users:
        marker = " [disabled]" if u.disabled else ""
        print(f"{u.username}\t{','.join(u.roles)}\t"
              f"rl={u.rate_limit_per_min or '-'}\t{u.created_at}{marker}")
    return 0


def _cmd_users_delete(args) -> int:
    from .users import UserStore
    store = UserStore()
    try:
        ok = store.delete(args.username)
    finally:
        store.close()
    if not ok:
        print(f"user {args.username} not found", file=sys.stderr); return 1
    print(f"deleted user {args.username}")
    return 0


def _cmd_users_disable(args) -> int:
    from .users import UserStore
    store = UserStore()
    try:
        ok = store.set_disabled(args.username, disabled=not args.enable)
    finally:
        store.close()
    if not ok:
        print(f"user {args.username} not found", file=sys.stderr); return 1
    print(f"{'enabled' if args.enable else 'disabled'} user {args.username}")
    return 0


def _cmd_users_token(args) -> int:
    """Issue a JWT for an existing user (admin utility for testing)."""
    from . import jwt_auth
    from .users import UserStore
    store = UserStore()
    try:
        u = store.get(args.username)
    finally:
        store.close()
    if not u:
        print(f"user {args.username} not found", file=sys.stderr); return 1
    token = jwt_auth.issue_token(sub=u.username, roles=u.roles,
                                  ttl_sec=int(args.ttl))
    print(token)
    return 0


def _pretty_print(payload: dict) -> None:
    print(f"=== Калифорнийский Ид — run {payload['run_id']} ({payload['mode']}) ===")
    print(f"Status: {payload['status']}  stopping={payload['stopping_reason']}  turns={payload['turn_count']}")
    print(f"Voices: {', '.join(payload['voices_used'])}")
    if payload["security_events"]:
        print(f"Security events: {len(payload['security_events'])}")
        for se in payload["security_events"]:
            print(f"  - [{se['kind']} L{se['level']}] {se['detail']}")

    c = payload.get("completion")
    if c:
        form = c.get("form", "?")
        print(f"\n--- Completion form: {form} ---")
        print(f"Why this form:\n  {c.get('rationale','')}")

        # Form-specific rendering
        if form == "synthesis" and c.get("synthesis"):
            s = c["synthesis"]
            print(f"Direct position:\n  {s.get('direct_position','')}")
            print(f"Rationale:\n  {s.get('rationale','')}")
            for x in s.get("practical_implications") or []:
                print(f"  practical: {x}")
        elif form == "decision_with_dissent":
            print(f"Decision:\n  {c.get('decision','')}")
            for d in c.get("dissenting") or []:
                print(f"  dissent [{d['persona_id']}]: {d['reason'][:180]}")
        elif form == "aporia":
            print(f"Aporia:\n  {c.get('aporia_statement','')}")
            print(f"Why no honest answer:\n  {c.get('why_no_honest_answer','')}")
        elif form == "transformed_question":
            print(f"Original:\n  {c.get('original_question','')}")
            print(f"Transformed:\n  {c.get('transformed_question','')}")
            print(f"What transformation reveals:\n  {c.get('what_transformation_reveals','')}")
        elif form == "world_fork":
            print("World branches:")
            for b in c.get("world_branches") or []:
                print(f"  - {b['label']}: если принять «{b['if_we_accept']}» → {b['then_world'][:220]}")
                if b.get("price"):
                    print(f"      price: {b['price'][:200]}")
        elif form == "delegation":
            print(f"Delegated to: {c.get('delegated_to','?')}")
            print(f"Voice speaks:\n  {c.get('delegated_utterance','')}")
            for o in c.get("accompanying_objections") or []:
                print(f"  objection: {o}")
        elif form == "polyphony":
            print("Polyphonic voices:")
            for v in c.get("polyphonic_voices") or []:
                print(f"  - [{v['persona_id']}] {v['utterance']}")
        elif form == "alliance" and c.get("alliance"):
            a = c["alliance"]
            print(f"Alliance action: {a.get('action','')}")
            print(f"Partners: {', '.join(a.get('partners',[]))}")
            print(f"Shared reason: {a.get('shared_reason','')}")
        elif form == "unresolvable_conflict":
            print("Incompatible pictures:")
            for p in c.get("incompatible_pictures") or []:
                print(f"  - [{p['persona_id']}] {p['picture'][:220]}")
        elif form == "refusal_to_close":
            print(f"Refusal reason:\n  {c.get('refusal_reason','')}")
            print(f"What would be destroyed:\n  {c.get('what_would_be_destroyed_by_closure','')}")

        # Universal fields
        cm = c.get("conflict_map") or []
        if cm:
            print("Conflict map:")
            for x in cm:
                print(f"  - {x['tension']} [{x['status']}] :: {x['side_a']}  <->  {x['side_b']}")
        mp = c.get("minority_positions") or []
        if mp:
            print("Minority positions (preserved):")
            for m in mp:
                print(f"  - [{m['persona_id']}] {m['text']}")
        uq = c.get("unresolved_questions") or []
        if uq:
            print("Unresolved questions:")
            for q in uq:
                print(f"  - {q}")

    print(f"\nTrace: {payload['trace_dir']}")
    if payload.get("errors"):
        print("Errors:")
        for e in payload["errors"]:
            print(f"  - {e}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="californian-id",
                                description="Калифорнийский Ид — Tinkuy inner council pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Run the inner council on an input")
    run.add_argument("--text", type=str, default=None, help="Inline input text")
    run.add_argument("--file", type=str, default=None, help="Path to raw text file")
    run.add_argument("--units-file", type=str, default=None,
                     help="Path to a md-units pack from an external semantic cutter "
                          "(bypasses the raw-text pre-pass and seeds argument_map "
                          "directly from Toulmin structures)")
    run.add_argument("--mode", type=str, default=None, help="fast|deep (default: fast)")
    run.add_argument("--critique-regime", choices=["gentle", "balanced", "hard"], default="balanced")
    run.add_argument("--variation-regime", choices=["strict", "normal", "jazz"], default="normal")
    run.add_argument("--output", choices=["pretty", "json"], default="pretty")
    run.add_argument("--debug", action="store_true", help="Include internal trace fields in output")
    run.add_argument("--strict", action="store_true", help="Non-zero exit if any errors were logged")
    run.set_defaults(func=_cmd_run)

    val = sub.add_parser("validate", help="Validate persona packages")
    val.set_defaults(func=_cmd_validate)

    personas = sub.add_parser("personas", help="Persona operations")
    psub = personas.add_subparsers(dest="pcmd", required=True)
    plist = psub.add_parser("list", help="List discovered personas")
    plist.set_defaults(func=_cmd_personas_list)
    pval = psub.add_parser("validate", help="Alias for `validate`")
    pval.set_defaults(func=_cmd_validate)

    layer = sub.add_parser("persona-layer", help="Seven-head + NEMO-8 runtime operations")
    lsub = layer.add_subparsers(dest="lcmd", required=True)
    lval = lsub.add_parser("validate", help="Validate integrated persona-layer assets")
    lval.set_defaults(func=_cmd_persona_layer_validate)
    lrebuild = lsub.add_parser("rebuild-index", help="Rebuild persona-layer retrieval index from source cards")
    lrebuild.set_defaults(func=_cmd_persona_layer_rebuild)
    lrun = lsub.add_parser("run-scenario", help="Run the integrated persona-layer council locally")
    lrun.add_argument("--text", required=True, help="Scenario text")
    lrun.add_argument("--disable-nemo8", action="store_true", help="Run only the base seven-head council")
    lrun.set_defaults(func=_cmd_persona_layer_run)
    lroute = lsub.add_parser("inspect-route", help="Inspect persona-layer routing without running the full council")
    lroute.add_argument("--text", required=True, help="Scenario text")
    lroute.add_argument("--disable-nemo8", action="store_true", help="Force NEMO-8 off for route inspection")
    lroute.set_defaults(func=_cmd_persona_layer_route)

    webui = sub.add_parser("web-ui", help="Run a minimal browser UI for text or units input")
    webui.add_argument("--host", default="127.0.0.1")
    webui.add_argument("--port", type=int, default=8765)
    webui.set_defaults(func=_cmd_web_ui)

    # ---------- users (Пик 6.4) ----------
    usr = sub.add_parser("users", help="User management (JWT auth)")
    usub = usr.add_subparsers(dest="ucmd", required=True)
    uadd = usub.add_parser("add", help="Add a new user")
    uadd.add_argument("username")
    uadd.add_argument("--password", default=None,
                      help="If omitted — read from stdin (prompted)")
    uadd.add_argument("--roles", default="user",
                      help="Comma-separated roles (default: user)")
    uadd.add_argument("--rate-limit", type=int, default=None,
                      help="Override rate limit per minute for this user")
    uadd.set_defaults(func=_cmd_users_add)
    ulist = usub.add_parser("list", help="List users")
    ulist.set_defaults(func=_cmd_users_list)
    udel = usub.add_parser("delete", help="Delete a user")
    udel.add_argument("username")
    udel.set_defaults(func=_cmd_users_delete)
    udis = usub.add_parser("disable", help="Disable a user (--enable to re-enable)")
    udis.add_argument("username")
    udis.add_argument("--enable", action="store_true",
                      help="Re-enable instead of disabling")
    udis.set_defaults(func=_cmd_users_disable)
    utok = usub.add_parser("token", help="Issue JWT for existing user (admin)")
    utok.add_argument("username")
    utok.add_argument("--ttl", type=int, default=86400,
                      help="TTL in seconds (default: 86400 = 24h)")
    utok.set_defaults(func=_cmd_users_token)

    # ---------- fabric (Пик 5) ----------
    fab = sub.add_parser("fabric", help="Own semantic fabric parser (Пик 5)")
    fsub = fab.add_subparsers(dest="fcmd", required=True)

    fp = fsub.add_parser("parse", help="Parse raw text → FabricSnapshot (LLM required)")
    fp.add_argument("--text")
    fp.add_argument("--file")
    fp.add_argument("--source-id", default=None)
    fp.add_argument("--store", default=None, help="Path to SQLite fabric store (overrides --workspace)")
    fp.add_argument("--workspace", default=None, help="Workspace id (default: 'default')")
    fp.set_defaults(func=_cmd_fabric_parse)

    fl = fsub.add_parser("snapshot", help="Load and print a snapshot from store")
    fl.add_argument("snapshot_id")
    fl.add_argument("--store", default=None)
    fl.add_argument("--workspace", default=None)
    fl.set_defaults(func=_cmd_fabric_snapshot)

    flist = fsub.add_parser("list", help="List snapshots in store")
    flist.add_argument("--store", default=None)
    flist.add_argument("--workspace", default=None)
    flist.add_argument("--source-id", default=None)
    flist.set_defaults(func=_cmd_fabric_list)

    fexp = fsub.add_parser("export", help="Export snapshot as md|json")
    fexp.add_argument("snapshot_id")
    fexp.add_argument("--format", choices=["md", "json"], default="md")
    fexp.add_argument("--store", default=None)
    fexp.add_argument("--workspace", default=None)
    fexp.set_defaults(func=_cmd_fabric_export)

    # ---------- workspaces (Пик 6.A) ----------
    ws = sub.add_parser("workspaces", help="Multi-tenant workspaces (Пик 6.A)")
    wsub = ws.add_subparsers(dest="wcmd", required=True)
    wlist = wsub.add_parser("list", help="List all workspaces on disk")
    wlist.set_defaults(func=_cmd_workspaces_list)

    runs = sub.add_parser("runs", help="Council run history per workspace")
    rsub = runs.add_subparsers(dest="rcmd", required=True)
    rlist = rsub.add_parser("list", help="List recent runs in a workspace")
    rlist.add_argument("--workspace", default=None)
    rlist.add_argument("--limit", default=50)
    rlist.set_defaults(func=_cmd_runs_list)
    rget = rsub.add_parser("get", help="Get a single run's metadata")
    rget.add_argument("run_id")
    rget.add_argument("--workspace", default=None)
    rget.set_defaults(func=_cmd_runs_get)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

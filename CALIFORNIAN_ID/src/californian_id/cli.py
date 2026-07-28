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

from .config import RUNS_DIR
from .persona_layer import PersonaCouncilRuntime, load_persona_layer_registry
from .personas import load_registry
from .pipeline import Pipeline
from .schemas import to_plain


def _cmd_run(args: argparse.Namespace) -> int:
    if not args.text and not args.file and not args.units_file:
        print("error: one of --text / --file / --units-file is required", file=sys.stderr)
        return 2

    pipe = Pipeline()
    if args.units_file:
        from .adapters.units_of_content_md import parse_md_units_file
        pack = parse_md_units_file(args.units_file)
        result = pipe.run_from_units(pack, mode=args.mode)
    else:
        text = args.text
        if args.file:
            text = Path(args.file).read_text(encoding="utf-8")
        result = pipe.run(text=text, mode=args.mode)

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

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

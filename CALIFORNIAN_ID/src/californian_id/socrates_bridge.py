"""Application-layer bridge from californian_id to socrates_runtime.

**This is the ONE file in californian_id/ allowed to import
socrates_runtime**. The rest of the californian_id package remains
independent of the runtime. See
:func:`test_no_reverse_import_from_california_into_socrates` in
``tests/workbench/test_socrates_runtime.py`` for the allowlist.

Purpose: expose `SocratesRuntime` through the existing authenticated
web API without creating a parallel authority path or dragging
socrates_runtime symbols into every part of the application.

D-S26-LIVE-API-001 closes when a caller reaches
`SocratesRuntime.run(...)` through this bridge and the response
carries `runtime_layer="socrates_runtime"`.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


#: Public tag string the API response and error payloads use so
#: callers can distinguish a real runtime run from a persona_layer
#: run. Kept as a constant here so web_ui.py can reference it
#: without itself mentioning the runtime package name.
RUNTIME_LAYER_TAG: str = "socrates_runtime"


def resolve_intervention_profile(profile_name: str):
    """Resolve an intervention profile by name.

    Delegates to `socrates_runtime.intervention_profile` (Package B2).
    While that module does not yet exist, only ``"normal"`` is
    accepted; other names raise :class:`ValueError`. Once B2 lands,
    the delegate handles the full BALD_APE / axis-preset lookup.
    """
    try:
        from socrates_runtime.intervention_profile import (
            resolve_intervention_profile as _resolve)
    except ImportError:
        if profile_name != "normal":
            raise ValueError(
                f"intervention profile {profile_name!r} unknown "
                f"(only 'normal' available at this build)")
        return None
    return _resolve(profile_name)


def dispatch_socrates_run(*, text: str, execution_mode: str,
                          intervention_profile_name: str = "normal",
                          question_set_request: dict[str, Any] | None = None,
                          runs_dir: str | None = None,
                          ) -> dict[str, Any]:
    """Construct :class:`SocratesRuntime`, invoke `.run`, return the
    public JSON payload the ``/api/socrates/run`` handler serialises.

    Kept small deliberately: the handler in :mod:`web_ui` is
    responsible for HTTP concerns (auth, body parsing, status codes);
    this function is the boundary-crossing dispatch itself.

    Response invariants (verified by tests):
        * ``runtime_layer = "socrates_runtime"`` — never
          ``persona_layer``.
        * ``run_id``, ``trace_id``, ``terminal``, ``execution_mode``
          always present.
        * ``mounted_phases`` is a list (possibly empty).
        * No hidden chain-of-thought field.
    """
    from socrates_runtime import SocratesRuntime
    from socrates_runtime.phase_executor import ExecutionMode

    intervention = resolve_intervention_profile(intervention_profile_name)

    trace_dir = (Path(runs_dir) / "socrates_api"
                 if runs_dir else None)
    runtime = SocratesRuntime(trace_dir=trace_dir)

    mode = (ExecutionMode.LIVE if execution_mode == "LIVE"
            else ExecutionMode.DETERMINISTIC)
    try:
        result = runtime.run(text, mode=mode,
                              intervention_profile=intervention,
                              question_set_request=question_set_request)
    except TypeError:
        # Backcompat: SocratesRuntime.run without B2 intervention or
        # B2Q question-set kwarg.
        try:
            result = runtime.run(text, mode=mode,
                                  intervention_profile=intervention)
        except TypeError:
            result = runtime.run(text, mode=mode)

    public = result.to_public()
    return {
        "runtime_layer": RUNTIME_LAYER_TAG,
        "run_id": public.get("run_id"),
        "trace_id": public.get("trace_id"),
        "terminal": public.get("terminal"),
        "execution_mode": public.get("execution_mode"),
        "provider_id": public.get("provider_id"),
        "model_id": public.get("model_id"),
        "mounted_phases": public.get("mounted_phases", []),
        "state": public.get("state", {}),
        "rendering": public.get("rendering"),
        "trace_path": public.get("trace_path"),
        "duration_ms": public.get("duration_ms"),
        "intervention_profile": intervention_profile_name,
        # B2R: expose the derived plan + the post-terminal liberatory
        # step at the top level of the response so a caller can prove
        # pre-render pressure without walking `state`.
        "intervention_plan": public.get("intervention_plan"),
        "liberatory_pass_result": public.get("liberatory_pass_result"),
        # B2Q: expose the QuestionSetPlan when derived. Non-None
        # means the returned rendering text was authored from this
        # plan, not from the stochastic renderer — the count and
        # hierarchy are causally governed by the material topology.
        "question_set_plan": public.get("question_set_plan"),
    }

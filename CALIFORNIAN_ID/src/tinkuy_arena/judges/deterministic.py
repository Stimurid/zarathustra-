"""The first judge — reads facts out of a real match trace.

Every dimension answered here is answered from code, never from a model.
The rubric is small on purpose: it names the properties an operator would
verify by hand in ten seconds if they had to. Additional properties (LLM
judgments, epistemic assessments) join the Arena as separate judges — this
one stays boring by design.
"""
from __future__ import annotations

import secrets

from ..protocol import EvaluationRecord, Judge, Match

#: The dimensions this judge produces. Names are stable; adding new ones is
#: fine, renaming needs migration.
D_RESPONDED = "d.responded"
D_NO_ERROR = "d.no_runtime_error"
D_ARGUMENT_GRAPH_NON_EMPTY = "d.argument_graph_non_empty"
D_COUNCIL_INVOKED = "d.council_invoked"
D_SECURITY_CLEAN = "d.security_clean"
D_RESPONSE_HAS_CONTENT = "d.response_has_content"


class DeterministicJudge:
    """Pure-code judge. No provider, no external state, fully reproducible.

    An engine kind that could not possibly satisfy a dimension gets
    ``unknown`` rather than ``fail`` — the baseline_single_agent is not a
    council, and marking its lack of an argument graph as a failure would
    be dishonest.
    """

    judge_id: str = "arena.judge.deterministic"
    version: str = "0.1.0"

    def dimensions(self) -> list[str]:
        return [D_RESPONDED, D_NO_ERROR, D_ARGUMENT_GRAPH_NON_EMPTY,
                D_COUNCIL_INVOKED, D_SECURITY_CLEAN, D_RESPONSE_HAS_CONTENT]

    def evaluate(self, match: Match, participant_id: str
                 ) -> list[EvaluationRecord]:
        turn = match.turn_for(participant_id)
        if turn is None:
            return [self._record(match, participant_id, dim, "unknown",
                                 evidence="no turn recorded")
                    for dim in self.dimensions()]

        engine = (turn.runtime_summary or {}).get("engine", "")
        supports_council = engine == "zarathustra_council"

        out = [
            self._record(
                match, participant_id, D_RESPONDED,
                "pass" if not turn.failed else "fail",
                value=not turn.failed,
                evidence=(turn.error or "turn executed without exception"),
            ),
            self._record(
                match, participant_id, D_NO_ERROR,
                "pass" if not turn.error else "fail",
                value=(turn.error or ""),
                evidence=turn.error or "",
            ),
            self._record(
                match, participant_id, D_RESPONSE_HAS_CONTENT,
                "pass" if turn.response_text.strip() else "fail",
                value=len(turn.response_text),
                evidence=f"response length = {len(turn.response_text)}",
            ),
        ]

        # -- council-specific dimensions --
        if supports_council:
            council_turns = int((turn.runtime_summary or {}).get("council_turns", 0))
            out.append(self._record(
                match, participant_id, D_COUNCIL_INVOKED,
                "pass" if council_turns > 0 else "fail",
                value=council_turns,
                evidence=f"{council_turns} council turn(s) recorded",
            ))
            amap = (turn.runtime_summary or {}).get("argument_map", {})
            total = sum(int(v or 0) for v in amap.values())
            out.append(self._record(
                match, participant_id, D_ARGUMENT_GRAPH_NON_EMPTY,
                "pass" if total > 0 else "fail",
                value=amap,
                evidence=f"total argument-graph entries = {total}",
            ))
            sec = list((turn.runtime_summary or {}).get("security_events") or [])
            out.append(self._record(
                match, participant_id, D_SECURITY_CLEAN,
                "pass" if not sec else "partial",
                value=sec,
                evidence=("no security events" if not sec
                          else f"events = {sec}"),
            ))
        else:
            for dim in (D_COUNCIL_INVOKED, D_ARGUMENT_GRAPH_NON_EMPTY,
                        D_SECURITY_CLEAN):
                out.append(self._record(
                    match, participant_id, dim, "unknown",
                    evidence=f"engine_kind={engine!r} does not surface this signal",
                ))
        return out

    def _record(self, match: Match, participant_id: str, dim_id: str,
                verdict: str, value=None, evidence: str = "") -> EvaluationRecord:
        return EvaluationRecord(
            record_id=f"ev_{secrets.token_hex(6)}",
            match_id=match.match_id,
            participant_id=participant_id,
            dim_id=dim_id, verdict=verdict, value=value, evidence=evidence,
            provenance={"judge_id": self.judge_id, "version": self.version},
        )

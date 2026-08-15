"""Working Memory seam with the Socrates authority gate.

The invariant this exists to enforce:

    producing information  ≠  authority to persist information

The substrate already exists and is durable — ``NarrativeStore`` (SQLite, one
database per workspace, typed cross-run notes). What did not exist anywhere in
the repository is the gate: ``NarrativeStore.add()`` writes immediately, and a
content search across every local repository found no ``propose_write`` /
``commit_write`` semantics at all.

So this module adds the **policy**, not a store. It is important that it owns no
database:

    * ``create_new_memory_store: false`` is frozen in the binding;
    * a rejected proposal must leave no trace in any database, which is only
      true if proposals never touch one;
    * a second memory database would "solve" D-S26-001 by moving the problem.

A proposal lives in memory for the duration of the session and is reported into
the existing RunTrace. Committing delegates to ``NarrativeStore.add`` — the real
organ, the real file, the real table.
"""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .identity import BindingResult, identify

ORGAN = "working_memory"

#: Mirrors ``californian_id.narrative_memory.NOTE_KINDS``; imported lazily at
#: call time so this module never becomes the authority on what a note may be.
PROPOSED = "PROPOSED"
COMMITTED = "COMMITTED"
REJECTED = "REJECTED"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class WriteAuthority:
    """Who is allowed to make a proposal durable, and on what grounds.

    Socrates' G-S18 state-write gate is expressed here as data rather than as
    code: the runtime does not decide authority, it records the decision it was
    given and refuses when it was not given one.
    """
    granted: bool
    granted_by: str = ""
    basis: str = ""
    #: Only a human-owned or explicitly delegated authority may persist.
    authority_kind: str = "NONE"     # HUMAN | SYSTEM_DELEGATED | NONE

    @classmethod
    def denied(cls, reason: str) -> "WriteAuthority":
        return cls(granted=False, basis=reason, authority_kind="NONE")


@dataclass
class WriteProposal:
    """A candidate write. Not persisted, by construction."""
    proposal_id: str
    workspace_id: str
    kind: str
    text: str
    related_run_ids: list[str] = field(default_factory=list)
    author: str = "socrates"
    state: str = PROPOSED
    created_at: str = field(default_factory=_now)
    decided_at: str = ""
    decision_reason: str = ""
    committed_note_id: str = ""

    def content_hash(self) -> str:
        return hashlib.sha256(
            f"{self.workspace_id}|{self.kind}|{self.text}".encode("utf-8")
        ).hexdigest()[:16]

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["content_hash"] = self.content_hash()
        return d


def _store_for(workspace_id: str, db_path: Path | str | None):
    from californian_id.narrative_memory import NarrativeStore

    if db_path is not None:
        return NarrativeStore(Path(db_path))
    return NarrativeStore.for_workspace(workspace_id)


# ---------------------------------------------------------------- READ

def read(workspace_id: str = "default", kind: str | None = None,
         limit: int = 50, db_path: Path | str | None = None) -> BindingResult:
    """`working_memory.read` — read the real durable store."""
    from californian_id.narrative_memory import NarrativeStore

    ident = identify(ORGAN, NarrativeStore.list)
    try:
        store = _store_for(workspace_id, db_path)
    except Exception as exc:                                  # noqa: BLE001
        return BindingResult(ORGAN, "working_memory.read", False,
                             reason=f"хранилище недоступно: {exc}", identity=ident)
    try:
        notes = store.list(kind=kind, limit=limit)
    finally:
        store.close()
    return BindingResult(
        ORGAN, "working_memory.read", True, value=notes, identity=ident,
        provenance={"workspace_id": workspace_id, "kind": kind,
                    "count": len(notes), "db_path": str(store.db_path)})


def read_one(note_id: str, workspace_id: str = "default",
             db_path: Path | str | None = None) -> BindingResult:
    """Read back exactly one note — the readback half of persistence proof."""
    from californian_id.narrative_memory import NarrativeStore

    ident = identify(ORGAN, NarrativeStore.get)
    store = _store_for(workspace_id, db_path)
    try:
        note = store.get(note_id)
    finally:
        store.close()
    if note is None:
        return BindingResult(ORGAN, "working_memory.read_one", False,
                             reason=f"записи нет в хранилище: {note_id}",
                             identity=ident)
    return BindingResult(ORGAN, "working_memory.read_one", True, value=note,
                         identity=ident, provenance={"note_id": note_id})


# ------------------------------------------------------- PROPOSE / DECIDE

def propose_write(workspace_id: str, kind: str, text: str,
                  related_run_ids: list[str] | None = None,
                  author: str = "socrates") -> BindingResult:
    """`working_memory.propose_write` — produce a candidate, persist nothing.

    Validation borrows the store's own rules (kind vocabulary, non-empty text)
    so a proposal that would be refused at commit time is refused here, at the
    cheap end — but it still does not write.
    """
    from californian_id.narrative_memory import NOTE_KINDS

    ident = identify(ORGAN, propose_write)
    if kind not in NOTE_KINDS:
        return BindingResult(
            ORGAN, "working_memory.propose_write", False,
            reason=f"неизвестный вид записи: {kind}; допустимые: "
                   f"{sorted(NOTE_KINDS)}", identity=ident)
    if not text or not text.strip():
        return BindingResult(ORGAN, "working_memory.propose_write", False,
                             reason="пустой текст записи", identity=ident)

    proposal = WriteProposal(
        proposal_id=f"prop_{uuid.uuid4().hex[:12]}",
        workspace_id=workspace_id, kind=kind, text=text.strip(),
        related_run_ids=list(related_run_ids or []), author=author)
    return BindingResult(
        ORGAN, "working_memory.propose_write", True, value=proposal,
        identity=ident,
        provenance={"proposal_id": proposal.proposal_id,
                    "content_hash": proposal.content_hash(),
                    "persisted": False,
                    "note": "предложение существует только в памяти сессии"})


def reject_write(proposal: WriteProposal, reason: str) -> BindingResult:
    """`working_memory.reject_write` — refuse, and leave the store untouched."""
    ident = identify(ORGAN, reject_write)
    if proposal.state != PROPOSED:
        return BindingResult(ORGAN, "working_memory.reject_write", False,
                             reason=f"предложение уже в состоянии {proposal.state}",
                             identity=ident)
    proposal.state = REJECTED
    proposal.decided_at = _now()
    proposal.decision_reason = reason
    return BindingResult(
        ORGAN, "working_memory.reject_write", True, value=proposal,
        identity=ident,
        provenance={"proposal_id": proposal.proposal_id, "persisted": False,
                    "reason": reason})


def commit_if_authorized(proposal: WriteProposal, authority: WriteAuthority,
                         db_path: Path | str | None = None) -> BindingResult:
    """`working_memory.commit_if_authorized` — the gate.

    Without granted authority nothing reaches the store, and the refusal is
    explicit. With it, the write is delegated to ``NarrativeStore.add`` — this
    module never issues SQL of its own.
    """
    from californian_id.narrative_memory import NarrativeNote, NarrativeStore

    ident = identify(ORGAN, NarrativeStore.add)

    if proposal.state != PROPOSED:
        return BindingResult(
            ORGAN, "working_memory.commit_if_authorized", False,
            reason=f"предложение уже в состоянии {proposal.state} — "
                   "повторная фиксация запрещена", identity=ident)

    if not authority.granted or authority.authority_kind == "NONE":
        proposal.state = REJECTED
        proposal.decided_at = _now()
        proposal.decision_reason = (
            authority.basis or "полномочие на запись не предоставлено")
        return BindingResult(
            ORGAN, "working_memory.commit_if_authorized", False,
            reason=("шлюз состояния закрыт: " + proposal.decision_reason),
            identity=ident,
            provenance={"proposal_id": proposal.proposal_id, "persisted": False,
                        "authority_kind": authority.authority_kind,
                        "invariant": "порождение информации ≠ полномочие её сохранить"})

    note = NarrativeNote(
        note_id=f"wm_{proposal.content_hash()}",
        workspace_id=proposal.workspace_id,
        kind=proposal.kind,
        text=proposal.text,
        related_run_ids=list(proposal.related_run_ids),
        author=proposal.author,
    )
    store = _store_for(proposal.workspace_id, db_path)
    try:
        store.add(note)
        db = str(store.db_path)
    finally:
        store.close()

    proposal.state = COMMITTED
    proposal.decided_at = _now()
    proposal.decision_reason = authority.basis
    proposal.committed_note_id = note.note_id
    return BindingResult(
        ORGAN, "working_memory.commit_if_authorized", True, value=note,
        identity=ident,
        provenance={"proposal_id": proposal.proposal_id, "persisted": True,
                    "note_id": note.note_id, "db_path": db,
                    "granted_by": authority.granted_by,
                    "authority_kind": authority.authority_kind})

"""Hybrid managed RAG over Zarathustra cultural corpus.

Three logical namespaces:
    - zarathustra_scenes          — SceneOperationCard(card_type=scene)
    - zarathustra_operations      — SceneOperationCard(card_type in {operation, completion_pattern})
    - zarathustra_primary_fragments — chunks of primary text (normalized/)

Router:
    BodyProjection + tension --> required_function --> metadata filter -->
    hybrid lexical retrieval --> rerank --> 1..3 cards [+ 1..3 fragments] --> Zarathustra prompt.

This runtime uses ONLY lexical (BM25-lite) retrieval. Every retrieval event
carries provenance (source_id, locator, quote_hash). Every event goes into
trace via `record_event`.

No external vector DB required. When an embedding backend is later added,
the interface `retrieve(...)` stays the same.
"""
from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import yaml

from .config import PACKAGE_ROOT


CORPUS_ROOT = PACKAGE_ROOT / "corpus" / "zarathustra"
CARDS_DIRS = ("scenes", "operations", "constraints", "risks")
NORMALIZED_DIR = CORPUS_ROOT / "normalized"


# ------------------------- data types -------------------------
@dataclass
class RetrievedCard:
    card_id: str
    card_type: str  # scene | operation | constraint | risk | completion_pattern
    title: str
    score: float
    file_path: str
    metadata: dict[str, Any]
    provenance: dict[str, Any]
    reason: str  # why picked


@dataclass
class RetrievedFragment:
    source_id: str
    locator: str
    text: str
    score: float
    file_path: str
    provenance: dict[str, Any]


@dataclass
class RetrievalEvent:
    """Traceable record of one retrieval call."""
    query: str
    filters: dict[str, Any]
    namespace: str
    top_k: int
    hits_card: list[dict] = field(default_factory=list)
    hits_fragment: list[dict] = field(default_factory=list)
    routing_reason: str = ""


# ------------------------- indexes -------------------------
def _load_all_cards() -> list[dict]:
    out: list[dict] = []
    for d in CARDS_DIRS:
        p = CORPUS_ROOT / d
        if not p.exists():
            continue
        for f in sorted(p.glob("*.yaml")):
            try:
                data = yaml.safe_load(f.read_text(encoding="utf-8"))
                if data:
                    data["_file"] = str(f.relative_to(CORPUS_ROOT))
                    out.append(data)
            except Exception:
                continue
    return out


def _chunk_text(text: str, size: int = 800, overlap: int = 200) -> list[str]:
    if not text:
        return []
    text = re.sub(r"\s+", " ", text)
    if len(text) <= size:
        return [text]
    chunks: list[str] = []
    step = max(1, size - overlap)
    for start in range(0, len(text), step):
        chunks.append(text[start:start + size])
        if start + size >= len(text):
            break
    return chunks


def _load_all_fragments(max_files: int | None = None, chunk_size: int = 800) -> list[dict]:
    """Load and chunk primary corpus. Cheap because we already normalized."""
    frags: list[dict] = []
    if not NORMALIZED_DIR.exists():
        return _load_fragment_fallback_from_cards()
    files = sorted(NORMALIZED_DIR.glob("*.txt"))
    if not files:
        return _load_fragment_fallback_from_cards()
    if max_files:
        files = files[:max_files]
    for f in files:
        stem = f.stem
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for i, chunk in enumerate(_chunk_text(text, size=chunk_size)):
            qhash = hashlib.sha256(chunk.encode("utf-8")).hexdigest()[:16]
            frags.append({
                "source_id": stem.upper(),
                "locator": f"CHUNK={stem}#{i}",
                "text": chunk,
                "quote_hash": f"sha256:{qhash}",
                "_file": str(f.relative_to(CORPUS_ROOT)),
            })
    return frags


def _load_fragment_fallback_from_cards() -> list[dict]:
    """Build a minimal fragment index from card provenance when corpus texts are absent."""
    frags: list[dict] = []
    for card in _load_all_cards():
        card_text = _card_search_text(card)
        if not card_text:
            continue
        for source in card.get("primary_sources") or []:
            source_id = str(source.get("source_id") or "").strip()
            if not source_id:
                continue
            locator = str(source.get("locator") or f"CARD={card.get('card_id', '?')}")
            quote_hash = str(source.get("quote_hash") or "")
            if not quote_hash:
                digest = hashlib.sha256(card_text.encode("utf-8")).hexdigest()[:16]
                quote_hash = f"sha256:{digest}"
            frags.append({
                "source_id": source_id.upper(),
                "locator": locator,
                "text": card_text,
                "quote_hash": quote_hash,
                "_file": str(card.get("_file", "")),
            })
    return frags


# ------------------------- retrieval math -------------------------
_TOKEN_RE = re.compile(r"[0-9A-Za-z_]+|[\u0400-\u04FF]+", re.UNICODE)


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "") if len(t) > 2]


def _bm25_score(query_toks: list[str], docs: list[list[str]]) -> list[float]:
    n = len(docs)
    if n == 0:
        return []
    avgdl = sum(len(d) for d in docs) / n or 1
    df: Counter[str] = Counter()
    for d in docs:
        for t in set(d):
            df[t] += 1
    k1, b = 1.5, 0.75
    scores: list[float] = []
    for d in docs:
        tf = Counter(d)
        dl = len(d)
        s = 0.0
        for qt in query_toks:
            if qt not in tf:
                continue
            idf = math.log(1 + (n - df[qt] + 0.5) / (df[qt] + 0.5))
            s += idf * (tf[qt] * (k1 + 1) / (tf[qt] + k1 * (1 - b + b * dl / (avgdl or 1))))
        scores.append(s)
    return scores


# ------------------------- routing -------------------------
# Map "required function" of Zarathustra to card_type filter + query hints.
ROUTE_MAP = {
    # function : (namespace filter, hint tokens)
    "polyphony_at_completion": ("scene|constraint|completion_pattern",
                                 ["полифон", "polyphony", "незаверш"]),
    "unmask_thesis_substitution": ("risk|operation",
                                    ["подмена", "тезис", "straw"]),
    "detect_trick": ("risk", ["уловк", "trick", "fallacy"]),
    "introduce_absent_subject": ("operation", ["парламент", "нечеловеч", "актор", "absent"]),
    "shift_ontology": ("operation", ["ризом", "детерритори", "assemblage", "shift"]),
    "stop_futile_dispute": ("operation|completion_pattern",
                             ["прекрат", "бесплод", "остановк"]),
    "responsible_act": ("operation", ["поступок", "ответственн"]),
    "meet_autonomous_figure": ("scene", ["figure", "фигур", "voice", "воображен"]),
    "hold_thesis": ("operation", ["удержан", "тезис"]),
    "avoid_false_synthesis": ("risk|completion_pattern",
                              ["ложн", "synthesis", "консенсус"]),
    "hold_multiple_selves": ("scene",
                             ["множествен", "механичн", "наблюден"]),
    "prevent_authorial_absorption": ("constraint",
                                      ["автор", "герой", "поглощен"]),
    "any": ("scene|operation|constraint|risk|completion_pattern", []),
}


def infer_required_function(
    body_snapshot: dict,
    dispute_hint: dict | None = None,
    active_operation: str | None = None,
) -> str:
    """Deterministic routing from state to required intervention function."""
    dispute_hint = dispute_hint or {}
    fallacies = set(dispute_hint.get("fallacies_or_tricks") or [])
    if "straw_man" in fallacies:
        return "unmask_thesis_substitution"
    if "proof_by_assertion" in fallacies:
        return "stop_futile_dispute"
    if fallacies & {"ad_hominem", "appeal_to_majority", "motte_and_bailey"}:
        return "detect_trick"
    if dispute_hint.get("thesis_preserved") is False:
        return "unmask_thesis_substitution"
    if active_operation in {"build_future_image", "shift_temporal_horizon"}:
        return "introduce_absent_subject"
    if active_operation in {"problematize_question", "create_aporia"}:
        return "shift_ontology"
    if active_operation in {"defend"}:
        return "hold_thesis"
    if active_operation in {"propose_alliance"}:
        return "polyphony_at_completion"
    if len(body_snapshot.get("voices_history", [])) >= 4 and \
            not body_snapshot.get("ontological_premises"):
        return "avoid_false_synthesis"
    return "any"


# ------------------------- main API -------------------------
class CulturalIndex:
    """Managed hybrid RAG over Zarathustra cultural corpus.

    Lazy-built and cached. Rebuilds on first `retrieve`; deterministic per pack.
    """

    def __init__(self) -> None:
        self._cards: list[dict] | None = None
        self._card_tokens: list[list[str]] | None = None
        self._frags: list[dict] | None = None
        self._frag_tokens: list[list[str]] | None = None
        self._events: list[RetrievalEvent] = []

    # ---- indexes ----
    def _cards_index(self) -> tuple[list[dict], list[list[str]]]:
        if self._cards is None:
            self._cards = _load_all_cards()
            self._card_tokens = [_tokens(_card_search_text(c)) for c in self._cards]
        return self._cards, self._card_tokens  # type: ignore

    def _fragments_index(self) -> tuple[list[dict], list[list[str]]]:
        if self._frags is None:
            self._frags = _load_all_fragments()
            self._frag_tokens = [_tokens(f["text"]) for f in self._frags]
        return self._frags, self._frag_tokens  # type: ignore

    # ---- retrieval ----
    def retrieve_cards(
        self,
        query: str,
        required_function: str = "any",
        top_k: int = 3,
    ) -> tuple[list[RetrievedCard], RetrievalEvent]:
        cards, card_toks = self._cards_index()
        filt, hint_tokens = ROUTE_MAP.get(required_function, ROUTE_MAP["any"])
        allowed_types = set(filt.split("|"))
        # metadata filter
        filtered = [
            (i, c) for i, c in enumerate(cards) if c.get("card_type") in allowed_types
        ]
        if not filtered:
            filtered = list(enumerate(cards))
        filtered_docs = [card_toks[i] for i, _ in filtered]

        query_toks = _tokens(query) + list(hint_tokens)
        scores = _bm25_score(query_toks, filtered_docs)
        pairs = sorted(zip(scores, filtered), key=lambda x: x[0], reverse=True)[:top_k]

        out: list[RetrievedCard] = []
        for score, (idx, c) in pairs:
            if score <= 0:
                continue
            provs = c.get("primary_sources") or []
            out.append(RetrievedCard(
                card_id=c.get("card_id", "?"),
                card_type=c.get("card_type", "?"),
                title=c.get("title", ""),
                score=float(score),
                file_path=c.get("_file", ""),
                metadata={
                    "activation_conditions": c.get("activation_conditions", []),
                    "contraindications": c.get("contraindications", []),
                    "provenance_status": c.get("provenance_status", "unknown"),
                    "operation": c.get("operation", {}),
                    "figures": c.get("figures", []),
                },
                provenance={"primary_sources": provs, "file": c.get("_file")},
                reason=f"required_function={required_function}, score={score:.2f}",
            ))
        event = RetrievalEvent(
            query=query[:200],
            filters={"card_type_in": sorted(allowed_types), "required_function": required_function},
            namespace="zarathustra_scenes+operations+constraints+risks",
            top_k=top_k,
            hits_card=[{
                "card_id": r.card_id, "card_type": r.card_type,
                "score": r.score, "title": r.title,
                "provenance": r.provenance,
            } for r in out],
            routing_reason=f"required_function={required_function}",
        )
        self._events.append(event)
        return out, event

    def retrieve_primary_fragments(
        self,
        query: str,
        source_id_filter: str | None = None,
        top_k: int = 2,
    ) -> tuple[list[RetrievedFragment], RetrievalEvent]:
        frags, frag_toks = self._fragments_index()
        # metadata filter
        if source_id_filter:
            f_pool = [(i, f) for i, f in enumerate(frags)
                      if source_id_filter.upper() in f["source_id"].upper()]
        else:
            f_pool = list(enumerate(frags))
        if not f_pool:
            event = RetrievalEvent(
                query=query[:200],
                filters={"source_id_filter": source_id_filter},
                namespace="zarathustra_primary_fragments",
                top_k=top_k,
                hits_fragment=[],
                routing_reason="no_fragments_matched_filter",
            )
            self._events.append(event)
            return [], event
        docs = [frag_toks[i] for i, _ in f_pool]
        scores = _bm25_score(_tokens(query), docs)
        pairs = sorted(zip(scores, f_pool), key=lambda x: x[0], reverse=True)[:top_k]

        out: list[RetrievedFragment] = []
        for score, (idx, f) in pairs:
            if score <= 0:
                continue
            out.append(RetrievedFragment(
                source_id=f["source_id"],
                locator=f["locator"],
                text=f["text"][:600],
                score=float(score),
                file_path=f["_file"],
                provenance={
                    "source_id": f["source_id"],
                    "locator": f["locator"],
                    "quote_hash": f["quote_hash"],
                },
            ))
        event = RetrievalEvent(
            query=query[:200],
            filters={"source_id_filter": source_id_filter or "*"},
            namespace="zarathustra_primary_fragments",
            top_k=top_k,
            hits_fragment=[{
                "source_id": r.source_id, "locator": r.locator,
                "score": r.score, "provenance": r.provenance,
            } for r in out],
            routing_reason="lexical_bm25_fragment_search",
        )
        self._events.append(event)
        return out, event

    # ---- events ----
    def drain_events(self) -> list[RetrievalEvent]:
        e = self._events
        self._events = []
        return e


def _card_search_text(c: dict) -> str:
    parts = [
        c.get("title", ""),
        c.get("situation", ""),
        " ".join(c.get("figures") or []),
        " ".join(c.get("activation_conditions") or []),
        " ".join(c.get("contraindications") or []),
    ]
    op = c.get("operation") or {}
    parts.append(op.get("name", ""))
    parts.append(op.get("description", ""))
    return " ".join(p for p in parts if p)

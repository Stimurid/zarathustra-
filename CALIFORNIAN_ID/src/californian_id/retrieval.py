"""Persona-scoped retrieval. Lexical fallback (BM25-lite) so runtime does not
require an external vector store.

Each persona has a `corpus/` directory. Retrieval never mixes persona corpora
unless explicitly allowed. Provenance is always attached.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EvidenceChunk:
    source_id: str
    locator: str
    text: str
    score: float
    persona_id: str
    provenance: dict[str, str]
    retrieval_reason: str


_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text) if len(t) > 2]


def _chunk_file(path: Path, chunk_size: int = 800, overlap: int = 200) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    text = re.sub(r"\s+", " ", text)
    if len(text) <= chunk_size:
        return [text] if text else []
    chunks: list[str] = []
    step = max(1, chunk_size - overlap)
    for start in range(0, len(text), step):
        chunk = text[start : start + chunk_size]
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(text):
            break
    return chunks


class LexicalPersonaRetriever:
    def __init__(self, corpus_root: Path):
        self.corpus_root = corpus_root

    def retrieve(
        self,
        persona_id: str,
        query: str,
        top_k: int = 3,
    ) -> list[EvidenceChunk]:
        pdir = self.corpus_root / persona_id / "corpus"
        if not pdir.exists():
            return []
        files: list[Path] = [
            p for p in pdir.rglob("*")
            if p.is_file() and p.suffix.lower() in {".md", ".txt"}
        ]
        if not files:
            return []
        chunks: list[tuple[Path, int, str]] = []
        for f in files:
            for i, chunk in enumerate(_chunk_file(f)):
                chunks.append((f, i, chunk))
        if not chunks:
            return []
        query_toks = _tokens(query)
        if not query_toks:
            return []
        docs = [_tokens(c[2]) for c in chunks]
        n_docs = len(docs)
        avgdl = sum(len(d) for d in docs) / n_docs if n_docs else 1
        df: Counter[str] = Counter()
        for d in docs:
            for t in set(d):
                df[t] += 1
        k1, b = 1.5, 0.75
        scored: list[tuple[float, int]] = []
        for idx, d in enumerate(docs):
            tf = Counter(d)
            dl = len(d)
            score = 0.0
            for qt in query_toks:
                if qt not in tf:
                    continue
                idf = math.log(1 + (n_docs - df[qt] + 0.5) / (df[qt] + 0.5))
                term_score = idf * (
                    tf[qt] * (k1 + 1)
                    / (tf[qt] + k1 * (1 - b + b * dl / (avgdl or 1)))
                )
                score += term_score
            if score > 0:
                scored.append((score, idx))
        scored.sort(reverse=True)
        top = scored[:top_k]
        results: list[EvidenceChunk] = []
        for score, idx in top:
            f, chunk_i, text = chunks[idx]
            results.append(
                EvidenceChunk(
                    source_id=f.name,
                    locator=f"{f.relative_to(self.corpus_root)}#chunk={chunk_i}",
                    text=text,
                    score=float(score),
                    persona_id=persona_id,
                    provenance={"path": str(f), "chunk_index": str(chunk_i)},
                    retrieval_reason="lexical_bm25_fallback",
                )
            )
        return results

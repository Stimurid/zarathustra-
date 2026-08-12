r"""B-1.3 — Long text chunker.

Простой regex-разбивал длинного текста на seкции → псевдо-юниты для
run_from_units.

Приоритет разбиения:
  1. Markdown headings `^#{1,6}\s+`
  2. Numbered sections `^\d+\.\s+` или `^[IVX]+\.\s+`
  3. Blank line paragraphs (2+ \n)
  4. Length fallback (soft-max chars → break at last sentence end)

Ограничение (по BACKLOG.md): это встраивание простейшего резчика,
не полноценная ткань Тинкуя. Для критичных задач — использовать
Пик 5 fabric parser.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..schemas import SemanticUnit, UnitPack


# Разумный размер одного псевдо-юнита. Не слишком мало (не хочу 500 юнитов
# на 100 KB), не слишком много (юнит должен помещаться в один turn context).
DEFAULT_TARGET_CHARS = 2000
DEFAULT_MAX_CHARS = 4000
DEFAULT_MIN_CHARS = 300


_HEADING_RE = re.compile(r"^(?:#{1,6}\s+.+|(?:\d+|[IVXLC]+)\.\s+.+)$", re.MULTILINE)
_SENT_END_RE = re.compile(r"[.!?…]['\"»)]?\s")


@dataclass
class Chunk:
    """Промежуточный chunk перед превращением в SemanticUnit."""
    index: int
    title: str
    text: str
    start_char: int
    end_char: int


def _split_by_headings(text: str) -> list[Chunk]:
    """Разбивает по заголовкам (md-headings, numbered sections)."""
    matches = list(_HEADING_RE.finditer(text))
    if len(matches) < 2:
        return []
    chunks: list[Chunk] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        title = m.group(0).strip().lstrip("#").strip()
        body = text[start:end].strip()
        chunks.append(Chunk(index=i, title=title[:120],
                            text=body, start_char=start, end_char=end))
    return chunks


def _split_by_paragraphs(text: str,
                        target: int = DEFAULT_TARGET_CHARS,
                        soft_max: int = DEFAULT_MAX_CHARS) -> list[Chunk]:
    """Разбивает по blank line, накапливая до target chars."""
    paras = re.split(r"\n\s*\n", text)
    chunks: list[Chunk] = []
    buf: list[str] = []
    buf_start = 0
    cursor = 0
    for para in paras:
        if not para.strip():
            cursor += len(para) + 2
            continue
        if buf and sum(len(p) for p in buf) + len(para) > soft_max:
            _flush(chunks, buf, buf_start, cursor)
            buf = []
            buf_start = cursor
        if not buf:
            buf_start = cursor
        buf.append(para)
        cursor += len(para) + 2
        if sum(len(p) for p in buf) >= target:
            _flush(chunks, buf, buf_start, cursor)
            buf = []
            buf_start = cursor
    if buf:
        _flush(chunks, buf, buf_start, cursor)
    return chunks


def _flush(chunks: list[Chunk], buf: list[str],
           start: int, end: int) -> None:
    body = "\n\n".join(buf).strip()
    if not body:
        return
    # заголовок = первая строка (или её первые 80 char)
    first_line = body.splitlines()[0].strip() if body else ""
    title = first_line[:100] if first_line else f"chunk {len(chunks) + 1}"
    chunks.append(Chunk(index=len(chunks), title=title,
                        text=body, start_char=start, end_char=end))


def _split_by_length(text: str,
                    target: int = DEFAULT_TARGET_CHARS,
                    hard_max: int = DEFAULT_MAX_CHARS) -> list[Chunk]:
    """Fallback: разбиение по длине с попыткой найти границу предложения."""
    chunks: list[Chunk] = []
    cursor = 0
    i = 0
    while cursor < len(text):
        end = min(cursor + target, len(text))
        if end < len(text):
            # ищем ближайший конец предложения в окне
            window = text[end:min(end + (hard_max - target), len(text))]
            m = _SENT_END_RE.search(window)
            if m:
                end = end + m.end()
        body = text[cursor:end].strip()
        if body:
            first_line = body.splitlines()[0].strip()
            title = first_line[:100] if first_line else f"chunk {i + 1}"
            chunks.append(Chunk(index=i, title=title,
                                text=body, start_char=cursor, end_char=end))
            i += 1
        cursor = end
    return chunks


def chunk_text(text: str, *,
              target: int = DEFAULT_TARGET_CHARS,
              max_chars: int = DEFAULT_MAX_CHARS,
              min_chars: int = DEFAULT_MIN_CHARS) -> list[Chunk]:
    """Public API: разбить текст на chunks в порядке приоритета."""
    if not text or not text.strip():
        return []
    text = text.strip()
    # 1. по заголовкам
    chunks = _split_by_headings(text)
    if chunks and all(len(c.text) <= max_chars * 2 for c in chunks):
        # объединяем слишком маленькие с соседями? Пока оставим как есть
        return [c for c in chunks if len(c.text) >= min_chars] or chunks
    # 2. по параграфам
    chunks = _split_by_paragraphs(text, target=target, soft_max=max_chars)
    # если параграфов нет (single blob) или chunks слишком крупные — fallback
    too_big = any(len(c.text) > max_chars * 1.2 for c in chunks)
    if chunks and not too_big:
        return chunks
    # 3. fallback по длине
    return _split_by_length(text, target=target, hard_max=max_chars)


def to_unit_pack(text: str, *,
                seminar_title: str = "long_text_chunker",
                target: int = DEFAULT_TARGET_CHARS,
                max_chars: int = DEFAULT_MAX_CHARS) -> UnitPack:
    """Собрать UnitPack из raw text через chunker.

    Каждый chunk → SemanticUnit с intention='сведения' (нейтральная).
    Для аккуратной интеракции с советом — используй потом focus_on
    в run_from_units, если хочешь обсудить конкретные chunk'и.
    """
    chunks = chunk_text(text, target=target, max_chars=max_chars)
    units: list[SemanticUnit] = []
    for c in chunks:
        units.append(SemanticUnit(
            unit_id=f"chunk_{c.index:04d}",
            title=c.title or f"chunk {c.index}",
            intention="сведения",
            abstract=c.text[:400],
            key_concepts=[],
        ))
    return UnitPack(
        seminar_title=seminar_title,
        source_path=None,
        cutter_id="californian_id.adapters.text_chunker",
        cutter_model="regex_v1",
        units=units,
    )

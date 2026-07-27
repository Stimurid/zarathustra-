"""Regex parser for md-units format used by the semantic cutter.

Two shapes observed in the wild:
    1) `### U1 — Title` sections with fields as bullet lists
       (Заголовок / Намерение / Объект / Участники / Позиция / Тема-Рема /
        Тулмин / Вмешательства / Провенанс / Абстракт).
    2) Same, but preceded by a preamble with:
       - Provenance (tool, model, source file)
       - Speaker inventory (labels ↔ roles ↔ names)
       - Diarization defects
       - Recognition damage

Both shapes are supported. Preamble becomes SourceAudit; U-blocks become
SemanticUnit list.
"""
from __future__ import annotations

import re
from pathlib import Path

from ...schemas import (
    DiarizationDefect,
    SemanticUnit,
    SourceAudit,
    ThemeRheme,
    ToulminBundle,
    UnitPack,
    UnitParticipant,
    UnitProvenance,
)


# --- section detection ---
_UNIT_HEADER_RE = re.compile(
    r"^###\s+(U\d+)\s*[—\-–]\s*(.+?)\s*$",
    flags=re.MULTILINE,
)
_H1_RE = re.compile(r"^#\s+(.+?)\s*$", flags=re.MULTILINE)


def _split_units(text: str) -> tuple[str, list[tuple[str, str, str]]]:
    """Split full md into (preamble, [(unit_id, title, body)]).

    Preamble = everything before the first `### U1 — …` heading.
    """
    matches = list(_UNIT_HEADER_RE.finditer(text))
    if not matches:
        return text, []
    preamble = text[: matches[0].start()]
    units = []
    for i, m in enumerate(matches):
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end]
        # Strip trailing separator lines like `---`
        body = re.sub(r"\n---+\s*$", "", body).strip()
        units.append((m.group(1), m.group(2).strip(), body))
    return preamble, units


# --- unit parsing ---
def _grab_line_after(body: str, label: str) -> str:
    """Return content after `- <label>: <value>` (single-line value)."""
    m = re.search(
        rf"^\s*[-*]\s*{re.escape(label)}\s*[:—]\s*(.+?)\s*$",
        body, flags=re.MULTILINE,
    )
    return m.group(1).strip() if m else ""


def _grab_block_between(body: str, header: str, next_headers: tuple[str, ...] = ()) -> str:
    """Grab the body between `<header>` and any of `next_headers` (or end)."""
    hdr = re.search(rf"^\s*{re.escape(header)}\s*$", body, flags=re.MULTILINE)
    if not hdr:
        return ""
    start = hdr.end()
    end = len(body)
    for nh in next_headers:
        m = re.search(rf"^\s*{re.escape(nh)}\s*$", body[start:], flags=re.MULTILINE)
        if m:
            end = start + m.start()
            break
    return body[start:end].strip()


_PARTICIPANT_RE = re.compile(
    r"([A-ZА-Я][A-Za-zА-Яа-яёЁ_0-9\s]+?)"
    r"(?:\s*\(([^)]+)\))?",
)


def _parse_participants(raw: str) -> list[UnitParticipant]:
    """Best-effort parse of "Роль (Имя), Роль (Имя), Участник_1" list."""
    if not raw:
        return []
    out: list[UnitParticipant] = []
    parts = re.split(r"[,;]\s*", raw)
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # "Методолог (Олег Гринько)" | "Участник_Speaker 8" | "Докладчик"
        m = re.match(r"^([^()]+?)(?:\s*\(([^)]+)\))?\s*$", p)
        if not m:
            continue
        role = m.group(1).strip()
        name = m.group(2).strip() if m.group(2) else None
        # heuristic label detection
        label = ""
        lm = re.search(r"(Speaker\s*\d+|Участник_\d+|Участник_Speaker\s*\d+)", p)
        if lm:
            label = lm.group(1)
        out.append(UnitParticipant(label=label, normalized_role=role, name=name))
    return out


_TR_RE = re.compile(
    r"[-*]\s*Тема\s*:\s*(?P<theme>.+?)\s*\|\s*Рема\s*:\s*(?P<rheme>.+?)\s*$",
    flags=re.MULTILINE,
)


def _parse_theme_rheme(body: str) -> list[ThemeRheme]:
    out: list[ThemeRheme] = []
    tr_block = _grab_block_between(
        body, "Тема-Рема",
        next_headers=("Тулмин", "Вмешательства аудитории внутри ЕС",
                      "Провенанс ЕС", "Опорные цитаты", "Абстракт ЕС"),
    )
    if not tr_block:
        return out
    for m in _TR_RE.finditer(tr_block):
        theme = m.group("theme").strip()
        rheme_full = m.group("rheme").strip()
        # extract locator/participant from ("Роль, индекс 4") pattern in rheme
        loc_m = re.search(r"\(([^)]+),\s*(?:индекс\s*)?([^)]+)\)", rheme_full)
        loc, plabel = "", ""
        if loc_m:
            plabel = loc_m.group(1).strip()
            loc = loc_m.group(2).strip()
        out.append(ThemeRheme(theme=theme, rheme=rheme_full, participant_label=plabel, locator=loc))
    return out


def _parse_toulmin(body: str) -> ToulminBundle | None:
    """Parse the Toulmin block. Some U-blocks don't have one — return None."""
    block = _grab_block_between(
        body, "Тулмин",
        next_headers=("Counterclaim_j", "Вмешательства аудитории внутри ЕС",
                      "Провенанс ЕС", "Опорные цитаты", "Абстракт ЕС"),
    )
    counter_block = _grab_block_between(
        body, "Counterclaim_j",
        next_headers=("Вмешательства аудитории внутри ЕС",
                      "Провенанс ЕС", "Опорные цитаты", "Абстракт ЕС"),
    )
    if not (block or counter_block):
        return None
    def take(field: str, txt: str) -> str:
        m = re.search(
            rf"^\s*[-*]\s*{field}\s*:\s*(.+?)\s*$",
            txt, flags=re.MULTILINE | re.IGNORECASE,
        )
        return m.group(1).strip() if m else ""
    t = ToulminBundle(
        claim=take("Claim", block),
        data=take("Data/Grounds", block) or take("Data", block),
        warrant=take("Warrant", block),
        backing=take("Backing", block),
        qualifier=take("Qualifier", block),
        rebuttal=take("Rebuttal", block),
    )
    if counter_block:
        t.counterclaim = take("Counterclaim", counter_block)
    # if everything empty, no toulmin
    if not any([t.claim, t.data, t.warrant, t.rebuttal, t.counterclaim]):
        return None
    return t


def _parse_provenance(body: str) -> list[UnitProvenance]:
    block = _grab_block_between(
        body, "Провенанс ЕС",
        next_headers=("Опорные цитаты", "Абстракт ЕС"),
    )
    if not block:
        return []
    out: list[UnitProvenance] = []
    # entries like "- [Олег Гринько, 04]", "- [Участник_Speaker 8, idx]"
    for m in re.finditer(r"\[([^\]]+)\]", block):
        raw = m.group(1)
        parts = [p.strip() for p in raw.split(",", 1)]
        who = parts[0] if parts else ""
        loc = parts[1] if len(parts) > 1 else ""
        # separate label vs name
        label_m = re.search(r"(Speaker\s*\d+|Участник_\d+|Участник_Speaker\s*\d+)", who)
        label = label_m.group(1) if label_m else ""
        name = who if not label else who.replace(label, "").strip(" _()")
        out.append(UnitProvenance(participant_label=label, participant_name=name, locator=loc))
    return out


def _parse_abstract(body: str) -> str:
    block = _grab_block_between(body, "Абстракт ЕС")
    return block.strip()


def _parse_unit(unit_id: str, title: str, body: str) -> SemanticUnit:
    u = SemanticUnit(unit_id=unit_id, title=title)
    u.intention = _grab_line_after(body, "Намерение")
    u.object_aspect = _grab_line_after(body, "Объект/аспект")
    u.position = _grab_line_after(body, "Позиция владельца содержания (цели, ответственность)") \
        or _grab_line_after(body, "Позиция владельца содержания")
    participants_raw = _grab_line_after(body, "Участники/роли внутри ЕС") \
        or _grab_line_after(body, "Участники/роли")
    u.participants = _parse_participants(participants_raw)
    u.theme_rheme = _parse_theme_rheme(body)
    u.toulmin = _parse_toulmin(body)
    u.provenance = _parse_provenance(body)
    u.abstract = _parse_abstract(body)
    # crude key_concepts extraction from title + object_aspect words > 3 chars
    words = re.findall(r"[А-Яа-яЁёA-Za-z]{4,}", f"{title} {u.object_aspect}")
    u.key_concepts = sorted(set(w.lower() for w in words))[:12]
    return u


# --- preamble / source audit ---
_ROLE_ROW_RE = re.compile(
    r"^\s*\|\s*(?P<label>[^|]+?)\s*\|\s*(?P<count>\d+)\s*\|\s*(?P<role>[^|]+?)\s*\|",
    flags=re.MULTILINE,
)


def _parse_source_audit(preamble: str) -> SourceAudit | None:
    if len(preamble.strip()) < 100:
        return None
    a = SourceAudit()
    # inventory table: | Метка | Реплик | Нормализованная роль | Основание |
    for m in _ROLE_ROW_RE.finditer(preamble):
        label = m.group("label").strip()
        role = m.group("role").strip()
        if label.lower() in {"метка", "-------", ":---"} or role.lower() in {"нормализованная роль", "-------"}:
            continue
        # skip pure separator rows
        if set(label) <= set("-: "):
            continue
        a.speaker_roles.append(UnitParticipant(label=label, normalized_role=role))
    # diarization defects: bullets with "Разрыв А", "Склейка Б", "Склейка В"
    for m in re.finditer(
        r"(Разрыв|Склейка)\s+[А-ЯA-Z][^\n]*?метка\s+«([^»]+)»",
        preamble,
    ):
        a.diarization_defects.append(DiarizationDefect(
            kind=m.group(1).lower(),
            at_label=m.group(2).strip(),
            description=m.group(0)[:220],
        ))
    # recognition damage: bullets under "Повреждения распознавания"
    dmg_block = _grab_block_between(preamble, "### 1.4. Повреждения распознавания") \
        or _grab_block_between(preamble, "Повреждения распознавания")
    if dmg_block:
        for m in re.finditer(r"«([^»]+)»", dmg_block):
            a.recognition_damage.append({"locator": "verbatim", "verbatim": m.group(1)})
    # ambiguous vocatives — any "минимум два <Имя>" / "два <Имя>" phrase
    for m in re.finditer(
        r"(?:минимум\s+)?два\s+([А-ЯЁ][а-яё]+)",
        preamble, flags=re.IGNORECASE,
    ):
        name = m.group(1)
        a.ambiguous_vocatives.append(f"«{name}» — два лица в комнате")
    # Also catch "вокатив «X» лиц не различ..."
    for m in re.finditer(
        r"вокатив\w*\s+«([^»]+)»[^\n]{0,80}не\s+различ",
        preamble, flags=re.IGNORECASE,
    ):
        a.ambiguous_vocatives.append(f"вокатив «{m.group(1)}» не различает лиц")
    a.notes = preamble.strip()[:2000]
    return a if (a.speaker_roles or a.diarization_defects
                 or a.recognition_damage or a.ambiguous_vocatives) else None


# --- pack metadata from preamble/H1 ---
def _extract_pack_meta(text: str, preamble: str) -> dict:
    meta: dict = {}
    h1 = _H1_RE.search(text)
    if h1:
        meta["seminar_title"] = h1.group(1).strip()
    m = re.search(r"диапазон\s+тайм[-\s]кодов?\s*[:.]?\s*([0-9:]+)\s*[-–—]\s*([0-9:]+)",
                  preamble, flags=re.IGNORECASE)
    if m:
        meta["seminar_locator_span"] = f"{m.group(1)} — {m.group(2)}"
    m = re.search(r"Источник\s*:\s*[`«\"]?([^\n`»\"]+)[`»\"]?", preamble)
    if m:
        meta["source_path"] = m.group(1).strip()
    m = re.search(r"Инструмент\s*:\s*[`]?([^\n`]+?)[`]?\s*$",
                  preamble, flags=re.MULTILINE)
    if m:
        meta["cutter_id"] = m.group(1).strip()
    m = re.search(r"Модель[^:]*:\s*[^`]*[`]?([^\n`]+?)[`]?\s*$",
                  preamble, flags=re.MULTILINE)
    if m:
        meta["cutter_model"] = m.group(1).strip()
    # unresolved questions count (rich preamble might mention)
    m = re.search(r"(\d+)\s+непогаш[её]нн\w+\s+вопрос", preamble)
    if m:
        meta["unresolved_from_preamble"] = int(m.group(1))
    return meta


# --- public API ---
def parse_md_units_text(text: str) -> UnitPack:
    preamble, unit_specs = _split_units(text)
    if not unit_specs:
        raise ValueError("no `### Un — Title` unit headings found; not a units-of-content markdown")
    units = [_parse_unit(uid, title, body) for uid, title, body in unit_specs]
    audit = _parse_source_audit(preamble)
    meta = _extract_pack_meta(text, preamble)
    return UnitPack(
        units=units,
        source_audit=audit,
        seminar_title=meta.get("seminar_title", ""),
        seminar_locator_span=meta.get("seminar_locator_span", ""),
        cutter_id=meta.get("cutter_id", ""),
        cutter_model=meta.get("cutter_model", ""),
        source_path=meta.get("source_path", ""),
    )


def parse_md_units_file(path: str | Path) -> UnitPack:
    return parse_md_units_text(Path(path).read_text(encoding="utf-8"))

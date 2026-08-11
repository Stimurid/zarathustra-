"""B-5.5 Веха 5 — File attach extractor + normalizer.

Пользователь через UI прикрепляет файл (MD/TXT/JSON) во время идущего рана
через WS/REST intervention kind=attach_file. Payload доходит до
Pipeline._consume_pending, оттуда — сюда для нормализации, а Pipeline
инжектит normalized text в system-prompt следующего persona turn'а
(или в user context, если attach_to_persona не задан).

Ограничения (MVP):
  - Text-only форматы: .md, .txt, .json, .yaml, .yml.
  - Максимум ATTACH_MAX_CHARS (default 30 000) — обрезается с пометкой.
  - Одна attach = ≤5 KB инжектится (первый chunk); полный текст в audit.
  - PDF/DOCX/HTML — не поддерживается в MVP (сообщение об ошибке).

Нет побочных эффектов: чистая функция normalize().
"""
from __future__ import annotations

import json as _json
from dataclasses import dataclass
from typing import Any


ATTACH_MAX_CHARS = 30_000
INJECT_MAX_CHARS = 5_000
SUPPORTED_EXT = {".md", ".txt", ".json", ".yaml", ".yml"}


@dataclass
class NormalizedAttachment:
    filename: str
    ext: str
    text: str                # для инъекции (обрезано до INJECT_MAX_CHARS)
    full_text: str           # для audit (обрезано до ATTACH_MAX_CHARS)
    was_truncated: bool
    attach_to_persona: str = ""
    note: str = ""           # предупреждения если что-то не так


def _ext_of(filename: str) -> str:
    if not filename or "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()


def normalize(payload: dict[str, Any]) -> NormalizedAttachment | None:
    """Принимает payload attach_file intervention. Возвращает нормализованное
    представление или None если payload невалиден.
    """
    if not isinstance(payload, dict):
        return None
    filename = str(payload.get("filename") or "").strip()
    content = payload.get("content")
    if content is None:
        return None
    attach_to_persona = str(payload.get("attach_to_persona") or "").strip()

    ext = _ext_of(filename)
    if ext and ext not in SUPPORTED_EXT:
        return NormalizedAttachment(
            filename=filename, ext=ext, text="", full_text="",
            was_truncated=False, attach_to_persona=attach_to_persona,
            note=f"unsupported ext {ext}; supported: {sorted(SUPPORTED_EXT)}",
        )

    # bytes → str fallback
    if isinstance(content, bytes):
        try:
            content = content.decode("utf-8", errors="replace")
        except Exception:
            return NormalizedAttachment(
                filename=filename, ext=ext, text="", full_text="",
                was_truncated=False, attach_to_persona=attach_to_persona,
                note="binary content not decodable as utf-8",
            )
    if not isinstance(content, str):
        # dict/list — если это JSON payload, сериализуем в pretty
        try:
            content = _json.dumps(content, ensure_ascii=False, indent=2)
        except Exception:
            return None

    # JSON — pretty-print, чтобы читалось LLM
    if ext == ".json":
        try:
            parsed = _json.loads(content)
            content = _json.dumps(parsed, ensure_ascii=False, indent=2)
        except Exception:
            pass  # оставляем как есть, инжектим сырым

    was_truncated = False
    full_text = content
    if len(full_text) > ATTACH_MAX_CHARS:
        full_text = full_text[:ATTACH_MAX_CHARS] + "\n\n... [truncated]"
        was_truncated = True

    inject_text = full_text
    if len(inject_text) > INJECT_MAX_CHARS:
        inject_text = inject_text[:INJECT_MAX_CHARS] + "\n\n... [inject-clipped]"

    return NormalizedAttachment(
        filename=filename or "unnamed",
        ext=ext or ".txt",
        text=inject_text,
        full_text=full_text,
        was_truncated=was_truncated,
        attach_to_persona=attach_to_persona,
        note="",
    )


def format_attach_block(a: NormalizedAttachment) -> str:
    """Форматирует attach как блок для инъекции в system prompt."""
    header = f"## Прикреплённый пользователем материал\n"
    header += f"Файл: `{a.filename}`"
    if a.attach_to_persona:
        header += f" (для голоса `{a.attach_to_persona}`)"
    if a.was_truncated:
        header += " · **truncated**"
    return f"{header}\n\n```\n{a.text}\n```\n"

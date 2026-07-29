"""Minimal built-in web UI for running the council from a browser."""
from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import yaml

from .adapters.units_of_content_md import parse_md_units_text
from .ingress import parse_envelope
from .pipeline import Pipeline
from .schemas import to_plain


_HTML = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Zarathustra Runner</title>
  <style>
    :root {
      --bg: #f4efe6;
      --ink: #1e1b18;
      --panel: #fffaf2;
      --line: #d8c8b1;
      --accent: #8d3f1f;
      --accent-2: #29524a;
      --muted: #6b6259;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, #fff7e8 0, transparent 28rem),
        linear-gradient(180deg, #efe3d0 0%, var(--bg) 100%);
    }
    main {
      max-width: 1100px;
      margin: 0 auto;
      padding: 32px 20px 56px;
    }
    h1 {
      margin: 0 0 8px;
      font-size: clamp(2rem, 4vw, 3.6rem);
      line-height: 0.95;
      letter-spacing: -0.03em;
    }
    .sub {
      color: var(--muted);
      margin-bottom: 28px;
      max-width: 56rem;
    }
    .grid {
      display: grid;
      grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
      gap: 20px;
    }
    .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 10px 30px rgba(53, 35, 16, 0.06);
    }
    label {
      display: block;
      margin-bottom: 8px;
      font-size: 0.95rem;
      color: var(--muted);
    }
    textarea {
      width: 100%;
      min-height: 360px;
      border-radius: 14px;
      border: 1px solid var(--line);
      padding: 14px;
      resize: vertical;
      font: inherit;
      background: #fffdf8;
      color: var(--ink);
    }
    select, button, input[type=file] {
      font: inherit;
    }
    .controls {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 14px;
    }
    .controls .full {
      grid-column: 1 / -1;
    }
    select {
      width: 100%;
      padding: 10px 12px;
      border-radius: 12px;
      border: 1px solid var(--line);
      background: #fffdf8;
    }
    .actions {
      display: flex;
      gap: 12px;
      align-items: center;
      margin-top: 14px;
      flex-wrap: wrap;
    }
    button {
      background: linear-gradient(135deg, var(--accent), #b25526);
      color: white;
      border: 0;
      border-radius: 999px;
      padding: 12px 18px;
      cursor: pointer;
    }
    button.secondary {
      background: linear-gradient(135deg, var(--accent-2), #3d7469);
    }
    .hint, .status {
      color: var(--muted);
      font-size: 0.95rem;
    }
    pre {
      white-space: pre-wrap;
      word-break: break-word;
      background: #fffdf8;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      min-height: 420px;
      max-height: 70vh;
      overflow: auto;
      margin: 0;
    }
    .pill {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      background: #f2e7d8;
      color: var(--accent);
      margin-right: 8px;
      margin-bottom: 8px;
      font-size: 0.88rem;
    }
    @media (max-width: 900px) {
      .grid { grid-template-columns: 1fr; }
      textarea { min-height: 260px; }
    }
  </style>
</head>
<body>
  <main>
    <h1>Zarathustra Runner</h1>
    <div class="sub">Вставь текст или загрузи файл. `raw text` идёт в legacy-вход, `auto-slice` режет сырой поток в raw_stream units, `semantic-units` принимает canonical JSON/YAML envelope или md units pack.</div>
    <div class="grid">
      <section class="card">
        <div class="controls">
          <div>
            <label for="inputMode">Тип входа</label>
            <select id="inputMode">
              <option value="raw" selected>raw text</option>
              <option value="auto-slice">auto-slice raw_stream</option>
              <option value="semantic-units">semantic-units</option>
            </select>
          </div>
          <div>
            <label for="mode">Режим глубины</label>
            <select id="mode">
              <option value="fast">fast</option>
              <option value="deep">deep</option>
            </select>
          </div>
          <div>
            <label for="critique">Critique Regime</label>
            <select id="critique">
              <option value="gentle">gentle</option>
              <option value="balanced" selected>balanced</option>
              <option value="hard">hard</option>
            </select>
          </div>
          <div>
            <label for="variation">Variation Regime</label>
            <select id="variation">
              <option value="strict">strict</option>
              <option value="normal" selected>normal</option>
              <option value="jazz">jazz</option>
            </select>
          </div>
          <div>
            <label for="preset">Пресет</label>
            <select id="preset">
              <option value="" selected>по умолчанию</option>
            </select>
          </div>
          <div>
            <label for="modelPick">Модель (bypass preset)</label>
            <select id="modelPick">
              <option value="" selected>из пресета</option>
            </select>
          </div>
          <div>
            <label for="maxTokens">max_tokens</label>
            <input id="maxTokens" type="number" min="128" max="8192" step="256" placeholder="из конфига"
                   style="width: 100%; padding: 6px 8px; border-radius: 10px; border: 1px solid var(--line); background: #fff;">
          </div>
          <div>
            <label for="outFmt">Формат ответа</label>
            <select id="outFmt">
              <option value="text" selected>text (речь Заратустры)</option>
              <option value="json">json (структура)</option>
            </select>
          </div>
          <div>
            <label for="detailLvl">Детализация</label>
            <select id="detailLvl">
              <option value="only_result" selected>только результат</option>
              <option value="with_turns">результат + ходы совета</option>
            </select>
          </div>
          <div>
            <label for="debug">Debug</label>
            <select id="debug">
              <option value="false" selected>без trace</option>
              <option value="true">с trace</option>
            </select>
          </div>
          <div class="full">
            <label for="fileInput">Файл</label>
            <input id="fileInput" type="file" accept=".txt,.md,.json,.yaml,.yml,.text">
          </div>
        </div>
        <label for="inputText">Текст</label>
        <textarea id="inputText" placeholder="Вставь расшифровку, вопрос, canonical semantic-units envelope, md units pack или другой материал..."></textarea>
        <div class="actions">
          <button id="runBtn" type="button">Запустить совет</button>
          <button class="secondary" id="clearBtn" type="button">Очистить</button>
          <span class="status" id="status">Готово.</span>
        </div>
      </section>
      <section class="card">
        <div>
          <span class="pill">text or file</span>
          <span class="pill">raw / auto-slice / semantic-units</span>
          <span class="pill">critique regime</span>
          <span class="pill">variation regime</span>
        </div>
        <label for="output">Результат</label>
        <pre id="output">Здесь появится JSON результата.</pre>
        <div class="hint">Файл не отправляется отдельно: браузер читает его локально и подставляет содержимое в текстовое поле. Для `semantic-units` можно вставить canonical JSON/YAML envelope или md units pack.</div>
      </section>
    </div>
  </main>
  <script>
    const input = document.getElementById('inputText');
    const fileInput = document.getElementById('fileInput');
    const output = document.getElementById('output');
    const statusEl = document.getElementById('status');
    const runBtn = document.getElementById('runBtn');
    const clearBtn = document.getElementById('clearBtn');

    fileInput.addEventListener('change', async (event) => {
      const file = event.target.files && event.target.files[0];
      if (!file) return;
      const text = await file.text();
      input.value = text;
      statusEl.textContent = `Загружен файл: ${file.name}`;
    });

    clearBtn.addEventListener('click', () => {
      input.value = '';
      output.textContent = 'Здесь появится JSON результата.';
      statusEl.textContent = 'Очищено.';
      fileInput.value = '';
    });

    (async () => {
      try {
        const r = await fetch('api/presets');
        const j = await r.json();
        const sel = document.getElementById('preset');
        for (const p of (j.presets || [])) {
          const opt = document.createElement('option');
          opt.value = p.name;
          opt.textContent = p.label || p.name;
          sel.appendChild(opt);
        }
      } catch(e) {}
      try {
        const r2 = await fetch('api/models');
        const j2 = await r2.json();
        const sel2 = document.getElementById('modelPick');
        // wipe placeholder — server sends {id:"", label:"по умолчанию (из пресета)"} тоже
        sel2.innerHTML = '';
        for (const m of (j2.models || [])) {
          const opt = document.createElement('option');
          opt.value = m.id || '';
          opt.textContent = m.label || m.id || '(default)';
          sel2.appendChild(opt);
        }
      } catch(e) {}
    })();

    runBtn.addEventListener('click', async () => {
      const text = input.value.trim();
      if (!text) {
        statusEl.textContent = 'Нужен текст или файл.';
        return;
      }
      runBtn.disabled = true;
      const t0 = Date.now();
      statusEl.textContent = 'Идёт запрос к LLM…';
      // Заметный overlay c прогрессом времени
      output.textContent = '⏳ Совет собирается…\\n\\nЖивой запрос к LLM: обычно 60–180 секунд.\\nПодожди, не нажимай ещё раз.\\n\\n(смотри статус в углу карточки — там таймер)';
      const timer = setInterval(() => {
        const dt = Math.floor((Date.now() - t0) / 1000);
        statusEl.textContent = `Идёт запрос к LLM… ${dt}s`;
      }, 1000);
      try {
        const response = await fetch('api/run', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            text,
            input_mode: document.getElementById('inputMode').value,
            mode: document.getElementById('mode').value,
            critique_regime: document.getElementById('critique').value,
            variation_regime: document.getElementById('variation').value,
            preset: document.getElementById('preset').value,
            model: document.getElementById('modelPick').value,
            max_tokens: (document.getElementById('maxTokens').value || null),
            output_format: document.getElementById('outFmt').value,
            detail: document.getElementById('detailLvl').value,
            debug: document.getElementById('debug').value === 'true'
          })
        });
        const payload = await response.json();
        // text-mode: показать body как plain text, meta ниже;
        // json-mode: JSON.stringify как раньше.
        if (payload && payload.format === 'text' && payload.body) {
          output.textContent = payload.body + '\\n\\n--- meta ---\\n' + JSON.stringify(payload.meta || {}, null, 2);
        } else {
          output.textContent = JSON.stringify(payload, null, 2);
        }
        const dt = Math.floor((Date.now() - t0) / 1000);
        statusEl.textContent = response.ok
          ? `Готово за ${dt}s.`
          : `Ошибка HTTP ${response.status} за ${dt}s.`;
      } catch (error) {
        output.textContent = String(error);
        statusEl.textContent = 'Ошибка сети (проверь соединение / DevTools → Network).';
      } finally {
        clearInterval(timer);
        runBtn.disabled = false;
      }
    });
  </script>
</body>
</html>
"""


def run_web_request(
    text: str,
    *,
    input_mode: str = "raw",
    mode: str = "fast",
    critique_regime: str = "balanced",
    variation_regime: str = "normal",
    debug: bool = False,
    preset: str | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
    output_format: str = "json",    # "json" | "text"
    detail: str = "with_turns",     # "only_result" | "with_turns"
) -> dict[str, Any]:
    pipe = Pipeline(
        preset_override=preset or None,
        model_override=model or None,
        max_tokens_override=max_tokens if (max_tokens and max_tokens > 0) else None,
    )
    resolved_input_mode = input_mode
    ingress_mode = "legacy_raw"

    if input_mode == "semantic-units":
        result = _run_semantic_units_request(
            pipe,
            text=text,
            mode=mode,
            critique_regime=critique_regime,
            variation_regime=variation_regime,
        )
        ingress_mode = "semantic_units"
    elif input_mode == "auto-slice":
        envelope = parse_envelope({
            "mode": "raw_stream",
            "run_id": "web-ui-raw-stream",
            "content": text,
            "metadata": {"source": "web_ui"},
        })
        result = pipe.run_from_envelope(
            envelope,
            mode=mode,
            critique_regime=critique_regime,
            variation_regime=variation_regime,
        )
        ingress_mode = "raw_stream"
    elif input_mode == "units":
        pack = parse_md_units_text(text)
        result = pipe.run_from_units(
            pack,
            mode=mode,
            critique_regime=critique_regime,
            variation_regime=variation_regime,
        )
        resolved_input_mode = "semantic-units"
        ingress_mode = "md_units_pack"
    else:
        result = pipe.run(
            text=text,
            mode=mode,
            critique_regime=critique_regime,
            variation_regime=variation_regime,
        )

    payload: dict[str, Any] = {
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
        "regimes": {
            "critique_regime": critique_regime,
            "variation_regime": variation_regime,
        },
        "input_mode": resolved_input_mode,
        "ingress_mode": ingress_mode,
        "preset": pipe.preset_override,
        "model": pipe.model_override,
        "max_tokens": pipe.max_tokens_override,
        "closing_speech": (
            (result.run_state.completion.closing_speech or "").strip()
            if result.run_state.completion else ""
        ),
    }
    if detail == "with_turns" or debug:
        payload["turns"] = [
            {
                "turn_index": t.turn_index,
                "persona_id": t.persona_id,
                "operation": t.operation,
                "utterance": t.utterance,
                "confidence": t.confidence,
                "model": t.model_name,
                "provider": t.model_provider,
            }
            for t in result.run_state.turns
        ]
    if debug:
        payload["situation"] = to_plain(result.run_state.situation)
        payload["argument_map"] = to_plain(result.run_state.argument_map)

    # Text-format rendering: короче ответ, приоритет closing_speech.
    if output_format == "text":
        payload = _render_text_payload(payload, detail=detail)
    return payload


def _render_text_payload(payload: dict[str, Any], *, detail: str) -> dict[str, Any]:
    """Свернуть JSON-структуру в лаконичный text-документ.

    Возвращает `{format: "text", body: "...", meta: {...}}` — тонкая мета
    остаётся, но всё остальное — plain text (закрывающая речь Заратустры
    + опционально ходы голосов).
    """
    lines: list[str] = []
    c = payload.get("completion") or {}
    speech = (payload.get("closing_speech") or "").strip()
    form = c.get("form") or "?"

    lines.append("⚡ Заратустра")
    lines.append("")
    if speech:
        lines.append(speech)
    else:
        lines.append(
            "(mock-режим или пустой ответ модели — закрывающая речь недоступна; "
            "переключи preset/model для полного текста)"
        )
    lines.append("")
    lines.append(f"[форма завершения: {form} · voices: {', '.join(payload.get('voices_used') or []) or '—'}]")

    if detail == "with_turns":
        turns = payload.get("turns") or []
        if turns:
            lines.append("")
            lines.append("—" * 3 + " ход совета " + "—" * 3)
            for t in turns:
                lines.append("")
                lines.append(f"[{t.get('persona_id')} · {t.get('operation')}]")
                lines.append((t.get("utterance") or "").strip())

    return {
        "format": "text",
        "body": "\n".join(lines),
        "meta": {
            "run_id": payload.get("run_id"),
            "mode": payload.get("mode"),
            "status": payload.get("status"),
            "form": form,
            "voices_used": payload.get("voices_used"),
            "turn_count": payload.get("turn_count"),
            "preset": payload.get("preset"),
            "model": payload.get("model"),
            "max_tokens": payload.get("max_tokens"),
            "security_events": payload.get("security_events"),
            "trace_dir": payload.get("trace_dir"),
            "errors": payload.get("errors"),
        },
    }


def _run_semantic_units_request(
    pipe: Pipeline,
    *,
    text: str,
    mode: str,
    critique_regime: str,
    variation_regime: str,
):
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("mode:"):
        parsed = yaml.safe_load(text)
        if not isinstance(parsed, dict):
            raise ValueError("semantic-units input must decode to an object")
        envelope = parse_envelope(parsed)
        return pipe.run_from_envelope(
            envelope,
            mode=mode,
            critique_regime=critique_regime,
            variation_regime=variation_regime,
        )
    pack = parse_md_units_text(text)
    return pipe.run_from_units(
        pack,
        mode=mode,
        critique_regime=critique_regime,
        variation_regime=variation_regime,
    )


class _WebUIHandler(BaseHTTPRequestHandler):
    server_version = "ZarathustraWebUI/0.1"

    def do_GET(self) -> None:  # noqa: N802
        # Strip query-string: /?nocache=... должен матчить корневые пути
        path_only = self.path.split("?", 1)[0]
        # Rewrite so все ниже проверки видят чистый path
        self.path = path_only
        if self.path in {"/api/presets", "/presets"}:
            from .config import load_config
            cfg = load_config()
            self._send_json({"presets": cfg.presets()})
            return
        if self.path in {"/api/models", "/models"}:
            from .config import load_config
            cfg = load_config()
            self._send_json({"models": cfg.model_menu()})
            return
        if self.path not in {"/", "/index.html"}:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        body = _HTML.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # Prevent browser/proxy caching of the UI — иначе после deploy
        # пользователь получает старую HTML с несовпадающими id, script не
        # находит нужные элементы, handler не привязывается, кнопка "мертва".
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        if self.path not in {"/api/run", "/run"}:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            data = json.loads(raw.decode("utf-8"))
            text = (data.get("text") or "").strip()
            if not text:
                self._send_json({"error": "text is required"}, status=HTTPStatus.BAD_REQUEST)
                return
            payload = run_web_request(
                text,
                input_mode=data.get("input_mode") or "raw",
                mode=data.get("mode") or "fast",
                critique_regime=data.get("critique_regime") or "balanced",
                variation_regime=data.get("variation_regime") or "normal",
                debug=bool(data.get("debug")),
                preset=(data.get("preset") or None),
                model=(data.get("model") or None),
                max_tokens=(int(data["max_tokens"]) if data.get("max_tokens") else None),
                output_format=(data.get("output_format") or "json"),
                detail=(data.get("detail") or "with_turns"),
            )
            self._send_json(payload)
        except Exception as exc:  # pragma: no cover - defensive boundary
            self._send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve_web_ui(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), _WebUIHandler)
    print(f"Zarathustra web UI running on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

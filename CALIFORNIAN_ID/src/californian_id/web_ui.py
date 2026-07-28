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
            <label for="debug">Вывод</label>
            <select id="debug">
              <option value="false" selected>обычный</option>
              <option value="true">с debug trace</option>
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
          <button id="runBtn">Запустить совет</button>
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

    runBtn.addEventListener('click', async () => {
      const text = input.value.trim();
      if (!text) {
        statusEl.textContent = 'Нужен текст или файл.';
        return;
      }
      runBtn.disabled = true;
      statusEl.textContent = 'Считаю...';
      output.textContent = 'Выполняется запуск...';
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
            debug: document.getElementById('debug').value === 'true'
          })
        });
        const payload = await response.json();
        output.textContent = JSON.stringify(payload, null, 2);
        statusEl.textContent = response.ok ? 'Готово.' : 'Ошибка запуска.';
      } catch (error) {
        output.textContent = String(error);
        statusEl.textContent = 'Ошибка сети.';
      } finally {
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
) -> dict[str, Any]:
    pipe = Pipeline()
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
    }
    if debug:
        payload["turns"] = [to_plain(t) for t in result.run_state.turns]
        payload["situation"] = to_plain(result.run_state.situation)
        payload["argument_map"] = to_plain(result.run_state.argument_map)
    return payload


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
        if self.path not in {"/", "/index.html"}:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        body = _HTML.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
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

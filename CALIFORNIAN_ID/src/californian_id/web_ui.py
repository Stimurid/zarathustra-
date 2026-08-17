"""Minimal built-in web UI for running the council from a browser."""
from __future__ import annotations

import json
import os
import secrets
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import yaml

from .adapters.units_of_content_md import parse_md_units_text
from .config import load_config
from .ingress import envelope_to_unit_pack, parse_envelope
from .models import Message, build_client
from .persona_layer import CouncilRun, PersonaCard, PersonaCouncilRuntime
from .pipeline import Pipeline
from . import prompt_assets
from .regimes import CRITIQUE_REGIMES, VARIATION_REGIMES
from .schemas import UnitPack, to_plain


LAYER_CALIFORNIAN_ID = "californian_id"
LAYER_PERSONA = "persona_layer"
SUPPORTED_LAYERS = {LAYER_CALIFORNIAN_ID, LAYER_PERSONA}
GROUNDING_MODES = {"strict_card", "balanced", "freer_synthesis"}
ASSEMBLY_MODES = {"synthesis", "verdict", "dissent_forward", "diagnostic", "projective", "roast"}
COUNCIL_SPANS = {"auto", "force_pair", "force_triangular", "force_full_council"}
COMPAT_API_KEY_ENV = "TINKUY_COMPAT_API_KEY"
COMPAT_BASE_URL = "https://tinkuy.mindkampf.ru/v1"
COMPAT_MODEL_ALIASES: dict[str, dict[str, Any]] = {
    "tinkuy-persona-fast": {
        "runtime_layer": LAYER_PERSONA,
        "mode": "fast",
        "preset": "fast",
        "assembly_mode": "synthesis",
        "council_span": "auto",
    },
    "tinkuy-persona-deep": {
        "runtime_layer": LAYER_PERSONA,
        "mode": "deep",
        "preset": "reasoning",
        "assembly_mode": "synthesis",
        "council_span": "auto",
    },
    "tinkuy-persona-roast": {
        "runtime_layer": LAYER_PERSONA,
        "mode": "fast",
        "preset": "reasoning",
        "assembly_mode": "roast",
        "council_span": "auto",
    },
    "tinkuy-calif-fast": {
        "runtime_layer": LAYER_CALIFORNIAN_ID,
        "mode": "fast",
        "preset": "fast",
        "assembly_mode": "synthesis",
        "council_span": "auto",
    },
    "tinkuy-calif-deep": {
        "runtime_layer": LAYER_CALIFORNIAN_ID,
        "mode": "deep",
        "preset": "reasoning",
        "assembly_mode": "synthesis",
        "council_span": "auto",
    },
}


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
    select, button, input[type=file], input[type=number] {
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
    select, input[type=number] {
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
    .access-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 10px;
      margin: 12px 0 16px;
    }
    .copy-row {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 8px;
      align-items: center;
    }
    input[readonly] {
      width: 100%;
      padding: 10px 12px;
      border-radius: 12px;
      border: 1px solid var(--line);
      background: #fffdf8;
      color: var(--ink);
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
    <div class="sub">Вставь текст или загрузи файл. `raw text` идет как прямой вход, `auto-slice` режет сырой поток во встроенные raw_stream units, `semantic-units` принимает canonical JSON/YAML envelope или md units pack. Переключатель `Council Layer` выбирает между текущим CALIFORNIAN_ID runtime и persona layer с семью головами и NEMO-8.</div>
    <div class="grid">
      <section class="card">
        <div class="controls">
          <div>
            <label for="councilLayer">Council Layer</label>
            <select id="councilLayer">
              <option value="persona_layer" selected>persona layer (7 heads + NEMO-8)</option>
              <option value="californian_id">californian_id runtime</option>
            </select>
          </div>
          <div>
            <label for="inputMode">Тип входа</label>
            <select id="inputMode">
              <option value="raw" selected>raw text</option>
              <option value="auto-slice">auto-slice raw_stream</option>
              <option value="raw+fabric">raw+fabric (Пик 5)</option>
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
            <label for="closingGenre">Жанр закрытия (7.2)</label>
            <select id="closingGenre">
              <option value="">— default —</option>
            </select>
          </div>
          <div>
            <label for="dialogueProtocol">Диалог-протокол (7.4)</label>
            <select id="dialogueProtocol">
              <option value="">— default —</option>
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
            <label for="groundingMode">Grounding Mode</label>
            <select id="groundingMode">
              <option value="strict_card">strict card</option>
              <option value="balanced" selected>balanced</option>
              <option value="freer_synthesis">freer synthesis</option>
            </select>
          </div>
          <div>
            <label for="assemblyMode">Assembly Mode</label>
            <select id="assemblyMode">
              <option value="synthesis" selected>synthesis</option>
              <option value="verdict">verdict</option>
              <option value="dissent_forward">dissent-forward</option>
              <option value="diagnostic">diagnostic</option>
              <option value="projective">projective</option>
              <option value="roast">roast</option>
            </select>
          </div>
          <div>
            <label for="councilSpan">Council Span</label>
            <select id="councilSpan">
              <option value="auto" selected>auto</option>
              <option value="force_pair">force pair</option>
              <option value="force_triangular">force triangular</option>
              <option value="force_full_council">force full council</option>
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
              <option value="" selected>по умолчанию (из пресета)</option>
            </select>
          </div>
          <div>
            <label for="voiceMaxTokens">Токены голосов</label>
            <input id="voiceMaxTokens" type="number" min="128" max="8192" step="256" placeholder="из конфига">
          </div>
          <div>
            <label for="closingMaxTokens">Токены Заратустры</label>
            <input id="closingMaxTokens" type="number" min="128" max="8192" step="256" placeholder="из конфига">
          </div>
          <div>
            <label for="maxTurns">Max Turns</label>
            <input id="maxTurns" type="number" min="1" max="24" step="1" placeholder="из runtime mode">
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
            <label for="showOrchestrationTrace">Show orchestration trace</label>
            <select id="showOrchestrationTrace">
              <option value="false" selected>hide orchestration trace</option>
              <option value="true">show orchestration trace</option>
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
          <label style="margin-left:1em;font-size:0.9em;">
            Workspace: <input type="text" id="workspaceId" value="default"
              style="width:8em;padding:2px;font-family:monospace;" />
          </label>
          <label style="margin-left:1em;font-size:0.9em;">
            <input type="checkbox" id="liveStream" /> Live (SSE, 6.B)
          </label>
          <label style="margin-left:0.5em;font-size:0.9em;">
            <input type="checkbox" id="asyncMode" /> Async (6.3)
          </label>
          <span class="status" id="status">Готово.</span>
        </div>
        <div class="actions" style="margin-top:0.5em;" id="hilBar">
          <span style="color:var(--muted);font-size:0.85em;">HIL (B-5.5 Веха 1):</span>
          <button class="secondary" id="pauseBtn" type="button" disabled>⏸ Pause</button>
          <button class="secondary" id="resumeBtn" type="button" disabled>▶ Resume</button>
          <button class="secondary" id="cancelBtn" type="button" disabled>⏹ Cancel</button>
          <span class="hint" id="hilStatus" style="margin-left:1em;"></span>
        </div>
        <div class="actions" style="margin-top:0.5em;">
          <button class="secondary" id="historyBtn" type="button">📜 История ранов</button>
          <span id="historyInfo" class="hint"></span>
        </div>
        <div id="historyPanel" style="display:none;margin-top:0.5em;max-height:220px;overflow:auto;border:1px solid #333;padding:0.5em;font-size:0.85em;font-family:monospace;"></div>
      </section>
      <section class="card">
        <div>
          <span class="pill" id="pillInput">input: raw text</span>
          <span class="pill" id="pillLayer">layer: persona layer</span>
          <span class="pill" id="pillCritique">critique: balanced</span>
          <span class="pill" id="pillVariation">variation: normal</span>
          <span class="pill" id="pillSpan">span: auto</span>
        </div>
        <label for="output">Результат</label>
        <pre id="output">Здесь появится результат.</pre>
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
    const headerSub = document.querySelector('.sub');

    if (headerSub) {
      headerSub.textContent = 'Вставь текст или загрузи файл. `raw text` отправляет материал как есть, `auto-slice` режет сырой поток во встроенные raw_stream units, `semantic-units` принимает canonical JSON/YAML envelope, md units pack или близкую аналитическую разметку и при необходимости адаптирует ее через LLM. `Council Layer` переключает между persona layer и CALIFORNIAN_ID runtime, `Council Span` управляет числом голосов в persona layer, `Assembly Mode` задает тип финальной сборки Заратустры, а `Show orchestration trace` показывает маршрут совета. Блок `API Access` выдает отдельный Tinkuy-compatible ключ и model aliases для `https://tinkuy.mindkampf.ru/v1`.';
    }

    function copyText(value) {
      if (!value) return;
      navigator.clipboard.writeText(value).catch(() => {});
    }

    function mountApiAccess(payload) {
      const outputLabel = document.querySelector('label[for="output"]');
      if (!outputLabel) return;
      const block = document.createElement('div');
      block.innerHTML = `
        <label>API Access</label>
        <div class="access-grid">
          <div>
            <label for="apiAccessMode">Access Mode</label>
            <input id="apiAccessMode" type="text" readonly>
          </div>
          <div>
            <label for="apiBaseUrl">Base URL</label>
            <div class="copy-row">
              <input id="apiBaseUrl" type="text" readonly>
              <button class="secondary" id="copyBaseUrlBtn" type="button">copy</button>
            </div>
          </div>
          <div>
            <label for="apiKeyValue">API Key</label>
            <div class="copy-row">
              <input id="apiKeyValue" type="text" readonly>
              <button class="secondary" id="copyApiKeyBtn" type="button">copy</button>
            </div>
          </div>
          <div>
            <label for="apiModelsValue">Suggested Models</label>
            <div class="copy-row">
              <input id="apiModelsValue" type="text" readonly>
              <button class="secondary" id="copyModelsBtn" type="button">copy</button>
            </div>
          </div>
        </div>
      `;
      outputLabel.parentNode.insertBefore(block, outputLabel);
      document.getElementById('apiAccessMode').value = payload.access_mode || '';
      document.getElementById('apiBaseUrl').value = payload.base_url || '';
      document.getElementById('apiKeyValue').value = payload.api_key || '';
      document.getElementById('apiModelsValue').value = (payload.suggested_models || []).join(', ');
      document.getElementById('copyBaseUrlBtn').addEventListener('click', () => copyText(payload.base_url || ''));
      document.getElementById('copyApiKeyBtn').addEventListener('click', () => copyText(payload.api_key || ''));
      document.getElementById('copyModelsBtn').addEventListener('click', () => copyText((payload.suggested_models || []).join(', ')));
    }

    function updateModePills() {
      const inputMode = document.getElementById('inputMode');
      const councilLayer = document.getElementById('councilLayer');
      const critique = document.getElementById('critique');
      const variation = document.getElementById('variation');
      const councilSpan = document.getElementById('councilSpan');
      document.getElementById('pillInput').textContent = `input: ${inputMode.options[inputMode.selectedIndex].text}`;
      document.getElementById('pillLayer').textContent = `layer: ${councilLayer.options[councilLayer.selectedIndex].text}`;
      document.getElementById('pillCritique').textContent = `critique: ${critique.options[critique.selectedIndex].text}`;
      document.getElementById('pillVariation').textContent = `variation: ${variation.options[variation.selectedIndex].text}`;
      document.getElementById('pillSpan').textContent = `span: ${councilSpan.options[councilSpan.selectedIndex].text}`;
    }

    fileInput.addEventListener('change', async (event) => {
      const file = event.target.files && event.target.files[0];
      if (!file) return;
      const text = await file.text();
      input.value = text;
      statusEl.textContent = `Загружен файл: ${file.name}`;
    });

    clearBtn.addEventListener('click', () => {
      input.value = '';
      output.textContent = 'Здесь появится результат.';
      statusEl.textContent = 'Очищено.';
      fileInput.value = '';
    });

    (async () => {
      try {
        const presetsResponse = await fetch('api/presets');
        const presetsPayload = await presetsResponse.json();
        const presetSelect = document.getElementById('preset');
        for (const preset of (presetsPayload.presets || [])) {
          if ((preset.name || '').toLowerCase() === 'mock') continue;
          if ((preset.provider || '').toLowerCase() === 'mock') continue;
          const option = document.createElement('option');
          option.value = preset.name;
          option.textContent = preset.label || preset.name;
          presetSelect.appendChild(option);
        }
      } catch (error) {}
      try {
        const modelsResponse = await fetch('api/models');
        const modelsPayload = await modelsResponse.json();
        const modelSelect = document.getElementById('modelPick');
        modelSelect.innerHTML = '<option value="" selected>по умолчанию (из пресета)</option>';
        for (const model of (modelsPayload.models || [])) {
          if ((model.id || '').toLowerCase() === 'mock') continue;
          const option = document.createElement('option');
          option.value = model.id || '';
          option.textContent = model.label || model.id || '(default)';
          modelSelect.appendChild(option);
        }
      } catch (error) {}
      try {
        const accessResponse = await fetch('api/access');
        const accessPayload = await accessResponse.json();
        mountApiAccess(accessPayload);
      } catch (error) {}
      updateModePills();
    })();

    for (const id of ['inputMode', 'councilLayer', 'critique', 'variation', 'councilSpan']) {
      document.getElementById(id).addEventListener('change', updateModePills);
    }

    function currentWorkspace() {
      return (document.getElementById('workspaceId').value || 'default').trim() || 'default';
    }

    async function loadDropdowns() {
      try {
        const g = await (await fetch('api/genres')).json();
        const gs = document.getElementById('closingGenre');
        (g.genres || []).forEach(x => {
          const o = document.createElement('option');
          o.value = x.genre_id; o.textContent = x.display_name;
          gs.appendChild(o);
        });
        if (g.default) gs.value = ''; // keep — using default
        const p = await (await fetch('api/protocols')).json();
        const ps = document.getElementById('dialogueProtocol');
        (p.protocols || []).forEach(x => {
          const o = document.createElement('option');
          o.value = x.protocol_id; o.textContent = x.display_name;
          ps.appendChild(o);
        });
      } catch (e) { /* stay silent, dropdowns show only defaults */ }
    }
    loadDropdowns();

    function buildRequestBody(text) {
      return {
        text,
        workspace_id: currentWorkspace(),
        closing_genre: document.getElementById('closingGenre').value || null,
        dialogue_protocol: document.getElementById('dialogueProtocol').value || null,
        runtime_layer: document.getElementById('councilLayer').value,
        input_mode: document.getElementById('inputMode').value,
        mode: document.getElementById('mode').value,
        critique_regime: document.getElementById('critique').value,
        variation_regime: document.getElementById('variation').value,
        grounding_mode: document.getElementById('groundingMode').value,
        assembly_mode: document.getElementById('assemblyMode').value,
        council_span: document.getElementById('councilSpan').value,
        preset: document.getElementById('preset').value,
        model: document.getElementById('modelPick').value,
        voice_max_tokens: document.getElementById('voiceMaxTokens').value || null,
        closing_max_tokens: document.getElementById('closingMaxTokens').value || null,
        max_turns: document.getElementById('maxTurns').value || null,
        output_format: document.getElementById('outFmt').value,
        detail: document.getElementById('detailLvl').value,
        show_orchestration_trace: document.getElementById('showOrchestrationTrace').value === 'true',
        debug: document.getElementById('debug').value === 'true'
      };
    }

    async function runAsync(text, t0, timer) {
      const resp = await fetch('api/run/async', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify(buildRequestBody(text))
      });
      const enq = await resp.json();
      if (!resp.ok) throw new Error('async submit: HTTP ' + resp.status);
      const rid = enq.run_id;
      output.textContent = 'Async job enqueued.\\nrun_id: ' + rid + '\\n\\nPolling status...';
      const ws = currentWorkspace();
      while (true) {
        await new Promise(r => setTimeout(r, 2000));
        const s = await fetch('api/run/' + rid + '/result?workspace=' + encodeURIComponent(ws));
        if (s.status === 202) {
          const st = await s.json();
          const dt = Math.floor((Date.now() - t0)/1000);
          statusEl.textContent = `Async: ${st.status} · ${dt}s`;
          continue;
        }
        if (!s.ok) throw new Error('async poll: HTTP ' + s.status);
        const payload = await s.json();
        if (payload.error) {
          output.textContent = 'ERROR:\\n' + payload.error + '\\n\\n' + (payload.traceback || '');
          statusEl.textContent = 'Async: ERROR';
          return;
        }
        if (payload && payload.format === 'text' && payload.body) {
          output.textContent = payload.body;
        } else {
          output.textContent = JSON.stringify(payload, null, 2);
        }
        const dt = Math.floor((Date.now() - t0)/1000);
        statusEl.textContent = `Async готово за ${dt}s.`;
        return;
      }
    }

    async function refreshHistory() {
      const ws = currentWorkspace();
      const panel = document.getElementById('historyPanel');
      const info = document.getElementById('historyInfo');
      try {
        const resp = await fetch('api/runs?workspace=' + encodeURIComponent(ws) + '&limit=50');
        const data = await resp.json();
        panel.style.display = 'block';
        if (!data.runs || data.runs.length === 0) {
          panel.innerHTML = '<i>Пусто. Workspace: ' + ws + '</i>';
          info.textContent = '';
          return;
        }
        info.textContent = data.runs.length + ' runs в workspace ' + ws;
        const rows = data.runs.map(r => {
          const badge = r.status === 'COMPLETED' ? '✓' : (r.status === 'RUNNING' ? '⏳' : '⚠');
          const summary = (r.input_summary || '').replace(/</g,'&lt;').slice(0,80);
          return `<div style="margin-bottom:4px;">
            <a href="#" data-rid="${r.run_id}" class="load-run" style="color:#79c;text-decoration:none;">${badge} ${r.run_id}</a>
            · <b>${r.completion_form || r.status}</b> · turns=${r.turn_count}
            · ${r.mode}/${r.input_mode || '?'}
            · ${r.created_at ? r.created_at.slice(0,19).replace('T',' ') : ''}
            <br/><span style="color:#888;padding-left:1em;">${summary}</span>
          </div>`;
        });
        panel.innerHTML = rows.join('');
        panel.querySelectorAll('.load-run').forEach(a => {
          a.addEventListener('click', async (ev) => {
            ev.preventDefault();
            const rid = a.getAttribute('data-rid');
            statusEl.textContent = 'Загрузка ' + rid + '...';
            const r = await fetch('api/run/' + rid + '/result?workspace=' + encodeURIComponent(ws));
            const payload = await r.json();
            if (r.status === 202) {
              output.textContent = 'Этот ран ещё RUNNING. Попробуй позже.';
            } else if (payload && payload.format === 'text' && payload.body) {
              output.textContent = payload.body;
            } else {
              output.textContent = JSON.stringify(payload, null, 2);
            }
            statusEl.textContent = 'Загружен ' + rid;
          });
        });
      } catch (e) {
        panel.style.display = 'block';
        panel.innerHTML = '<i>Ошибка: ' + String(e) + '</i>';
      }
    }
    document.getElementById('historyBtn').addEventListener('click', refreshHistory);

    // B-5.5 Веха 1 — HIL run control
    let currentLiveRunId = null;
    const pauseBtn = document.getElementById('pauseBtn');
    const resumeBtn = document.getElementById('resumeBtn');
    const cancelBtn = document.getElementById('cancelBtn');
    const hilStatus = document.getElementById('hilStatus');

    function setHilEnabled(enabled, runId) {
      currentLiveRunId = enabled ? runId : null;
      pauseBtn.disabled = !enabled;
      resumeBtn.disabled = !enabled;
      cancelBtn.disabled = !enabled;
      hilStatus.textContent = enabled ? ('run: ' + runId) : '';
    }

    async function sendIntervention(kind, payload) {
      if (!currentLiveRunId) return;
      try {
        const r = await fetch('api/run/' + currentLiveRunId + '/intervention', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({kind, payload: payload || {}})
        });
        const d = await r.json();
        if (!r.ok) {
          hilStatus.textContent = 'Ошибка: ' + (d.error || 'HTTP ' + r.status);
        } else {
          hilStatus.textContent = kind + ': accepted · state ' + (d.run_state?.state || '?');
        }
      } catch (e) {
        hilStatus.textContent = 'Ошибка сети: ' + String(e);
      }
    }

    pauseBtn.addEventListener('click', () => sendIntervention('pause'));
    resumeBtn.addEventListener('click', () => sendIntervention('resume'));
    cancelBtn.addEventListener('click', () => sendIntervention('cancel', {reason: 'user_cancel'}));

    async function runStreamed(text, t0, timer) {
      output.textContent = '';
      const response = await fetch('api/run/stream', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(buildRequestBody(text))
      });
      if (!response.ok || !response.body) {
        throw new Error('HTTP ' + response.status);
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let closingText = '';
      let finalPayload = null;
      let turnCount = 0;
      const appendLine = (s) => { output.textContent += s + '\\n'; };
      while (true) {
        const {value, done} = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, {stream: true});
        let idx;
        while ((idx = buffer.indexOf('\\n\\n')) >= 0) {
          const chunk = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          for (const line of chunk.split('\\n')) {
            if (!line.startsWith('data:')) continue;
            let evt;
            try { evt = JSON.parse(line.slice(5).trim()); }
            catch (e) { continue; }
            const k = evt.kind;
            const dt = Math.floor((Date.now() - t0) / 1000);
            statusEl.textContent = `Live: ${k} · ${dt}s`;
            if (k === 'run_started') {
              appendLine('=== run ' + evt.run_id + ' (workspace: ' + evt.workspace_id + ') ===');
              setHilEnabled(true, evt.run_id);
            } else if (k === 'paused') {
              appendLine('⏸ paused at turn ' + evt.at_turn_index + ' (reason: ' + evt.reason + ')');
            } else if (k === 'resumed') {
              appendLine('▶ resumed at turn ' + evt.at_turn_index);
            } else if (k === 'cancelled') {
              appendLine('⏹ cancelled at turn ' + evt.at_turn_index + ' (' + evt.reason + ')');
            } else if (k === 'checkpoint_timeout') {
              appendLine('⚠ checkpoint timeout: ' + evt.note);
            } else if (k === 'situation_reading_done') {
              appendLine('  situation: topic=' + JSON.stringify(evt.topic) + ' genre=' + evt.genre);
            } else if (k === 'cast_selected') {
              appendLine('  cast: ' + evt.personas.join(', ') + '  (max_turns=' + evt.max_turns + ')');
              appendLine('');
            } else if (k === 'turn_completed') {
              turnCount += 1;
              appendLine('[T' + evt.turn_index + ' · ' + evt.persona_id + ' · ' + evt.operation + ']');
              appendLine(evt.utterance);
              appendLine('');
            } else if (k === 'closing_speech_start') {
              appendLine('--- closing speech (form: ' + evt.form + ') ---');
              closingText = '';
            } else if (k === 'closing_speech_delta') {
              closingText += (evt.delta || '');
              // rebuild last line without breaking prior content
              // Cheaper: mark boundary and append delta
              output.textContent += (evt.delta || '');
            } else if (k === 'closing_speech_complete') {
              output.textContent += '\\n\\n(closing_speech: ' + evt.chars + ' chars)\\n';
            } else if (k === 'run_completed') {
              appendLine('=== completed: ' + evt.completion_form + ' · turns=' + evt.turns + ' · reason=' + evt.stopping_reason + ' ===');
            } else if (k === 'final_payload') {
              finalPayload = evt.payload;
            } else if (k === 'error') {
              appendLine('ERROR: ' + evt.error);
            }
          }
        }
      }
      const dt = Math.floor((Date.now() - t0) / 1000);
      statusEl.textContent = `Готово за ${dt}s (live, ${turnCount} turns).`;
      setHilEnabled(false, null);
      if (finalPayload && document.getElementById('debug').value === 'true') {
        output.textContent += '\\n\\n--- full payload ---\\n' + JSON.stringify(finalPayload, null, 2);
      }
    }

    async function runBlocking(text, t0, timer) {
      output.textContent = 'Совет собирается...\\n\\nЖивой запрос к LLM обычно занимает 60-180 секунд.\\nПодожди и не нажимай кнопку повторно.';
      const response = await fetch('api/run', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(buildRequestBody(text))
      });
      const payload = await response.json();
      if (payload && payload.format === 'text' && payload.body) {
        output.textContent = payload.body;
      } else {
        output.textContent = JSON.stringify(payload, null, 2);
      }
      const dt = Math.floor((Date.now() - t0) / 1000);
      statusEl.textContent = response.ok
        ? `Готово за ${dt}s.`
        : `Ошибка HTTP ${response.status} за ${dt}s.`;
    }

    runBtn.addEventListener('click', async () => {
      const text = input.value.trim();
      if (!text) {
        statusEl.textContent = 'Нужен текст или файл.';
        return;
      }
      runBtn.disabled = true;
      const t0 = Date.now();
      statusEl.textContent = 'Идет запрос к runtime...';
      const timer = setInterval(() => {
        const dt = Math.floor((Date.now() - t0) / 1000);
        statusEl.textContent = `Идет запрос к runtime... ${dt}s`;
      }, 1000);
      try {
        const useStream = document.getElementById('liveStream').checked;
        const useAsync = document.getElementById('asyncMode').checked;
        if (useAsync) {
          await runAsync(text, t0, timer);
          await refreshHistory();
        } else if (useStream) {
          await runStreamed(text, t0, timer);
        } else {
          await runBlocking(text, t0, timer);
        }
      } catch (error) {
        output.textContent += '\\n' + String(error);
        statusEl.textContent = 'Ошибка сети или runtime.';
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
    runtime_layer: str = LAYER_PERSONA,
    input_mode: str = "raw",
    mode: str = "fast",
    critique_regime: str = "balanced",
    variation_regime: str = "normal",
    grounding_mode: str = "balanced",
    assembly_mode: str = "synthesis",
    council_span: str = "auto",
    show_orchestration_trace: bool = False,
    debug: bool = False,
    preset: str | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
    voice_max_tokens: int | None = None,
    closing_max_tokens: int | None = None,
    max_turns: int | None = None,
    output_format: str = "json",
    detail: str = "with_turns",
    event_sink=None,
    workspace_id: str | None = None,
    closing_genre: str | None = None,
    dialogue_protocol: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    runtime_layer = runtime_layer if runtime_layer in SUPPORTED_LAYERS else LAYER_PERSONA
    grounding_mode = grounding_mode if grounding_mode in GROUNDING_MODES else "balanced"
    assembly_mode = assembly_mode if assembly_mode in ASSEMBLY_MODES else "synthesis"
    council_span = council_span if council_span in COUNCIL_SPANS else "auto"
    if runtime_layer == LAYER_PERSONA:
        payload = _run_persona_layer_request(
            text=text,
            input_mode=input_mode,
            mode=mode,
            critique_regime=critique_regime,
            variation_regime=variation_regime,
            grounding_mode=grounding_mode,
            assembly_mode=assembly_mode,
            council_span=council_span,
            show_orchestration_trace=show_orchestration_trace,
            detail=detail,
            debug=debug,
            preset=preset,
            model=model,
            voice_max_tokens=voice_max_tokens,
            closing_max_tokens=closing_max_tokens,
        )
    else:
        pipe = Pipeline(
            preset_override=preset or None,
            model_override=model or None,
            max_tokens_override=max_tokens if (max_tokens and max_tokens > 0) else None,
            voice_max_tokens_override=voice_max_tokens if (voice_max_tokens and voice_max_tokens > 0) else None,
            closing_max_tokens_override=closing_max_tokens if (closing_max_tokens and closing_max_tokens > 0) else None,
            max_turns_override=max_turns if (max_turns and max_turns > 0) else None,
            workspace_id=workspace_id,
        )
        # B-5.5 Веха 3 — всегда шлём события в WS-подписчиков (если запущены).
        # Комбинируем с user-supplied event_sink через wrapper.
        try:
            from . import ws_endpoint
            _ws_send = ws_endpoint.register_event_sink
        except Exception:
            _ws_send = None

        _user_sink = event_sink
        # B-5.5 race-fix v2.1: bridge run_id известен явно (client-provided
        # или сгенерированный worker'ом). Не полагаемся на evt.get('run_id')
        # — многие события (situation_reading_done, cast_selected,
        # turn_completed, closing_*, checkpoint_reached) НЕ содержат run_id
        # в payload'е, и раньше выкидывались.
        _bridge_run_id = run_id  # from parameter
        def _combined_sink(evt: dict) -> None:
            if _user_sink is not None:
                try:
                    _user_sink(evt)
                except Exception:
                    pass
            if _ws_send is not None:
                # Priority: явный run_id из вызова > evt.run_id > skip
                rid = _bridge_run_id or evt.get("run_id")
                if rid:
                    # обеспечить run_id в payload для клиента
                    if "run_id" not in evt:
                        evt = {**evt, "run_id": rid}
                    try:
                        _ws_send(rid, evt)
                    except Exception:
                        pass
        pipe.event_sink = _combined_sink

        if closing_genre:
            pipe.closing_genre_id = closing_genre
        if dialogue_protocol:
            pipe.dialogue_protocol_id = dialogue_protocol
        resolved_input_mode = input_mode
        ingress_mode = "legacy_raw"

        if input_mode == "semantic-units":
            result, ingress_mode = _run_semantic_units_request(
                pipe,
                text=text,
                mode=mode,
                critique_regime=critique_regime,
                variation_regime=variation_regime,
            )
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
        elif input_mode == "raw+fabric":
            result = pipe.run_from_raw_text(
                text=text,
                mode=mode,
                run_id=run_id,
                critique_regime=critique_regime,
                variation_regime=variation_regime,
                source_id="web_ui",
            )
            resolved_input_mode = "raw+fabric"
            ingress_mode = "fabric_snapshot"
        elif input_mode == "units":
            pack = parse_md_units_text(text)
            result = pipe.run_from_units(
                pack,
                mode=mode,
                run_id=run_id,
                critique_regime=critique_regime,
                variation_regime=variation_regime,
            )
            resolved_input_mode = "semantic-units"
            ingress_mode = "md_units_pack"
        else:
            result = pipe.run(
                text=text,
                mode=mode,
                run_id=run_id,
                critique_regime=critique_regime,
                variation_regime=variation_regime,
            )

        payload = {
            "runtime_layer": LAYER_CALIFORNIAN_ID,
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
                "grounding_mode": grounding_mode,
                "assembly_mode": assembly_mode,
                "council_span": council_span,
            },
            "input_mode": resolved_input_mode,
            "ingress_mode": ingress_mode,
            "preset": pipe.preset_override,
            "model": pipe.model_override,
            "max_tokens": pipe.max_tokens_override,
            "voice_max_tokens": pipe.voice_max_tokens_override,
            "closing_max_tokens": pipe.closing_max_tokens_override,
            "max_turns": pipe.max_turns_override,
            "closing_speech": (
                (result.run_state.completion.closing_speech or "").strip()
                if result.run_state.completion else ""
            ),
        }
        if detail == "with_turns" or debug:
            payload["turns"] = [
                {
                    "turn_index": turn.turn_index,
                    "persona_id": turn.persona_id,
                    "operation": turn.operation,
                    "utterance": turn.utterance,
                    "confidence": turn.confidence,
                    "model": turn.model_name,
                    "provider": turn.model_provider,
                }
                for turn in result.run_state.turns
            ]
        if debug:
            payload["situation"] = to_plain(result.run_state.situation)
            payload["argument_map"] = to_plain(result.run_state.argument_map)
        if show_orchestration_trace:
            payload["orchestration_trace"] = {
                "runtime_layer": LAYER_CALIFORNIAN_ID,
                "detail": "legacy runtime does not expose council-span routing trace",
            }

    if output_format == "text":
        return _render_text_payload(payload, detail=detail)
    return payload


def _run_persona_layer_request(
    *,
    text: str,
    input_mode: str,
    mode: str,
    critique_regime: str,
    variation_regime: str,
    grounding_mode: str,
    assembly_mode: str,
    council_span: str,
    show_orchestration_trace: bool,
    detail: str,
    debug: bool,
    preset: str | None = None,
    model: str | None = None,
    voice_max_tokens: int | None = None,
    closing_max_tokens: int | None = None,
) -> dict[str, Any]:
    pipe = Pipeline(
        preset_override=preset or None,
        model_override=model or None,
        voice_max_tokens_override=voice_max_tokens if (voice_max_tokens and voice_max_tokens > 0) else None,
        closing_max_tokens_override=closing_max_tokens if (closing_max_tokens and closing_max_tokens > 0) else None,
    )
    scene, ingress_mode, unit_count = _scene_from_web_input(text=text, input_mode=input_mode, pipe=pipe)
    runtime = PersonaCouncilRuntime()
    force_span = None if council_span == "auto" else council_span
    scaffold = runtime.run(scene, enable_nemo8=True, force_span=force_span)
    persona_client = _build_non_mock_client(pipe, "persona_turn")
    closing_client = _build_non_mock_client(pipe, "zarathustra_closing_speech")

    turns = _materialize_persona_layer_turns(
        runtime=runtime,
        scaffold=scaffold,
        scene=scene,
        persona_client=persona_client,
        critique_regime=critique_regime,
        variation_regime=variation_regime,
        grounding_mode=grounding_mode,
    )
    final_answer = _generate_persona_layer_final_answer(
        client=closing_client,
        scene=scene,
        scaffold=scaffold,
        turns=turns,
        critique_regime=critique_regime,
        variation_regime=variation_regime,
        grounding_mode=grounding_mode,
        assembly_mode=assembly_mode,
    )

    payload: dict[str, Any] = {
        "runtime_layer": LAYER_PERSONA,
        "run_id": scaffold.run_id,
        "mode": mode,
        "status": "COMPLETED",
        "stopping_reason": None,
        "completion": {
            "form": "persona_layer_llm_final_synthesis",
            "closing_speech": final_answer,
        },
        "synthesis": None,
        "voices_used": [turn["persona_id"] for turn in turns],
        "turn_count": len(turns),
        "security_events": [],
        "errors": [],
        "trace_dir": None,
        "regimes": {
            "critique_regime": critique_regime,
            "variation_regime": variation_regime,
            "grounding_mode": grounding_mode,
            "assembly_mode": assembly_mode,
            "council_span": council_span,
        },
        "input_mode": input_mode,
        "ingress_mode": ingress_mode,
        "preset": preset,
        "model": model or getattr(persona_client, "model", None),
        "max_tokens": None,
        "voice_max_tokens": voice_max_tokens,
        "closing_max_tokens": closing_max_tokens,
        "max_turns": None,
        "closing_speech": final_answer.strip(),
        "persona_layer": {
            "council_span": scaffold.trace["route_plan"]["council_span"],
            "cast_mode": scaffold.trace["route_plan"]["cast_mode"],
            "selected_persona_ids": scaffold.trace["route_plan"]["selected_persona_ids"],
            "execution_order": scaffold.trace["route_plan"]["execution_order"],
            "call_nemo8": scaffold.trace["route_plan"]["call_nemo8"],
            "nemo8_used": scaffold.nemo8_turn is not None,
            "reopened_persona_ids": [turn.persona_id for turn in scaffold.reopened_turns],
            "minority_positions": scaffold.minority_positions,
            "unit_count": unit_count,
            "text_runtime": "llm_materialized",
            "grounding_mode": grounding_mode,
            "assembly_mode": assembly_mode,
        },
    }
    if detail == "with_turns" or debug:
        payload["turns"] = turns
    if show_orchestration_trace:
        payload["orchestration_trace"] = {
            "council_span": scaffold.trace["route_plan"]["council_span"],
            "cast_mode": scaffold.trace["route_plan"]["cast_mode"],
            "selected_persona_ids": scaffold.trace["route_plan"]["selected_persona_ids"],
            "execution_order": scaffold.trace["route_plan"]["execution_order"],
            "call_nemo8": scaffold.trace["route_plan"]["call_nemo8"],
            "nemo8_used": scaffold.nemo8_turn is not None,
            "reopened_persona_ids": [turn.persona_id for turn in scaffold.reopened_turns],
            "reopen_decision": scaffold.trace["reopen_decision"],
            "rationale": scaffold.trace["route_plan"]["rationale"],
        }
    if debug:
        payload["trace"] = scaffold.trace
    return payload


def _build_non_mock_client(pipe: Pipeline, role: str):
    provider_name, provider_cfg = pipe._role_and_cfg(role)
    kind = str(provider_cfg.get("kind") or provider_name or "").lower()
    if kind == "mock" or provider_name == "mock":
        raise RuntimeError(
            f"persona_layer requires a real LLM for role `{role}`, but resolved provider is `mock`"
        )
    client = build_client(provider_name, provider_cfg)
    if getattr(client, "provider", "").lower() == "mock":
        raise RuntimeError(f"persona_layer role `{role}` resolved to mock client")
    return client


def _materialize_persona_layer_turns(
    *,
    runtime: PersonaCouncilRuntime,
    scaffold: CouncilRun,
    scene: str,
    persona_client,
    critique_regime: str,
    variation_regime: str,
    grounding_mode: str,
) -> list[dict[str, Any]]:
    rendered: list[dict[str, Any]] = []
    sequence: list[tuple[str, Any]] = [("base", turn) for turn in scaffold.base_turns]
    if scaffold.nemo8_turn is not None:
        sequence.append(("meta", scaffold.nemo8_turn))
    sequence.extend(("reopen", turn) for turn in scaffold.reopened_turns)

    prior_turns: list[dict[str, Any]] = []
    for index, (phase, turn) in enumerate(sequence):
        pkg = runtime.registry.personas[turn.persona_id]
        card = next(card for card in pkg.cards if card.card_id == turn.card_id)
        utterance = _generate_persona_layer_utterance(
            client=persona_client,
            package_dir=pkg.package_dir,
            persona_id=turn.persona_id,
            scene=scene,
            card=card,
            phase=phase,
            prior_turns=prior_turns,
            critique_regime=critique_regime,
            variation_regime=variation_regime,
            grounding_mode=grounding_mode,
            meta_challenge=turn.meta_challenge,
        )
        rendered_turn = {
            "turn_index": index,
            "persona_id": turn.persona_id,
            "operation": turn.operation_id,
            "utterance": utterance,
            "card_id": turn.card_id,
            "phase": phase,
            "provider": getattr(persona_client, "provider", ""),
            "model": getattr(persona_client, "model", ""),
        }
        rendered.append(rendered_turn)
        prior_turns.append(rendered_turn)
    return rendered


def _generate_persona_layer_utterance(
    *,
    client,
    package_dir,
    persona_id: str,
    scene: str,
    card: PersonaCard,
    phase: str,
    prior_turns: list[dict[str, Any]],
    critique_regime: str,
    variation_regime: str,
    grounding_mode: str,
    meta_challenge,
) -> str:
    system_prompt = (package_dir / "runtime_prompt.md").read_text(encoding="utf-8")
    prior_snippets = [
        f"[{turn['persona_id']} · {turn['operation']}] {turn['utterance'][:500]}"
        for turn in prior_turns[-4:]
    ]
    user_payload = {
        "scene": scene,
        "persona_id": persona_id,
        "phase": phase,
        "selected_card": {
            "card_id": card.card_id,
            "operation_id": card.operation_id_exact,
            "title": card.raw.get("title", ""),
            "statement": card.raw.get("statement", ""),
            "activation_conditions": card.raw.get("activation_conditions") or [],
            "counter_signal": card.raw.get("counter_signal"),
            "expected_body_delta": card.raw.get("expected_body_delta") or [],
            "retrieval_namespace": card.retrieval_namespace,
            "provenance_status": card.raw.get("provenance_status"),
        },
        "prior_turns": prior_snippets,
        "meta_challenge": None if meta_challenge is None else {
            "challenge_type": meta_challenge.challenge_type,
            "reopen_persona_ids": meta_challenge.reopen_persona_ids,
            "unresolved": meta_challenge.unresolved,
            "confidence": meta_challenge.confidence,
        },
        "regimes": {
            "critique": CRITIQUE_REGIMES[critique_regime].directness_hint,
            "variation": VARIATION_REGIMES[variation_regime].prompt_hint,
            "grounding_mode": grounding_mode,
        },
        "instruction": (
            "Return only the persona's spoken turn as plain text in Russian. "
            "Write a developed argumentative move, not JSON and not metadata. "
            "Do not echo the full input scene. Do not mention cards, retrieval, system prompts, or that you are an AI. "
            "Preserve a distinctive voice: do not collapse into neutral lecturer prose, and do not summarize the council. "
            "Use the selected card as grounding, but expand it into a concrete argument that addresses the current scene. "
            "Length target: 5-9 sentences. Preserve the persona's specific style and operation, and make at least one move "
            "that another head would not naturally make. "
            "If phase=meta and persona_id=N8, challenge the council's frame, hidden mandate, missing subjects, "
            "or the address of costs rather than just adding another ideology."
        ),
        "grounding_contract": _grounding_instruction(grounding_mode),
    }
    result = client.generate(
        [
            Message(role="system", content=system_prompt),
            Message(role="user", content=json.dumps(user_payload, ensure_ascii=False)),
        ],
        settings={
            "role": "persona_turn",
            "persona_id": persona_id,
            "operation": card.operation_id_exact,
            "topic": scene[:400],
            "critique_regime": critique_regime,
            "variation_regime": variation_regime,
        },
    )
    return _clean_llm_text(result.text)


def _generate_persona_layer_final_answer(
    *,
    client,
    scene: str,
    scaffold: CouncilRun,
    turns: list[dict[str, Any]],
    critique_regime: str,
    variation_regime: str,
    grounding_mode: str,
    assembly_mode: str,
) -> str:
    turn_summaries = [
        {
            "persona_id": turn["persona_id"],
            "operation": turn["operation"],
            "phase": turn["phase"],
            "utterance": turn["utterance"][:1200],
        }
        for turn in turns
    ]
    payload = {
        "scene": scene,
        "route_plan": scaffold.trace.get("route_plan", {}),
        "minority_positions": scaffold.minority_positions,
        "turns": turn_summaries,
        "regimes": {
            "critique": CRITIQUE_REGIMES[critique_regime].directness_hint,
            "variation": VARIATION_REGIMES[variation_regime].prompt_hint,
            "grounding_mode": grounding_mode,
            "assembly_mode": assembly_mode,
        },
        "instruction": (
            "Return only Zarathustra's final answer in Russian as plain text. "
            "Do not echo the full user input. Do not mention routing, cards, retrieval, JSON, traces, or system prompts. "
            "Synthesize the council into a real answer with preserved tensions, concrete distinctions, and a clear next framing. "
            "Do not flatten the voices into generic consensus. Name or clearly attribute at least two distinct lines of force, "
            "retain at least one unresolved tension or dissenting edge, and avoid turning the answer into bland pedagogical summary prose. "
            "If NEMO-8 intervened, incorporate its challenge as a structural correction rather than naming infrastructure. "
            "Length target: 2-6 compact paragraphs."
        ),
        "grounding_contract": _grounding_instruction(grounding_mode),
        "assembly_contract": _assembly_instruction(assembly_mode),
    }
    result = client.generate(
        [
            Message(
                role="system",
                content=(
                    "You are Zarathustra, sole orchestrator and final speaker of the council. "
                    "You synthesize voices without flattening meaningful dissent."
                ),
            ),
            Message(role="user", content=json.dumps(payload, ensure_ascii=False)),
        ],
        settings={
            "role": "zarathustra_closing_speech",
            "topic": scene[:400],
            "critique_regime": critique_regime,
            "variation_regime": variation_regime,
        },
    )
    return _clean_llm_text(result.text)


def _clean_llm_text(text: str) -> str:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("text"):
            cleaned = cleaned[4:].strip()
    return cleaned


def _grounding_instruction(mode: str) -> str:
    """Grounding contract text.

    Workbench Stage 0: the text now lives in ``data/prompt_assets/grounding.*.md``
    instead of this function body. Behaviour is unchanged — byte equality is
    asserted by ``tests/workbench/test_prompt_extraction_golden.py``.
    """
    key = mode if mode in GROUNDING_MODES else "balanced"
    return prompt_assets.runtime_block(f"grounding.{key}")


def _assembly_instruction(mode: str) -> str:
    """Assembly contract text (including the ``roast`` / «прожарка» mode).

    Workbench Stage 0: extracted to ``data/prompt_assets/assembly.*.md``.
    """
    key = mode if mode in ASSEMBLY_MODES else "synthesis"
    return prompt_assets.runtime_block(f"assembly.{key}")


def _render_text_payload(payload: dict[str, Any], *, detail: str) -> dict[str, Any]:
    lines: list[str] = []
    completion = payload.get("completion") or {}
    speech = (payload.get("closing_speech") or "").strip()
    form = completion.get("form") or "?"

    lines.append("Заратустра")
    lines.append("")
    if speech:
        lines.append(speech)
    else:
        # HARD_RULES §1: пустая речь = баг, а не placeholder. Живой pipeline
        # уже raise'ает (pipeline.py:459). Это ветка — только для тестов на
        # mock или если Codex-guard был обойдён.
        lines.append(
            "[ERROR] closing_speech is empty. См. errors в meta. "
            "В prod runtime это RuntimeError — если видишь это, значит либо "
            "запрос ушёл на mock (нарушение HARD_RULES §1), либо LLM "
            "вернул пустой ответ без exception."
        )
    lines.append("")
    lines.append(
        f"[форма завершения: {form} · layer: {payload.get('runtime_layer')} · voices: "
        f"{', '.join(payload.get('voices_used') or []) or '—'}]"
    )

    if detail == "with_turns":
        turns = payload.get("turns") or []
        if turns:
            lines.append("")
            lines.append("--- ход совета ---")
            for turn in turns:
                lines.append("")
                lines.append(f"[{turn.get('persona_id')} · {turn.get('operation')}]")
                lines.append((turn.get("utterance") or "").strip())
    orchestration_trace = payload.get("orchestration_trace")
    if orchestration_trace:
        lines.append("")
        lines.append("--- orchestration trace ---")
        lines.append(
            f"span: {orchestration_trace.get('council_span', 'n/a')} · cast: {orchestration_trace.get('cast_mode', 'n/a')} · "
            f"nemo8: {'yes' if orchestration_trace.get('nemo8_used') else 'no'}"
        )
        selected = ", ".join(orchestration_trace.get("selected_persona_ids") or []) or "—"
        execution = ", ".join(orchestration_trace.get("execution_order") or []) or "—"
        reopened = ", ".join(orchestration_trace.get("reopened_persona_ids") or []) or "—"
        lines.append(f"selected: {selected}")
        lines.append(f"execution: {execution}")
        lines.append(f"reopened: {reopened}")
        rationale = (orchestration_trace.get("rationale") or "").strip()
        if rationale:
            lines.append(f"why: {rationale}")
        reopen_decision = orchestration_trace.get("reopen_decision") or {}
        if reopen_decision:
            lines.append(
                f"reopen decision: accepted={reopen_decision.get('accepted')} reason={reopen_decision.get('reason')}"
            )

    return {
        "format": "text",
        "body": "\n".join(lines),
        "meta": {
            "run_id": payload.get("run_id"),
            "runtime_layer": payload.get("runtime_layer"),
            "mode": payload.get("mode"),
            "status": payload.get("status"),
            "form": form,
            "voices_used": payload.get("voices_used"),
            "turn_count": payload.get("turn_count"),
            "preset": payload.get("preset"),
            "model": payload.get("model"),
            "max_tokens": payload.get("max_tokens"),
            "voice_max_tokens": payload.get("voice_max_tokens"),
            "closing_max_tokens": payload.get("closing_max_tokens"),
            "max_turns": payload.get("max_turns"),
            "security_events": payload.get("security_events"),
            "trace_dir": payload.get("trace_dir"),
            "errors": payload.get("errors"),
            "persona_layer": payload.get("persona_layer"),
            "orchestration_trace": payload.get("orchestration_trace"),
        },
    }


def _parse_optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _run_semantic_units_request(
    pipe: Pipeline,
    *,
    text: str,
    mode: str,
    critique_regime: str,
    variation_regime: str,
):
    stripped = text.strip()
    try:
        if stripped.startswith("{") or stripped.startswith("mode:"):
            parsed = yaml.safe_load(text)
            if not isinstance(parsed, dict):
                raise ValueError("semantic-units input must decode to an object")
            envelope = parse_envelope(parsed)
            return (
                pipe.run_from_envelope(
                    envelope,
                    mode=mode,
                    critique_regime=critique_regime,
                    variation_regime=variation_regime,
                ),
                "semantic_units",
            )
        pack = parse_md_units_text(text)
        return (
            pipe.run_from_units(
                pack,
                mode=mode,
                critique_regime=critique_regime,
                variation_regime=variation_regime,
            ),
            "semantic_units",
        )
    except Exception:
        adapted_scene = _adapt_semantic_units_text_via_llm(pipe, text)
        return (
            pipe.run(
                text=adapted_scene,
                mode=mode,
                critique_regime=critique_regime,
                variation_regime=variation_regime,
            ),
            "semantic_units_llm_adapter",
        )


def _scene_from_web_input(*, text: str, input_mode: str, pipe: Pipeline | None = None) -> tuple[str, str, int]:
    if input_mode == "semantic-units":
        try:
            pack = _pack_from_semantic_units(text)
            return _pack_to_scene(pack), "semantic_units", len(pack.units)
        except Exception:
            pipe = pipe or Pipeline()
            adapted_scene = _adapt_semantic_units_text_via_llm(pipe, text)
            return adapted_scene, "semantic_units_llm_adapter", 0
    if input_mode == "auto-slice":
        envelope = parse_envelope({
            "mode": "raw_stream",
            "run_id": "web-ui-raw-stream",
            "content": text,
            "metadata": {"source": "web_ui"},
        })
        pack = envelope_to_unit_pack(envelope)
        return _pack_to_scene(pack), "raw_stream", len(pack.units)
    return text.strip(), "legacy_raw", 0


def _pack_from_semantic_units(text: str) -> UnitPack:
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("mode:"):
        parsed = yaml.safe_load(text)
        if not isinstance(parsed, dict):
            raise ValueError("semantic-units input must decode to an object")
        envelope = parse_envelope(parsed)
        return envelope_to_unit_pack(envelope)
    return parse_md_units_text(text)


def _adapt_semantic_units_text_via_llm(pipe: Pipeline, text: str) -> str:
    client = _build_non_mock_client(pipe, "zarathustra_situation_reading")
    payload = {
        "raw_input": text,
        "instruction": (
            "The input is intended as semantic units, Toulmin markup, claim/data/warrant analysis, or adjacent structured research notes, "
            "but it may not follow the runtime's canonical schema. Convert it into a clean plain-text scene for downstream council analysis. "
            "Preserve the main claim, key evidence, warrant, qualifiers, rebuttals, provenance caveats, and any explicit limits or prices of the thesis. "
            "Keep multiple live axes visible at once instead of collapsing the material into one dominant frame. "
            "Explicitly preserve, when present: price or sacrifice, ethics or moral status, institutions and power, project design or system capability, "
            "freedom or autonomy, long-term or intergenerational consequences, and epistemic limits or source caveats. "
            "Do not emit JSON, YAML, markdown headings, or meta commentary. Return only the normalized scene text in Russian."
        ),
    }
    result = client.generate(
        [
            Message(
                role="system",
                content=(
                    "You are a semantic input adapter for Zarathustra. "
                    "You normalize near-structured analytical notes into a council-ready scene without losing argumentative structure."
                ),
            ),
            Message(role="user", content=json.dumps(payload, ensure_ascii=False)),
        ],
        settings={
            "role": "zarathustra_situation_reading",
            "topic": "semantic_units_adapter",
        },
    )
    adapted = _clean_llm_text(result.text)
    if not adapted:
        raise RuntimeError("semantic-units LLM adapter returned empty text")
    return _stabilize_semantic_axes(adapted)


def _stabilize_semantic_axes(adapted: str) -> str:
    axis_line = (
        "Сохрани для совета одновременно: цену и жертву человеческой жизни; этический предел и моральный статус; "
        "институциональную власть, контроль и замкнутый контур управления; проектирование систем, дизайн новых правил и способность "
        "строить альтернативный порядок; свободу, автономию, согласие и право на отказ; долгосрочную траекторию, исторические и межпоколенческие "
        "последствия; эпистемические ограничения, статус интерпретации, пробелы в backing и ограничения источника."
    )
    normalized = adapted.strip()
    if axis_line.lower() in normalized.lower():
        return normalized
    return f"{normalized}\n\n{axis_line}"


def _build_api_access_payload() -> dict[str, Any]:
    api_key = os.environ.get(COMPAT_API_KEY_ENV)
    return {
        "access_mode": "tinkuy_compat_issued" if api_key else "not_issued",
        "provider": "tinkuy_openai_compatible" if api_key else None,
        "base_url": COMPAT_BASE_URL if api_key else None,
        "api_key": api_key if api_key else None,
        "api_key_env": COMPAT_API_KEY_ENV if api_key else None,
        "suggested_models": list(COMPAT_MODEL_ALIASES) if api_key else [],
        "note": (
            "Dedicated Tinkuy-issued key for the local OpenAI-compatible compatibility endpoint."
            if api_key else
            "A separate Tinkuy-issued API key is not available in this build."
        ),
    }


def _compat_models_payload() -> dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {
                "id": model_id,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "tinkuy",
            }
            for model_id in COMPAT_MODEL_ALIASES
        ],
    }


def _extract_bearer_token(handler: BaseHTTPRequestHandler) -> str:
    auth = handler.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        return ""
    return auth.split(" ", 1)[1].strip()


def _compat_key_is_valid(handler: BaseHTTPRequestHandler) -> bool:
    """Валидация Bearer. Порядок:
      1. Auth disabled env → True (dev).
      2. JWT (если Bearer выглядит как JWT) → verify_token.
      3. Multi-key CALIFORNIAN_ID_API_KEYS → label_for_bearer.
      4. Legacy TINKUY_COMPAT_API_KEY → строгое сравнение.
    """
    from . import auth, jwt_auth
    if auth.is_disabled():
        return True
    bearer = _extract_bearer_token(handler)
    if not bearer:
        return False
    # (2) JWT ветка — обрабатывает label_for_bearer через ту же функцию.
    if jwt_auth.looks_like_jwt(bearer) or auth.any_keys_configured():
        label = auth.label_for_bearer(bearer)
        if not label:
            return False
        allowed, _remaining, _limit = auth.check_rate_limit(label)
        return allowed
    # (4) legacy
    expected = os.environ.get(COMPAT_API_KEY_ENV) or ""
    if not expected:
        return False
    return bearer == expected


def _messages_to_text(messages: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for item in messages:
        role = str(item.get("role") or "user").upper()
        content = item.get("content")
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(str(part.get("text") or ""))
            content_text = "\n".join(part for part in text_parts if part.strip())
        else:
            content_text = str(content or "")
        if content_text.strip():
            lines.append(f"{role}:\n{content_text.strip()}")
    return "\n\n".join(lines).strip()


def _run_compat_chat_completion(request: dict[str, Any]) -> dict[str, Any]:
    model_name = str(request.get("model") or "tinkuy-persona-fast")
    alias = COMPAT_MODEL_ALIASES.get(model_name)
    if alias is None:
        raise ValueError(f"unknown compat model: {model_name}")
    messages = request.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages must be a non-empty list")
    text = _messages_to_text(messages)
    if not text:
        raise ValueError("messages produced empty text")
    max_tokens = request.get("max_completion_tokens")
    if max_tokens in (None, ""):
        max_tokens = request.get("max_tokens")
    payload = run_web_request(
        text=text,
        runtime_layer=alias["runtime_layer"],
        input_mode="raw",
        mode=alias["mode"],
        critique_regime="balanced",
        variation_regime="normal",
        grounding_mode="balanced",
        assembly_mode=alias["assembly_mode"],
        council_span=alias["council_span"],
        show_orchestration_trace=False,
        debug=False,
        preset=alias.get("preset"),
        model=None,
        max_tokens=_parse_optional_int(max_tokens),
        voice_max_tokens=None,
        closing_max_tokens=_parse_optional_int(max_tokens),
        max_turns=None,
        output_format="text",
        detail="only_result",
    )
    content = str(payload.get("body") or "").strip()
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    now = int(time.time())
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": now,
        "model": model_name,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }


def _pack_to_scene(pack: UnitPack) -> str:
    lines: list[str] = []
    if pack.seminar_title:
        lines.append(f"Title: {pack.seminar_title}")
    for unit in pack.units:
        speaker = ""
        if unit.provenance:
            first = unit.provenance[0]
            if isinstance(first, dict):
                speaker = str(first.get("participant_label") or first.get("participant_name") or "")
            else:
                speaker = first.participant_label or first.participant_name
        prefix = f"{speaker}: " if speaker else ""
        abstract = (unit.abstract or unit.title or "").strip()
        if not abstract:
            continue
        lines.append(f"{prefix}{abstract}")
    if pack.unresolved_questions_pack:
        lines.append("Open questions:")
        lines.extend(f"- {question}" for question in pack.unresolved_questions_pack)
    scene = "\n".join(lines).strip()
    if not scene:
        raise ValueError("semantic-units input produced an empty scene")
    return scene


class _WebUIHandler(BaseHTTPRequestHandler):
    server_version = "ZarathustraWebUI/0.2"

    def _query_param(self, name: str) -> str | None:
        # self.path is already path-only after do_GET stripped ?; read raw from headers
        # (нам достаточно смотреть self.raw_path — но её нет; вернём None и заставим
        # POST/JSON быть первичным источником workspace_id).
        raw = getattr(self, "raw_query", None)
        if not raw:
            return None
        from urllib.parse import parse_qs
        parts = parse_qs(raw)
        vals = parts.get(name) or []
        return vals[0] if vals else None

    def do_GET(self) -> None:  # noqa: N802
        raw = self.path
        if "?" in raw:
            path_only, self.raw_query = raw.split("?", 1)
        else:
            path_only, self.raw_query = raw, ""
        self.path = path_only
        # B-5.5 Веха 4 — Svelte live UI на /live/*
        if self.path == "/live" or self.path == "/live/":
            self._serve_live_index(); return
        if self.path.startswith("/live/"):
            self._serve_live_asset(self.path[len("/live/"):]); return
        if self.path in {"/v1/models"}:
            if not _compat_key_is_valid(self):
                self._send_json({"error": {"message": "unauthorized", "type": "invalid_request_error"}}, status=HTTPStatus.UNAUTHORIZED)
                return
            self._send_json(_compat_models_payload())
            return
        if self.path in {"/api/presets", "/presets"}:
            cfg = load_config()
            self._send_json({"presets": cfg.presets()})
            return
        if self.path in {"/api/models", "/models"}:
            cfg = load_config()
            self._send_json({"models": cfg.model_menu()})
            return
        if self.path in {"/api/access", "/access"}:
            self._send_json(_build_api_access_payload())
            return
        # 6.3 async job status / result
        if self.path.startswith("/api/run/") and self.path.endswith("/status"):
            run_id = self.path[len("/api/run/"):-len("/status")]
            ws = self._query_param("workspace") or "default"
            from .async_jobs import get_status
            data = get_status(ws, run_id)
            if data is None:
                self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND); return
            self._send_json(data); return
        # B-5.5 Веха 1 — runtime control snapshot + audit log
        if self.path.startswith("/api/run/") and self.path.endswith("/control"):
            run_id = self.path[len("/api/run/"):-len("/control")]
            from . import runtime_control
            ws = self._query_param("workspace") or "default"
            snap = runtime_control.snapshot_state(run_id)
            store = runtime_control.InterventionStore.for_workspace(ws)
            try:
                interventions = store.list_for_run(run_id)
            finally:
                store.close()
            from dataclasses import asdict
            self._send_json({
                "run_state": snap,
                "interventions": [asdict(i) for i in interventions],
            }); return
        if self.path.startswith("/api/run/") and self.path.endswith("/export"):
            run_id = self.path[len("/api/run/"):-len("/export")]
            ws = self._query_param("workspace") or "default"
            fmt = (self._query_param("format") or "md").lower()
            if fmt not in {"json", "md", "bundle"}:
                self._send_json({"error": f"unknown format {fmt}"},
                                status=HTTPStatus.BAD_REQUEST); return
            from . import exporters
            if fmt == "json":
                body = exporters.export_json(ws, run_id)
            elif fmt == "md":
                body = exporters.export_markdown(ws, run_id)
            else:
                body = exporters.export_bundle(ws, run_id)
            if body is None:
                self._send_json({"error": "run not found or not ready"},
                                status=HTTPStatus.NOT_FOUND); return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", exporters.content_type_for(fmt))
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Disposition",
                             f'attachment; filename="{exporters.filename_for(run_id, fmt)}"')
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/api/run/") and self.path.endswith("/result"):
            run_id = self.path[len("/api/run/"):-len("/result")]
            ws = self._query_param("workspace") or "default"
            from .async_jobs import get_result, get_status
            data = get_result(ws, run_id)
            if data is None:
                st = get_status(ws, run_id)
                if st is None:
                    self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND); return
                self._send_json({"status": st.get("status", "RUNNING"),
                                 "note": "not ready yet"}, status=HTTPStatus.ACCEPTED); return
            self._send_json(data); return
        # 8.2 cross-run search
        if self.path in {"/api/runs/search", "/runs/search"}:
            from . import cross_run
            ws = self._query_param("workspace") or "default"
            q = self._query_param("q") or ""
            limit = int(self._query_param("limit") or "20")
            results = cross_run.search_runs(ws, q, limit=limit)
            self._send_json({"workspace_id": ws, "query": q,
                             "count": len(results), "results": results})
            return
        # 6.5 runs list
        if self.path.startswith("/api/runs") or self.path == "/runs":
            from .workspaces import RunStore
            ws = self._query_param("workspace") or "default"
            limit = int(self._query_param("limit") or "50")
            store = RunStore.for_workspace(ws)
            try:
                items = store.list(limit=limit)
            finally:
                store.close()
            from dataclasses import asdict
            self._send_json({
                "workspace_id": ws,
                "runs": [asdict(m) for m in items],
            })
            return
        # 6.A workspaces list
        if self.path in {"/api/workspaces", "/workspaces"}:
            from .workspaces import list_workspaces
            self._send_json({"workspaces": list_workspaces()})
            return
        # 7.2 genres list
        if self.path in {"/api/genres", "/genres"}:
            from . import rhetorical_genres
            self._send_json({
                "genres": rhetorical_genres.list_genres(),
                "default": rhetorical_genres.default_genre_id(),
            })
            return
        # 7.4 dialogue protocols list
        if self.path in {"/api/protocols", "/protocols"}:
            from . import dialogue_protocols as _dp
            self._send_json({
                "protocols": _dp.list_protocols(),
                "default": _dp.default_protocol_id(),
            })
            return
        # 7.1 method packs list
        if self.path in {"/api/methods", "/methods"}:
            from . import method_packs
            self._send_json({"methods": method_packs.list_methods()})
            return
        # 8.3 billing summary
        if self.path in {"/api/billing", "/billing"}:
            from . import auth
            ws = self._query_param("workspace") or None
            self._send_json(auth.billing_summary(ws))
            return
        # 9.2 budgets summary
        if self.path in {"/api/budgets", "/budgets"}:
            from . import budgets
            ws = self._query_param("workspace") or None
            self._send_json(budgets.summary(ws))
            return
        # 6.4.3 whoami
        if self.path in {"/api/auth/me", "/auth/me"}:
            from . import jwt_auth
            bearer = _extract_bearer_token(self)
            if not bearer or not jwt_auth.looks_like_jwt(bearer):
                self._send_json({"error": "no jwt in Authorization"},
                                status=HTTPStatus.UNAUTHORIZED); return
            try:
                payload = jwt_auth.verify_token(bearer)
            except jwt_auth.JWTError as ex:
                self._send_json({"error": f"invalid token: {ex}"},
                                status=HTTPStatus.UNAUTHORIZED); return
            self._send_json({
                "username": payload.get("sub"),
                "roles": payload.get("roles") or [],
                "issued_at": payload.get("iat"),
                "expires_at": payload.get("exp"),
                "issuer": payload.get("iss"),
            })
            return
        # 9.1 narrative notes list
        if self.path in {"/api/narrative/notes", "/narrative/notes"}:
            from . import narrative_memory
            ws = self._query_param("workspace") or "default"
            kind = self._query_param("kind") or None
            limit = int(self._query_param("limit") or "50")
            store = narrative_memory.NarrativeStore.for_workspace(ws)
            try:
                notes = store.list(kind=kind, limit=limit)
            finally:
                store.close()
            from dataclasses import asdict
            self._send_json({"workspace_id": ws,
                             "count": len(notes),
                             "notes": [asdict(n) for n in notes]})
            return
        if self.path not in {"/", "/index.html"}:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        body = _HTML.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        if self.path in {"/api/run/stream", "/run/stream"}:
            self._handle_run_stream()
            return
        if self.path in {"/api/run/async", "/run/async"}:
            self._handle_run_async()
            return
        if self.path in {"/api/socrates/run"}:
            self._handle_socrates_run()
            return
        # B-5.5 Веха 1 — intervention endpoint (pause/resume/cancel + Веха 2 kinds)
        if self.path.startswith("/api/run/") and self.path.endswith("/intervention"):
            run_id = self.path[len("/api/run/"):-len("/intervention")]
            self._handle_intervention(run_id)
            return
        if self.path in {"/api/narrative/reflect", "/narrative/reflect"}:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length else b"{}"
                data = json.loads(raw.decode("utf-8")) if raw else {}
            except Exception as exc:
                self._send_json({"error": f"bad request: {exc}"},
                                status=HTTPStatus.BAD_REQUEST); return
            ws = data.get("workspace_id") or "default"
            window = int(data.get("window") or 10)
            from . import narrative_memory
            self._send_json(narrative_memory.reflect_over_window(ws, window=window))
            return
        # 6.4.3 auth
        if self.path in {"/api/auth/login", "/auth/login"}:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length else b"{}"
                data = json.loads(raw.decode("utf-8")) if raw else {}
            except Exception as exc:
                self._send_json({"error": f"bad request: {exc}"},
                                status=HTTPStatus.BAD_REQUEST); return
            username = (data.get("username") or "").strip()
            password = data.get("password") or ""
            if not username or not password:
                self._send_json({"error": "username and password required"},
                                status=HTTPStatus.BAD_REQUEST); return
            from . import jwt_auth
            from .users import UserStore
            store = UserStore()
            try:
                user = store.verify(username, password)
            finally:
                store.close()
            if not user:
                self._send_json({"error": "invalid credentials"},
                                status=HTTPStatus.UNAUTHORIZED); return
            ttl = int(data.get("ttl_sec") or jwt_auth.DEFAULT_TTL_SEC)
            token = jwt_auth.issue_token(sub=user.username, roles=user.roles,
                                          ttl_sec=ttl)
            self._send_json({
                "token": token,
                "token_type": "Bearer",
                "expires_in": ttl,
                "user": {"username": user.username, "roles": user.roles},
            })
            return
        if self.path in {"/api/reflect/cross_run", "/reflect/cross_run"}:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length else b"{}"
                data = json.loads(raw.decode("utf-8")) if raw else {}
            except Exception as exc:
                self._send_json({"error": f"bad request: {exc}"},
                                status=HTTPStatus.BAD_REQUEST); return
            ws = data.get("workspace_id") or "default"
            a = data.get("run_a") or ""; b = data.get("run_b") or ""
            if not a or not b:
                self._send_json({"error": "run_a and run_b required"},
                                status=HTTPStatus.BAD_REQUEST); return
            from . import cross_run
            self._send_json(cross_run.compare_runs(ws, a, b))
            return
        if self.path in {"/v1/chat/completions"}:
            if not _compat_key_is_valid(self):
                self._send_json({"error": {"message": "unauthorized", "type": "invalid_request_error"}}, status=HTTPStatus.UNAUTHORIZED)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length)
                data = json.loads(raw.decode("utf-8"))
                payload = _run_compat_chat_completion(data)
                try:
                    from . import dialogue_log
                    _msgs = data.get("messages") or []
                    _last_user = ""
                    for m in reversed(_msgs):
                        if isinstance(m, dict) and m.get("role") == "user":
                            _last_user = m.get("content") or ""
                            break
                    _choices = payload.get("choices") or []
                    _reply = ""
                    if _choices and isinstance(_choices[0], dict):
                        _msg = _choices[0].get("message") or {}
                        _reply = _msg.get("content") or ""
                    dialogue_log.log_dialogue(
                        source="v1_chat", input_text=str(_last_user),
                        response={
                            "run_id": payload.get("id"),
                            "model_id": payload.get("model"),
                            "provider_id": "openai_compat",
                            "rendering": {"text": _reply}})
                except Exception:
                    pass
                self._send_json(payload)
            except Exception as exc:
                self._send_json({"error": {"message": str(exc), "type": "invalid_request_error"}}, status=HTTPStatus.BAD_REQUEST)
            return
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
                runtime_layer=data.get("runtime_layer") or LAYER_PERSONA,
                input_mode=data.get("input_mode") or "raw",
                mode=data.get("mode") or "fast",
                critique_regime=data.get("critique_regime") or "balanced",
                variation_regime=data.get("variation_regime") or "normal",
                grounding_mode=data.get("grounding_mode") or "balanced",
                assembly_mode=data.get("assembly_mode") or "synthesis",
                council_span=data.get("council_span") or "auto",
                show_orchestration_trace=bool(data.get("show_orchestration_trace")),
                debug=bool(data.get("debug")),
                preset=(data.get("preset") or None),
                model=(data.get("model") or None),
                max_tokens=_parse_optional_int(data.get("max_tokens")),
                voice_max_tokens=_parse_optional_int(data.get("voice_max_tokens")),
                closing_max_tokens=_parse_optional_int(data.get("closing_max_tokens")),
                max_turns=_parse_optional_int(data.get("max_turns")),
                output_format=(data.get("output_format") or "json"),
                detail=(data.get("detail") or "with_turns"),
                workspace_id=data.get("workspace_id") or None,
                closing_genre=data.get("closing_genre") or None,
                dialogue_protocol=data.get("dialogue_protocol") or None,
            )
            try:
                from . import dialogue_log
                dialogue_log.log_dialogue(
                    source="run", input_text=text, response=payload,
                    extra={"workspace_id": data.get("workspace_id")})
            except Exception:
                pass
            self._send_json(payload)
        except Exception as exc:  # pragma: no cover
            try:
                from . import dialogue_log
                dialogue_log.log_dialogue(
                    source="run", input_text=text if 'text' in locals() else "",
                    error=f"{type(exc).__name__}: {exc}")
            except Exception:
                pass
            self._send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    # ---------- B-5.5 Веха 4 — Svelte live UI static serve ----------
    _LIVE_MIME = {
        ".html": "text/html; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".map": "application/json; charset=utf-8",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".ico": "image/x-icon",
        ".woff2": "font/woff2",
    }

    def _live_dir(self) -> Path:
        from .config import DATA_ROOT
        return DATA_ROOT / "frontend"

    def _serve_live_index(self) -> None:
        idx = self._live_dir() / "index.html"
        if not idx.exists():
            self._send_json({
                "error": "Live UI not built. Run `cd frontend && npm run build`.",
                "expected_path": str(idx),
            }, status=HTTPStatus.NOT_FOUND); return
        body = idx.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _serve_live_asset(self, relpath: str) -> None:
        # anti path traversal
        from pathlib import PurePosixPath
        p = PurePosixPath(relpath)
        if any(part in {"..", ""} for part in p.parts):
            self.send_error(HTTPStatus.FORBIDDEN, "bad path"); return
        target = self._live_dir() / relpath
        try:
            target = target.resolve()
            live_root = self._live_dir().resolve()
            if not str(target).startswith(str(live_root)):
                self.send_error(HTTPStatus.FORBIDDEN, "escape"); return
        except Exception:
            self.send_error(HTTPStatus.NOT_FOUND, "not found"); return
        if not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "asset not found"); return
        body = target.read_bytes()
        ext = target.suffix.lower()
        mime = self._LIVE_MIME.get(ext, "application/octet-stream")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        # assets имена с hash → можем cache надолго; index.html без cache
        self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return

    # ---------- B-5.5 Веха 1 intervention endpoint ----------
    def _handle_intervention(self, run_id: str) -> None:
        from . import runtime_control, jwt_auth
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            data = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception as exc:
            self._send_json({"error": f"bad request: {exc}"},
                            status=HTTPStatus.BAD_REQUEST); return
        kind = (data.get("kind") or "").strip().lower()
        if kind not in runtime_control.INTERVENTION_KINDS:
            self._send_json({"error": f"unknown kind: {kind}",
                             "allowed": sorted(runtime_control.INTERVENTION_KINDS)},
                            status=HTTPStatus.BAD_REQUEST); return
        # определить author из JWT если есть, иначе anonymous
        author = "anonymous"
        bearer = _extract_bearer_token(self)
        if bearer and jwt_auth.looks_like_jwt(bearer):
            try:
                payload_jwt = jwt_auth.verify_token(bearer)
                author = str(payload_jwt.get("sub") or "anonymous")
            except jwt_auth.JWTError:
                pass
        try:
            iv = runtime_control.signal(
                run_id=run_id, kind=kind, author=author,
                payload=data.get("payload") or {},
            )
        except ValueError as ex:
            self._send_json({"error": str(ex)}, status=HTTPStatus.BAD_REQUEST); return
        # ответ + snapshot текущего состояния
        snapshot = runtime_control.snapshot_state(run_id)
        from dataclasses import asdict
        self._send_json({
            "accepted": True,
            "intervention": {
                "intervention_id": iv.intervention_id,
                "run_id": iv.run_id,
                "kind": iv.kind,
                "author": iv.author,
                "created_at": iv.created_at,
            },
            "run_state": snapshot,
        }, status=HTTPStatus.ACCEPTED)

    # ---------- 6.3 async job endpoint ----------
    def _handle_run_async(self) -> None:
        from .async_jobs import submit
        from .trace import new_run_id
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            data = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception as exc:
            self._send_json({"error": f"bad request: {exc}"},
                            status=HTTPStatus.BAD_REQUEST); return
        text = (data.get("text") or "").strip()
        if not text:
            self._send_json({"error": "text is required"},
                            status=HTTPStatus.BAD_REQUEST); return
        ws = data.get("workspace_id") or "default"
        # B-5.5 race-fix v2: accept client-provided run_id для subscribe-first.
        client_rid = (data.get("run_id") or "").strip()
        if client_rid:
            from . import async_jobs
            if not async_jobs.is_valid_client_run_id(client_rid):
                self._send_json({
                    "error": "invalid client-provided run_id",
                    "expected_pattern": "^run_[a-z0-9_-]{8,56}$",
                }, status=HTTPStatus.BAD_REQUEST); return
            if async_jobs.run_id_conflict(ws, client_rid):
                self._send_json({
                    "error": "run_id conflict — already exists in workspace",
                    "workspace_id": ws, "run_id": client_rid,
                }, status=HTTPStatus.CONFLICT); return
            run_id = client_rid
        else:
            run_id = new_run_id()
        # 9.2 hard budget check
        from . import budgets
        deny, info = budgets.should_deny(ws)
        if deny:
            self._send_json({"error": "budget exceeded", **info},
                            status=HTTPStatus.TOO_MANY_REQUESTS); return

        def _job() -> dict[str, Any]:
            payload = run_web_request(
                text,
                runtime_layer=data.get("runtime_layer") or LAYER_CALIFORNIAN_ID,
                input_mode=data.get("input_mode") or "raw",
                mode=data.get("mode") or "fast",
                critique_regime=data.get("critique_regime") or "balanced",
                variation_regime=data.get("variation_regime") or "normal",
                preset=(data.get("preset") or None),
                model=(data.get("model") or None),
                max_tokens=_parse_optional_int(data.get("max_tokens")),
                voice_max_tokens=_parse_optional_int(data.get("voice_max_tokens")),
                closing_max_tokens=_parse_optional_int(data.get("closing_max_tokens")),
                max_turns=_parse_optional_int(data.get("max_turns")),
                workspace_id=ws,
                closing_genre=data.get("closing_genre") or None,
                dialogue_protocol=data.get("dialogue_protocol") or None,
                run_id=run_id,
            )
            try:
                from . import dialogue_log
                dialogue_log.log_dialogue(
                    source="run_async", input_text=text, response=payload,
                    extra={"workspace_id": ws, "run_id": run_id})
            except Exception:
                pass
            return payload
        submit(ws, run_id, _job,
               input_summary=text, input_mode=data.get("input_mode") or "raw",
               mode=data.get("mode") or "fast")
        self._send_json({
            "run_id": run_id,
            "workspace_id": ws,
            "status": "RUNNING",
            "poll_status": f"/api/run/{run_id}/status?workspace={ws}",
            "poll_result": f"/api/run/{run_id}/result?workspace={ws}",
        }, status=HTTPStatus.ACCEPTED)

    # ---------- 6.B.3 SSE endpoint ----------
    def _handle_run_stream(self) -> None:  # type: ignore[no-redef]
        """Server-Sent Events. Worker thread → queue.Queue → chunked flush."""
        import queue
        import threading

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            data = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception as exc:
            self._send_json({"error": f"bad request: {exc}"}, status=HTTPStatus.BAD_REQUEST)
            return

        text = (data.get("text") or "").strip()
        if not text:
            self._send_json({"error": "text is required"}, status=HTTPStatus.BAD_REQUEST)
            return

        events: "queue.Queue[dict | None]" = queue.Queue(maxsize=1024)

        # B-5.5 Веха 3 — параллельная доставка в WS подписчиков (если есть).
        try:
            from . import ws_endpoint
            _ws_bridge = ws_endpoint.register_event_sink
        except Exception:
            _ws_bridge = None

        def sink(evt: dict) -> None:
            try:
                events.put(evt, timeout=1)
            except queue.Full:
                pass
            if _ws_bridge is not None:
                run_id_from_evt = evt.get("run_id")
                if run_id_from_evt:
                    try:
                        _ws_bridge(run_id_from_evt, evt)
                    except Exception:
                        pass

        def worker() -> None:
            try:
                payload = run_web_request(
                    text,
                    runtime_layer=data.get("runtime_layer") or LAYER_CALIFORNIAN_ID,
                    input_mode=data.get("input_mode") or "raw",
                    mode=data.get("mode") or "fast",
                    critique_regime=data.get("critique_regime") or "balanced",
                    variation_regime=data.get("variation_regime") or "normal",
                    preset=(data.get("preset") or None),
                    model=(data.get("model") or None),
                    max_tokens=_parse_optional_int(data.get("max_tokens")),
                    voice_max_tokens=_parse_optional_int(data.get("voice_max_tokens")),
                    closing_max_tokens=_parse_optional_int(data.get("closing_max_tokens")),
                    max_turns=_parse_optional_int(data.get("max_turns")),
                    event_sink=sink,
                    workspace_id=data.get("workspace_id") or None,
                    closing_genre=data.get("closing_genre") or None,
                    dialogue_protocol=data.get("dialogue_protocol") or None,
                )
                events.put({"kind": "final_payload", "payload": payload})
            except Exception as ex:  # noqa: BLE001
                events.put({"kind": "error", "error": f"{type(ex).__name__}: {ex}"})
            finally:
                events.put(None)  # sentinel

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")  # tell nginx/caddy not to buffer
        self.end_headers()

        t = threading.Thread(target=worker, daemon=True)
        t.start()

        try:
            while True:
                evt = events.get()
                if evt is None:
                    break
                body = f"data: {json.dumps(evt, ensure_ascii=False)}\n\n".encode("utf-8")
                try:
                    self.wfile.write(body)
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    return
        finally:
            # give worker a moment to exit if still alive
            t.join(timeout=0.5)

    # ---------- D-S26-LIVE-API-001 real Socrates endpoint ----------
    def _handle_socrates_run(self) -> None:
        """POST /api/socrates/run — real runtime via bridge module.

        The runtime dispatch itself lives in
        :mod:`californian_id.socrates_bridge` (the ONE allowlisted
        file that may cross into the runtime package); this
        handler only owns HTTP concerns (auth via Caddy, body
        parsing, status codes). Response always carries
        ``runtime_layer`` set to the runtime tag string.

        Intervention profile (B2): the request may carry
        ``intervention_profile`` naming a preset. Unknown preset
        yields HTTP 400. Explicit activation only — a lexical
        mention of the preset name inside ``text`` does NOT
        activate; only the typed control field does.
        """
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            data = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception as exc:
            self._send_json({"error": f"bad request: {exc}"},
                            status=HTTPStatus.BAD_REQUEST); return

        text = (data.get("text") or data.get("input") or "").strip()
        if not text:
            self._send_json({"error": "text is required"},
                            status=HTTPStatus.BAD_REQUEST); return

        mode = (data.get("execution_mode") or "LIVE").upper()
        if mode not in ("LIVE", "DETERMINISTIC"):
            self._send_json({"error": f"execution_mode must be LIVE "
                                       f"or DETERMINISTIC, got {mode!r}"},
                            status=HTTPStatus.BAD_REQUEST); return

        raw_profile = (data.get("intervention_profile")
                        or data.get("intervention") or "normal")
        profile_name = str(raw_profile).strip().lower()

        # B2Q: typed control field. Only this JSON object can
        # activate the QuestionSetPlan; lexical mention of
        # "questions" in text CANNOT.
        raw_qsr = data.get("question_set_request")
        question_set_request: dict[str, Any] | None = None
        if raw_qsr is not None:
            if not isinstance(raw_qsr, dict):
                self._send_json(
                    {"error": "question_set_request must be an object"},
                    status=HTTPStatus.BAD_REQUEST); return
            question_set_request = raw_qsr

        context_id = data.get("context_id")
        if context_id is not None:
            context_id = str(context_id).strip() or None
        raw_action = data.get("context_action")
        context_action: dict[str, Any] | None = None
        if raw_action is not None:
            if not isinstance(raw_action, dict):
                self._send_json(
                    {"error": "context_action must be an object"},
                    status=HTTPStatus.BAD_REQUEST); return
            context_action = raw_action

        from . import socrates_bridge
        try:
            payload = socrates_bridge.dispatch_socrates_run(
                text=text, execution_mode=mode,
                intervention_profile_name=profile_name,
                question_set_request=question_set_request,
                context_id=context_id,
                context_action=context_action,
                runs_dir=os.environ.get("CALIFORNIAN_ID_RUNS_DIR"))
        except ValueError as exc:
            self._send_json({"error": str(exc)},
                            status=HTTPStatus.BAD_REQUEST); return
        except Exception as exc:
            # The bridge below sets runtime_layer on success; on
            # exception we set the same tag string from the bridge's
            # public constant so the caller can distinguish this
            # error from a persona_layer failure.
            from . import socrates_bridge as _bridge
            self._send_json(
                {"error": f"socrates run failed: {type(exc).__name__}: {exc}",
                 "runtime_layer": _bridge.RUNTIME_LAYER_TAG},
                status=HTTPStatus.INTERNAL_SERVER_ERROR); return

        try:
            from . import dialogue_log
            dialogue_log.log_dialogue(
                source="socrates", input_text=text, response=payload)
        except Exception:
            pass
        self._send_json(payload)

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve_web_ui(host: str = "127.0.0.1", port: int = 8765,
                 ws_port: int | None = None) -> None:
    # B-5.5 Веха 3 — WebSocket сервер на отдельном порту (+1 к HTTP).
    ws_port = ws_port if ws_port is not None else port + 1
    try:
        from . import ws_endpoint
        if ws_endpoint.HAS_WEBSOCKETS:
            ws_endpoint.start_ws_server(host=host, port=ws_port)
            print(f"WebSocket endpoint on ws://{host}:{ws_port}/ws/run/<id>")
    except Exception as ex:
        print(f"WS server failed to start: {ex}")

    server = ThreadingHTTPServer((host, port), _WebUIHandler)
    print(f"Zarathustra web UI running on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

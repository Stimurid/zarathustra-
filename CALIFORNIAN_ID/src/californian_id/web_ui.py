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
          <span class="status" id="status">Готово.</span>
        </div>
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

    runBtn.addEventListener('click', async () => {
      const text = input.value.trim();
      if (!text) {
        statusEl.textContent = 'Нужен текст или файл.';
        return;
      }
      runBtn.disabled = true;
      const t0 = Date.now();
      statusEl.textContent = 'Идет запрос к runtime...';
      output.textContent = 'Совет собирается...\\n\\nЖивой запрос к LLM обычно занимает 60-180 секунд.\\nПодожди и не нажимай кнопку повторно.';
      const timer = setInterval(() => {
        const dt = Math.floor((Date.now() - t0) / 1000);
        statusEl.textContent = `Идет запрос к runtime... ${dt}s`;
      }, 1000);
      try {
        const response = await fetch('api/run', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            text,
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
          })
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
      } catch (error) {
        output.textContent = String(error);
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
        )
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
    if mode == "strict_card":
        return (
            "Stay tightly anchored to the selected card. Reuse its operation, distinction, and risk logic closely. "
            "Do not widen into extra frameworks unless they are necessary to make the card intelligible in the current scene."
        )
    if mode == "freer_synthesis":
        return (
            "Use the selected card as an anchor, but allow wider synthesis, analogy, and recombination if the scene clearly demands it. "
            "Grounding must remain legible, yet the response may move beyond the card's immediate wording."
        )
    return (
        "Keep the selected card as the primary anchor, but develop it into a fuller argument responsive to the scene. "
        "You may widen one level beyond the card, but do not drift into generic abstract commentary."
    )


def _assembly_instruction(mode: str) -> str:
    if mode == "verdict":
        return (
            "Assemble toward a verdict. Name the strongest line, expose the weaker one, and state what should be retained or discarded."
        )
    if mode == "dissent_forward":
        return (
            "Assemble around the live fracture. Preserve the most important disagreement and let the answer move through that unresolved tension."
        )
    if mode == "diagnostic":
        return (
            "Assemble as diagnosis. Identify the central framing error, false assumption, or hidden confusion that deforms the whole discussion."
        )
    if mode == "projective":
        return (
            "Assemble toward the next move. Convert the council into a sharper next question, test, project step, or redesign of the scene."
        )
    if mode == "roast":
        return (
            "Assemble as merciless compassionate roast. Show the true form of the weak construction, expose its evasions, theatrical substitutes, "
            "missing courage, and false solidity. Be devastating to the bad frame, but not sadistic toward the humans inside it. "
            "Mercy stays with persons; destruction falls on confusion, vanity, cowardice, and fake architecture."
        )
    return (
        "Assemble as synthesis. Hold multiple live lines together without erasing real differences, and produce a coherent final answer."
    )


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
    expected = os.environ.get(COMPAT_API_KEY_ENV) or ""
    if not expected:
        return False
    return _extract_bearer_token(handler) == expected


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

    def do_GET(self) -> None:  # noqa: N802
        path_only = self.path.split("?", 1)[0]
        self.path = path_only
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
        if self.path in {"/v1/chat/completions"}:
            if not _compat_key_is_valid(self):
                self._send_json({"error": {"message": "unauthorized", "type": "invalid_request_error"}}, status=HTTPStatus.UNAUTHORIZED)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length)
                data = json.loads(raw.decode("utf-8"))
                payload = _run_compat_chat_completion(data)
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
            )
            self._send_json(payload)
        except Exception as exc:  # pragma: no cover
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

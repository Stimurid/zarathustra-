<script lang="ts">
  import { onDestroy } from 'svelte';
  import { WSClient } from './wsClient';
  import { council, applyEvent, resetCouncil } from './stores.svelte';
  import PauseResumeBar from './components/PauseResumeBar.svelte';
  import PersonaSliders from './components/PersonaSliders.svelte';
  import RouteOverridePreview from './components/RouteOverridePreview.svelte';
  import InsertVoicePanel from './components/InsertVoicePanel.svelte';
  import AttachFileButton from './components/AttachFileButton.svelte';
  import CouncilTimeline from './components/CouncilTimeline.svelte';
  import ClosingStream from './components/ClosingStream.svelte';
  import InterventionLog from './components/InterventionLog.svelte';

  let inputText = $state('');
  let runIdInput = $state('');
  let token = $state('');
  let client: WSClient | null = $state(null);
  let starting = $state(false);
  let startError = $state('');

  async function startRun(): Promise<void> {
    startError = '';
    if (!inputText.trim()) { startError = 'text required'; return; }
    starting = true;
    resetCouncil();
    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const resp = await fetch('/api/run/async', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          text: inputText, mode: 'fast', runtime_layer: 'californian_id',
          workspace_id: council.workspaceId || 'default'
        })
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      runIdInput = data.run_id;
      subscribe(data.run_id);
    } catch (e) {
      startError = String(e);
    } finally {
      starting = false;
    }
  }

  function subscribe(runId: string): void {
    if (!runId) return;
    if (client) client.close();
    resetCouncil();
    council.runId = runId;
    client = new WSClient(runId, token || undefined);
    const unsub = client.onEvent(applyEvent);
    const unsubState = client.onState((s) => { council.connState = s; });
    client.connect();
  }

  onDestroy(() => { if (client) client.close(); });

  function connectToExisting(): void {
    if (runIdInput) subscribe(runIdInput);
  }
</script>

<main>
  <header>
    <h1>Tinkuy Live <span style="font-size:0.6em;color:var(--muted);">B-5.5 Веха 4</span></h1>
    <p style="color:var(--muted);margin:0 0 16px;">
      Живой совет в реальном времени. Веди поток бегунками, вставляй свои
      реплики, приостанавливай ход, перебивай маршрутизатора.
    </p>
  </header>

  <section class="card">
    <label style="display:block;margin-bottom:8px;">
      Токен (JWT — если auth включён):
      <input type="text" bind:value={token} style="width:100%;margin-top:4px;font-family:monospace;font-size:0.85rem;" placeholder="eyJ..." />
    </label>
    <label style="display:block;margin-bottom:8px;">Рабочее пространство:
      <input type="text" bind:value={council.workspaceId} style="width:14em;margin-left:6px;" />
    </label>
    <label style="display:block;margin-bottom:8px;">Текст для совета:
      <textarea bind:value={inputText} placeholder="Вставь вопрос или транскрипт..."></textarea>
    </label>
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
      <button onclick={startRun} disabled={starting || !inputText.trim()}>
        {starting ? 'Запуск...' : '▶ Запустить совет'}
      </button>
      <span style="color:var(--muted);">или подключись к идущему:</span>
      <input type="text" bind:value={runIdInput} placeholder="run_id" style="min-width:22em;font-family:monospace;" />
      <button class="ghost" onclick={connectToExisting} disabled={!runIdInput}>Подключиться</button>
      {#if startError}<span style="color:var(--cancelled);">{startError}</span>{/if}
    </div>
    {#if council.runId}
      <p style="margin-top:10px;color:var(--muted);font-size:0.9rem;">
        <span class="pill">{council.connState}</span>
        run <code>{council.runId}</code>
        {#if council.topic} · topic: <b>{council.topic}</b>{/if}
        · <span class="pill {council.runState.toLowerCase()}">{council.runState}</span>
      </p>
    {/if}
  </section>

  {#if client}
    <div style="display:grid;grid-template-columns:minmax(0,1.4fr) minmax(280px,0.7fr);gap:12px;">
      <div>
        <PauseResumeBar {client} />
        <RouteOverridePreview {client} />
        <CouncilTimeline />
        <ClosingStream />
      </div>
      <div>
        <PersonaSliders {client} />
        <InsertVoicePanel {client} />
        <AttachFileButton {client} />
        <InterventionLog />
      </div>
    </div>
  {:else}
    <p style="color:var(--muted);text-align:center;padding:2em;">
      Запусти совет или подключись к идущему run_id, чтобы начать наблюдение.
    </p>
  {/if}
</main>

<style>
  main {
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px 20px 48px;
  }
  h1 { margin: 0 0 4px; font-size: clamp(1.8rem, 3vw, 2.6rem); letter-spacing: -0.02em; }
  @media (max-width: 900px) {
    main > div { grid-template-columns: 1fr !important; }
  }
</style>

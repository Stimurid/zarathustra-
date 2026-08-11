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
  let token = $state(localStorage.getItem('tinkuy_jwt') || '');
  let client: WSClient | null = $state(null);
  let starting = $state(false);
  let startError = $state('');

  // Login form state
  let showLogin = $state(false);
  let loginUsername = $state('');
  let loginPassword = $state('');
  let loginError = $state('');
  let loggingIn = $state(false);
  let currentUser = $state<{username: string; roles: string[]} | null>(null);

  async function login(): Promise<void> {
    loginError = '';
    if (!loginUsername || !loginPassword) { loginError = 'заполни оба поля'; return; }
    loggingIn = true;
    try {
      const resp = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username: loginUsername, password: loginPassword})
      });
      const data = await resp.json();
      if (!resp.ok) { loginError = data.error || `HTTP ${resp.status}`; return; }
      token = data.token;
      currentUser = data.user;
      localStorage.setItem('tinkuy_jwt', token);
      showLogin = false;
      loginPassword = '';
    } catch (e) {
      loginError = String(e);
    } finally {
      loggingIn = false;
    }
  }

  function logout(): void {
    token = '';
    currentUser = null;
    localStorage.removeItem('tinkuy_jwt');
    if (client) { client.close(); client = null; }
  }

  async function checkToken(): Promise<void> {
    if (!token) return;
    try {
      const resp = await fetch('/api/auth/me', {
        headers: {'Authorization': `Bearer ${token}`}
      });
      if (resp.ok) currentUser = await resp.json();
      else { token = ''; localStorage.removeItem('tinkuy_jwt'); }
    } catch { /* ignore */ }
  }
  if (token) checkToken();

  function makeClientRunId(): string {
    // B-5.5 race-fix v2: client-provided run_id для subscribe-first pattern.
    // Backend валидирует по ^run_[a-z0-9_-]{8,56}$
    const uuid = (crypto.randomUUID?.() ?? Math.random().toString(36).slice(2))
      .replace(/-/g, '').slice(0, 24).toLowerCase();
    return `run_${uuid}`;
  }

  async function startRun(): Promise<void> {
    startError = '';
    if (!inputText.trim()) { startError = 'text required'; return; }
    starting = true;
    resetCouncil();
    try {
      // 1. Генерируем run_id сами
      const clientRunId = makeClientRunId();
      runIdInput = clientRunId;

      // 2. Открываем WS с этим run_id, ждём hello frame
      if (client) client.close();
      council.runId = clientRunId;
      client = new WSClient(clientRunId, token || undefined);
      client.onEvent(applyEvent);
      client.onState((s) => { council.connState = s; });
      client.connect();
      try {
        await client.awaitHello(8000);
      } catch (e) {
        throw new Error('WS not ready: ' + String(e));
      }

      // 3. Теперь POST run с тем же ID — subscribe уже стоит, events дойдут
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const resp = await fetch('/api/run/async', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          run_id: clientRunId,
          text: inputText,
          mode: 'fast',
          runtime_layer: 'californian_id',
          workspace_id: council.workspaceId || 'default'
        })
      });
      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({error: `HTTP ${resp.status}`}));
        throw new Error(errData.error || `HTTP ${resp.status}`);
      }
    } catch (e) {
      startError = String(e);
      if (client) { client.close(); client = null; }
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
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
      <div>
        {#if currentUser}
          <span class="pill" style="background:#dfe;">
            👤 {currentUser.username}
            {#if currentUser.roles?.length}
              <span style="color:var(--muted);font-size:0.8em;">
                · {currentUser.roles.join(', ')}
              </span>
            {/if}
          </span>
          <button class="ghost" onclick={logout} style="margin-left:6px;font-size:0.85em;">
            Выйти
          </button>
        {:else}
          <button class="ghost" onclick={() => showLogin = !showLogin}
                  style="font-size:0.85em;">
            🔐 {showLogin ? 'Скрыть' : 'Войти'}
          </button>
          <span style="color:var(--muted);font-size:0.85em;margin-left:8px;">
            (или AUTH_DISABLED=1 для dev)
          </span>
        {/if}
      </div>
    </div>

    {#if showLogin && !currentUser}
      <div class="card" style="background:#faf7f0;margin-bottom:12px;">
        <b>Логин</b>
        <div style="display:grid;grid-template-columns:1fr 1fr auto;gap:8px;margin-top:8px;align-items:center;">
          <input type="text" bind:value={loginUsername} placeholder="username"
                 onkeydown={(e) => e.key === 'Enter' && login()} />
          <input type="password" bind:value={loginPassword} placeholder="password"
                 onkeydown={(e) => e.key === 'Enter' && login()} />
          <button onclick={login} disabled={loggingIn}>
            {loggingIn ? '...' : 'Войти'}
          </button>
        </div>
        {#if loginError}
          <p style="color:var(--cancelled);margin:6px 0 0;font-size:0.85em;">{loginError}</p>
        {/if}
        <p style="color:var(--muted);font-size:0.8em;margin:6px 0 0;">
          Создать пользователя: <code>python -m californian_id users add &lt;name&gt;</code>
        </p>
      </div>
    {/if}

    <details style="margin-bottom:10px;">
      <summary style="cursor:pointer;color:var(--muted);font-size:0.85em;">
        Ручной токен (JWT)
      </summary>
      <input type="text" bind:value={token}
             style="width:100%;margin-top:4px;font-family:monospace;font-size:0.85rem;"
             placeholder="eyJ..." />
    </details>
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

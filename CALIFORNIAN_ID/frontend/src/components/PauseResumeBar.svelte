<script lang="ts">
  import type { WSClient } from '../wsClient';
  import { council } from '../stores.svelte';

  let { client }: { client: WSClient } = $props();

  function pause() { client.intervention('pause'); }
  function resume() { client.intervention('resume'); }
  function cancel() {
    if (!confirm('Отменить ран? Текущий срез будет сохранён.')) return;
    client.intervention('cancel', { reason: 'user_ui_cancel' });
  }
</script>

<div class="card" style="display:flex;gap:10px;align-items:center;">
  <b style="margin-right:6px;">Контроль:</b>
  <button class="secondary" onclick={pause} disabled={council.runState !== 'RUNNING'}>⏸ Pause</button>
  <button class="secondary" onclick={resume} disabled={council.runState !== 'PAUSED'}>▶ Resume</button>
  <button onclick={cancel}
          disabled={council.runState === 'COMPLETED' || council.runState === 'CANCELLED'}>
    ⏹ Cancel
  </button>
  <span style="margin-left:auto;color:var(--muted);font-size:0.9rem;">
    ходов: {council.turns.length}
  </span>
</div>

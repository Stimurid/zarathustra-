<script lang="ts">
  import type { WSClient } from '../wsClient';
  import { council } from '../stores.svelte';

  let { client }: { client: WSClient } = $props();
  let utterance = $state('');
  let attachTo = $state('');

  function inject(): void {
    if (!utterance.trim()) return;
    client.intervention('user_voice', {
      utterance: utterance.trim(),
      author: 'ui_user',
      attach_to_persona: attachTo || undefined
    });
    utterance = '';
  }
</script>

<div class="card" style="border-left:3px solid var(--user);">
  <b>Твой голос</b>
  <p style="color:var(--muted);font-size:0.85rem;margin:4px 0 8px;">
    Реплика попадёт в тело совета как ход <code>USER_VOICE</code>.
  </p>
  <textarea bind:value={utterance} placeholder="Твой аргумент, вопрос, замечание..."></textarea>
  <div style="display:flex;gap:6px;margin-top:6px;align-items:center;">
    <select bind:value={attachTo} style="padding:6px;border:1px solid var(--line);border-radius:8px;flex:1;">
      <option value="">без привязки</option>
      {#each council.personas as p}<option value={p}>усилить {p.replace('LENS_', '')}</option>{/each}
    </select>
    <button onclick={inject} disabled={!utterance.trim()}>Вставить</button>
  </div>
</div>

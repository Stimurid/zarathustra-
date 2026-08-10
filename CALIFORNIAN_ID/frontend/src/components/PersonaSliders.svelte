<script lang="ts">
  import type { WSClient } from '../wsClient';
  import { council } from '../stores.svelte';

  let { client }: { client: WSClient } = $props();
  let pendingWeights: Record<string, number> = $state({});
  let debounceTimer: number | null = null;

  function onSlide(personaId: string, value: number): void {
    pendingWeights[personaId] = value;
    if (debounceTimer !== null) clearTimeout(debounceTimer);
    debounceTimer = window.setTimeout(() => {
      client.intervention('slider', { weights: { ...pendingWeights } });
      // локально обновим тоже, чтобы отражалось
      for (const [k, v] of Object.entries(pendingWeights)) council.personaWeights[k] = v;
      pendingWeights = {};
    }, 300);
  }

  function labelFor(v: number): string {
    if (v <= 0.1) return 'muted';
    if (v < 0.7) return 'quiet';
    if (v < 1.3) return 'normal';
    if (v < 2.2) return 'boosted';
    return 'loud';
  }
</script>

<div class="card">
  <b>Голоса</b>
  <p style="color:var(--muted);font-size:0.85rem;margin:4px 0 10px;">
    Бегунок ≤ 0.1 = mute на ход. Изменения применяются со следующего хода.
  </p>
  {#if council.personas.length === 0}
    <p style="color:var(--muted);font-style:italic;">cast ещё не выбран</p>
  {:else}
    {#each council.personas as p}
      {@const w = council.personaWeights[p] ?? 1.0}
      <div style="margin-bottom:10px;">
        <div style="display:flex;justify-content:space-between;font-size:0.88rem;">
          <span title={p}><code>{p.replace('LENS_', '')}</code></span>
          <span style="color:var(--muted);">{w.toFixed(2)} · {labelFor(w)}</span>
        </div>
        <input type="range" min="0.05" max="3.0" step="0.05" value={w}
               oninput={(e) => onSlide(p, parseFloat((e.target as HTMLInputElement).value))}
               style="width:100%;" />
      </div>
    {/each}
  {/if}
</div>

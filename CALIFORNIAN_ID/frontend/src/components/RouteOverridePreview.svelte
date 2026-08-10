<script lang="ts">
  import type { WSClient } from '../wsClient';
  import { council } from '../stores.svelte';

  let { client }: { client: WSClient } = $props();

  const OPERATIONS = ['attack', 'attack_presupposition', 'defend', 'steelman_opponent',
                      'shift_ontology', 'shift_scale', 'shift_temporal_horizon',
                      'build_future_image', 'build_counterexample',
                      'problematize_question', 'create_aporia', 'test_value',
                      'show_cost', 'draw_practical_implication',
                      'propose_alliance', 'refuse_alliance',
                      'introduce_absent_subject', 'restore_ground'];

  let overridePersona = $state('');
  let overrideOp = $state('attack');
  let overrideReason = $state('');

  function sendSteer(): void {
    if (!overridePersona) return;
    client.intervention('steer', {
      persona_id: overridePersona,
      operation: overrideOp,
      reason: overrideReason || 'user override'
    });
    overrideReason = '';
  }
</script>

<div class="card" style="border-left:3px solid var(--accent-2);">
  <b>Следующий ход</b>
  {#if council.nextPreview}
    <p style="margin:6px 0;">
      Заратустра выбрал:
      <span class="pill">{council.nextPreview.persona.replace('LENS_', '')}</span>
      <span class="pill">{council.nextPreview.operation}</span>
      {#if council.nextPreview.wasSteer}<span class="pill user">твой override</span>{/if}
    </p>
    <p style="color:var(--muted);font-size:0.85rem;margin:4px 0 8px;">
      причина: {council.nextPreview.reason || '—'}
    </p>
  {:else}
    <p style="color:var(--muted);font-style:italic;margin:6px 0 8px;">
      preview следующего хода появится здесь
    </p>
  {/if}

  <details>
    <summary style="cursor:pointer;color:var(--accent-2);font-size:0.9rem;">🎯 Перебить маршрутизацию</summary>
    <div style="margin-top:8px;display:grid;grid-template-columns:1fr 1fr;gap:6px;">
      <select bind:value={overridePersona} style="padding:6px;border:1px solid var(--line);border-radius:8px;">
        <option value="">— персона —</option>
        {#each council.personas as p}<option value={p}>{p.replace('LENS_', '')}</option>{/each}
      </select>
      <select bind:value={overrideOp} style="padding:6px;border:1px solid var(--line);border-radius:8px;">
        {#each OPERATIONS as op}<option value={op}>{op}</option>{/each}
      </select>
    </div>
    <input type="text" bind:value={overrideReason} placeholder="причина (опционально)"
           style="width:100%;margin-top:6px;" />
    <button onclick={sendSteer} disabled={!overridePersona} style="margin-top:8px;">
      Отправить override
    </button>
  </details>
</div>

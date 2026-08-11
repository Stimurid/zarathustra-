<script lang="ts">
  import type { WSClient } from '../wsClient';
  import { council } from '../stores.svelte';
  import { onDestroy } from 'svelte';

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

  // B-5.5 обход: countdown modal — при route_previewed эмится, у юзера
  // 3 секунды на override перед реальным turn'ом. Пример: рeдкий turn
  // (persona не голосовала долго) — можно быстро направить.
  const COUNTDOWN_SEC = 3;
  let countdownRemaining = $state(0);
  let countdownTimer: number | null = null;

  // Reactive: при новом nextPreview стартуем countdown
  let lastPreviewTurn = $state(-1);
  $effect(() => {
    if (council.nextPreview && council.nextPreview.turn_index !== lastPreviewTurn) {
      lastPreviewTurn = council.nextPreview.turn_index;
      startCountdown();
    }
  });

  function startCountdown(): void {
    stopCountdown();
    // Не показываем countdown если это уже был user_steer (юзер сам выбрал)
    if (council.nextPreview?.wasSteer) return;
    countdownRemaining = COUNTDOWN_SEC;
    countdownTimer = window.setInterval(() => {
      countdownRemaining -= 1;
      if (countdownRemaining <= 0) stopCountdown();
    }, 1000);
  }

  function stopCountdown(): void {
    if (countdownTimer !== null) {
      clearInterval(countdownTimer);
      countdownTimer = null;
    }
    countdownRemaining = 0;
  }

  onDestroy(stopCountdown);

  function sendSteer(): void {
    if (!overridePersona) return;
    client.intervention('steer', {
      persona_id: overridePersona,
      operation: overrideOp,
      reason: overrideReason || 'user override'
    });
    overrideReason = '';
    stopCountdown();
  }

  function quickInterrupt(): void {
    // Отправляем pause; юзер может дальше выбрать steer/user_voice спокойно
    client.intervention('pause');
    stopCountdown();
  }
</script>

<div class="card" style="border-left:3px solid var(--accent-2);
       {countdownRemaining > 0 ? 'box-shadow: 0 0 0 3px rgba(217,119,6,0.3); animation: pulse 1s infinite;' : ''}">
  <b>Следующий ход</b>
  {#if countdownRemaining > 0}
    <span class="pill paused" style="margin-left:8px;">
      ⏱ через {countdownRemaining}с
    </span>
    <button class="ghost" onclick={quickInterrupt}
            style="float:right;padding:4px 10px;font-size:0.85em;">
      ⏸ перехватить
    </button>
  {/if}
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

<style>
  @keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 3px rgba(217,119,6,0.3); }
    50% { box-shadow: 0 0 0 6px rgba(217,119,6,0.15); }
  }
</style>

<script lang="ts">
  import { council } from '../stores.svelte';
  import TurnCard from './TurnCard.svelte';
</script>

<div class="card">
  <b>Ход совета <span style="color:var(--muted);font-weight:normal;">({council.turns.length})</span></b>
  {#if council.turns.length === 0}
    <p style="color:var(--muted);font-style:italic;margin:8px 0;">
      совет ещё не начал говорить
    </p>
  {/if}
  <div style="display:flex;flex-direction:column;gap:8px;margin-top:8px;">
    {#each council.turns as turn (turn.turn_index + ':' + turn.persona_id)}
      <TurnCard {turn} />
    {/each}
  </div>
</div>

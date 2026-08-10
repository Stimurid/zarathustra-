<script lang="ts">
  import { council } from '../stores.svelte';

  function fmtTime(ms: number): string {
    const d = new Date(ms);
    return d.toLocaleTimeString('ru-RU');
  }
</script>

<div class="card" style="border-left:3px solid var(--muted);">
  <b>Журнал интервенций</b>
  {#if council.interventions.length === 0}
    <p style="color:var(--muted);font-style:italic;font-size:0.85rem;margin:6px 0;">
      пока пусто
    </p>
  {:else}
    <ul style="list-style:none;padding:0;margin:6px 0 0;">
      {#each council.interventions.slice().reverse() as iv}
        <li style="padding:4px 0;border-bottom:1px dashed var(--line);font-size:0.82rem;">
          <span class="pill">{iv.kind}</span>
          <code style="font-size:0.75rem;color:var(--muted);">{iv.intervention_id.slice(0, 12)}</code>
          <span style="float:right;color:var(--muted);">{fmtTime(iv.at)}</span>
        </li>
      {/each}
    </ul>
  {/if}
</div>

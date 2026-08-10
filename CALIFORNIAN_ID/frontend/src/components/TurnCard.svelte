<script lang="ts">
  import type { TurnRecord } from '../types';

  let { turn }: { turn: TurnRecord } = $props();
  let expanded = $state(true);

  const isUser = turn.persona_id === 'USER_VOICE';
</script>

<div style="border:1px solid var(--line);border-radius:12px;padding:10px 12px;background:{isUser ? '#f7f3ff' : '#fffdf8'};border-left:3px solid {isUser ? 'var(--user)' : 'var(--accent)'};">
  <div style="display:flex;justify-content:space-between;align-items:baseline;cursor:pointer;"
       onclick={() => expanded = !expanded}
       role="button" tabindex="0">
    <div>
      <span style="color:var(--muted);font-size:0.85rem;">T{turn.turn_index}</span>
      <b style="margin:0 6px;color:{isUser ? 'var(--user)' : 'var(--accent)'};">{turn.persona_id.replace('LENS_', '')}</b>
      <span class="pill">{turn.operation}</span>
      {#if turn.confidence !== undefined}
        <span style="color:var(--muted);font-size:0.8rem;">conf {turn.confidence.toFixed(2)}</span>
      {/if}
    </div>
    <span style="color:var(--muted);">{expanded ? '▾' : '▸'}</span>
  </div>
  {#if expanded}
    <div style="margin-top:8px;line-height:1.5;white-space:pre-wrap;">{turn.utterance}</div>
  {/if}
</div>

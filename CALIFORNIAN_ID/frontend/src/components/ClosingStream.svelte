<script lang="ts">
  import { council } from '../stores.svelte';
</script>

{#if council.completion}
  <div class="card" style="border-left:3px solid var(--accent-2);">
    <b>Заключительная речь</b>
    <span class="pill" style="margin-left:8px;">форма: {council.completion.form}</span>
    <div style="margin-top:10px;line-height:1.6;white-space:pre-wrap;font-size:1.02rem;">
      {council.completion.closing}
      {#if council.runState !== 'COMPLETED'}
        <span style="color:var(--accent);animation:blink 1s infinite;">▊</span>
      {/if}
    </div>
  </div>
{/if}

<style>
  @keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
  }
</style>

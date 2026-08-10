<script lang="ts">
  import type { WSClient } from '../wsClient';
  import { council } from '../stores.svelte';

  let { client }: { client: WSClient } = $props();
  let attaching = $state(false);
  let attachTo = $state('');
  let attached: string[] = $state([]);

  async function handleFile(file: File): Promise<void> {
    attaching = true;
    try {
      const text = await file.text();
      client.intervention('attach_file', {
        filename: file.name,
        content: text.slice(0, 30000),
        attach_to_persona: attachTo || undefined
      });
      attached = [...attached, `${file.name} (${(file.size / 1024).toFixed(1)}KB)`];
    } catch (e) {
      attached = [...attached, `error: ${e}`];
    } finally {
      attaching = false;
    }
  }
</script>

<div class="card" style="border-left:3px solid var(--accent);">
  <b>Прикрепить файл</b>
  <p style="color:var(--muted);font-size:0.85rem;margin:4px 0 6px;">
    MD/TXT/JSON до 30KB. Веха 5 добавит extractor для PDF/DOCX.
  </p>
  <select bind:value={attachTo} style="width:100%;padding:6px;border:1px solid var(--line);border-radius:8px;margin-bottom:6px;">
    <option value="">без привязки к голосу</option>
    {#each council.personas as p}<option value={p}>усилить {p.replace('LENS_', '')}</option>{/each}
  </select>
  <input type="file" accept=".md,.txt,.json"
         onchange={(e) => {
           const f = (e.target as HTMLInputElement).files?.[0];
           if (f) handleFile(f);
         }} disabled={attaching} />
  {#if attached.length > 0}
    <ul style="margin-top:6px;padding-left:20px;font-size:0.82rem;color:var(--muted);">
      {#each attached as name}<li>{name}</li>{/each}
    </ul>
  {/if}
</div>

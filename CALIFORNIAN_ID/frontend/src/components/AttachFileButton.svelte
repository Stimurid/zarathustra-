<script lang="ts">
  import type { WSClient } from '../wsClient';
  import { council } from '../stores.svelte';

  let { client }: { client: WSClient } = $props();
  let attaching = $state(false);
  let attachTo = $state('');
  let attached: string[] = $state([]);

  const TEXT_EXT = new Set(['md', 'txt', 'json', 'yaml', 'yml', 'csv', 'tsv']);
  const BINARY_EXT = new Set(['pdf', 'docx']);

  function extOf(name: string): string {
    const dot = name.lastIndexOf('.');
    return dot >= 0 ? name.slice(dot + 1).toLowerCase() : '';
  }

  function bytesToBase64(bytes: Uint8Array): string {
    let binary = '';
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
      binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
    }
    return btoa(binary);
  }

  async function handleFile(file: File): Promise<void> {
    attaching = true;
    try {
      const ext = extOf(file.name);
      const payload: any = {
        filename: file.name,
        attach_to_persona: attachTo || undefined,
      };
      if (TEXT_EXT.has(ext)) {
        const text = await file.text();
        payload.content = text.slice(0, 50_000);
      } else if (BINARY_EXT.has(ext)) {
        const buf = await file.arrayBuffer();
        const bytes = new Uint8Array(buf);
        if (bytes.length > 2_000_000) {
          attached = [...attached, `${file.name} (skipped: >2MB)`];
          return;
        }
        payload.b64_content = bytesToBase64(bytes);
        payload.is_base64 = true;
      } else {
        attached = [...attached, `${file.name} (unsupported ext .${ext})`];
        return;
      }
      client.intervention('attach_file', payload);
      const sizeKb = (file.size / 1024).toFixed(1);
      attached = [...attached, `${file.name} (${sizeKb}KB, .${ext})`];
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
    MD/TXT/JSON/YAML/CSV, PDF, DOCX (до 2MB).
  </p>
  <select bind:value={attachTo} style="width:100%;padding:6px;border:1px solid var(--line);border-radius:8px;margin-bottom:6px;">
    <option value="">без привязки к голосу</option>
    {#each council.personas as p}<option value={p}>усилить {p.replace('LENS_', '')}</option>{/each}
  </select>
  <input type="file" accept=".md,.txt,.json,.yaml,.yml,.csv,.tsv,.pdf,.docx"
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

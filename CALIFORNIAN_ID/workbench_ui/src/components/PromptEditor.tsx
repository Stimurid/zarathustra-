/**
 * C2 — real editor.
 *
 * CodeMirror 6 with genuine cursor/selection state, undo/redo, region
 * decorations (protected / editable), validation markers, provenance-span
 * highlighting and diff-target navigation.
 *
 * The region decorations are an affordance, not a security boundary: the server
 * refuses illegal protected-region mutations independently (see
 * `WorkbenchService.update_source` and `tests/workbench/test_c2_protected_regions.py`).
 */
import { useCallback, useEffect, useImperativeHandle, useRef, forwardRef } from 'react';
import {
  Compartment, EditorState, StateEffect, StateField, type Extension,
} from '@codemirror/state';
import {
  Decoration, EditorView, ViewUpdate, keymap, lineNumbers, highlightActiveLine,
  type DecorationSet,
} from '@codemirror/view';
import { defaultKeymap, history, historyKeymap, redo, undo } from '@codemirror/commands';
import { markdown } from '@codemirror/lang-markdown';
import { oneDark } from '@codemirror/theme-one-dark';

export interface RegionMark { name: string; kind: string; start: number | null; end: number | null; reason?: string; }
export interface SpanMark { target: string; span_start: number; span_end: number; kind: string; region_name?: string; rule_id?: string; }
export interface Marker { from: number; to: number; severity: string; message: string; }

export interface EditorHandle {
  insertAll(text: string): void;
  insertSelection(text: string): void;
  applyDiff(find: string, replace: string): boolean;
  undo(): void;
  redo(): void;
  gotoRegion(name: string): void;
  gotoOffset(offset: number): void;
  getSelection(): { from: number; to: number; text: string };
  getCursor(): number;
}

const setRegions = StateEffect.define<RegionMark[]>();
const setSpans = StateEffect.define<SpanMark[]>();
const setMarkers = StateEffect.define<Marker[]>();

const protectedDeco = Decoration.mark({ class: 'cm-region-protected' });
const editableDeco = Decoration.mark({ class: 'cm-region-editable' });
const spanDeco = Decoration.mark({ class: 'cm-provenance-span' });
const errDeco = Decoration.mark({ class: 'cm-marker-error' });
const warnDeco = Decoration.mark({ class: 'cm-marker-warn' });

function buildField<T>(effect: any, render: (items: T[], docLen: number) => DecorationSet) {
  return StateField.define<DecorationSet>({
    create: () => Decoration.none,
    update(value, tr) {
      value = value.map(tr.changes);
      for (const e of tr.effects) if (e.is(effect)) value = render(e.value as T[], tr.state.doc.length);
      return value;
    },
    provide: (f) => EditorView.decorations.from(f),
  });
}

const clamp = (n: number, len: number) => Math.max(0, Math.min(n, len));

const regionField = buildField<RegionMark>(setRegions, (regions, len) =>
  Decoration.set(regions
    .filter((r) => r.start != null && r.end != null && r.end > r.start)
    .map((r) => (r.kind === 'protected' ? protectedDeco : editableDeco)
      .range(clamp(r.start!, len), clamp(r.end!, len)))
    .sort((a, b) => a.from - b.from), true));

const spanField = buildField<SpanMark>(setSpans, (spans, len) =>
  Decoration.set(spans
    .filter((s) => s.target === 'system' && s.span_end > s.span_start)
    .map((s) => spanDeco.range(clamp(s.span_start, len), clamp(s.span_end, len)))
    .sort((a, b) => a.from - b.from), true));

const markerField = buildField<Marker>(setMarkers, (markers, len) =>
  Decoration.set(markers
    .filter((m) => m.to > m.from)
    .map((m) => (m.severity === 'error' ? errDeco : warnDeco)
      .range(clamp(m.from, len), clamp(m.to, len)))
    .sort((a, b) => a.from - b.from), true));

interface Props {
  value: string;
  readOnly?: boolean;
  regions: RegionMark[];
  spans?: SpanMark[];
  markers?: Marker[];
  onChange(text: string): void;
  onSelectionChange?(sel: { from: number; to: number; text: string }): void;
}

export const PromptEditor = forwardRef<EditorHandle, Props>(function PromptEditor(
  { value, readOnly, regions, spans, markers, onChange, onSelectionChange }, ref,
) {
  const host = useRef<HTMLDivElement>(null);
  const view = useRef<EditorView | null>(null);
  // Defect WB-009: EditorState.readOnly baked in at construction never changed
  // when the working variant switched from BASELINE to a candidate, so the
  // editor stayed silently read-only and edits were dropped. A Compartment
  // makes it reconfigurable.
  const roCompartment = useRef(new Compartment());
  const onChangeRef = useRef(onChange);
  const onSelRef = useRef(onSelectionChange);
  onChangeRef.current = onChange;
  onSelRef.current = onSelectionChange;

  useEffect(() => {
    if (!host.current || view.current) return;
    const extensions: Extension[] = [
      lineNumbers(), history(), highlightActiveLine(),
      keymap.of([...defaultKeymap, ...historyKeymap]),
      markdown(), oneDark,
      regionField, spanField, markerField,
      EditorView.lineWrapping,
      roCompartment.current.of(EditorState.readOnly.of(!!readOnly)),
      EditorView.updateListener.of((u: ViewUpdate) => {
        if (u.docChanged) onChangeRef.current(u.state.doc.toString());
        if (u.selectionSet && onSelRef.current) {
          const r = u.state.selection.main;
          onSelRef.current({ from: r.from, to: r.to,
            text: u.state.doc.sliceString(r.from, r.to) });
        }
      }),
    ];
    view.current = new EditorView({
      state: EditorState.create({ doc: value, extensions }),
      parent: host.current,
    });
    return () => { view.current?.destroy(); view.current = null; };
  }, []);

  // external value / readOnly sync
  useEffect(() => {
    const v = view.current; if (!v) return;
    if (v.state.doc.toString() !== value) {
      v.dispatch({ changes: { from: 0, to: v.state.doc.length, insert: value } });
    }
  }, [value]);

  useEffect(() => {
    const v = view.current; if (!v) return;
    v.dispatch({ effects: roCompartment.current.reconfigure(
      EditorState.readOnly.of(!!readOnly)) });
  }, [readOnly]);

  useEffect(() => {
    const v = view.current; if (!v) return;
    v.dispatch({ effects: [
      setRegions.of(regions || []),
      setSpans.of(spans || []),
      setMarkers.of(markers || []),
    ] });
  }, [regions, spans, markers, value]);

  const dispatchReplace = useCallback((from: number, to: number, insert: string) => {
    const v = view.current; if (!v) return;
    v.dispatch({ changes: { from, to, insert },
      selection: { anchor: from + insert.length } });
    v.focus();
  }, []);

  useImperativeHandle(ref, (): EditorHandle => ({
    insertAll(text) {
      const v = view.current; if (!v) return;
      const r = v.state.selection.main;
      dispatchReplace(r.from, r.to, text);          // replaces selection if any
    },
    insertSelection(text) {
      const v = view.current; if (!v) return;
      const r = v.state.selection.main;
      dispatchReplace(r.from, r.to, text);
    },
    applyDiff(find, replace) {
      const v = view.current; if (!v) return false;
      const doc = v.state.doc.toString();
      const idx = doc.indexOf(find);
      if (idx < 0) return false;
      dispatchReplace(idx, idx + find.length, replace);
      return true;
    },
    undo() { if (view.current) undo(view.current); },
    redo() { if (view.current) redo(view.current); },
    gotoRegion(name) {
      const r = regions.find((x) => x.name === name);
      if (!r || r.start == null) return;
      this.gotoOffset(r.start);
    },
    gotoOffset(offset) {
      const v = view.current; if (!v) return;
      const pos = clamp(offset, v.state.doc.length);
      v.dispatch({ selection: { anchor: pos },
        effects: EditorView.scrollIntoView(pos, { y: 'center' }) });
      v.focus();
    },
    getSelection() {
      const v = view.current;
      if (!v) return { from: 0, to: 0, text: '' };
      const r = v.state.selection.main;
      return { from: r.from, to: r.to, text: v.state.doc.sliceString(r.from, r.to) };
    },
    getCursor() { return view.current ? view.current.state.selection.main.head : 0; },
  }), [regions, dispatchReplace]);

  return <div className="cm-host" ref={host} data-testid="prompt-editor" />;
});

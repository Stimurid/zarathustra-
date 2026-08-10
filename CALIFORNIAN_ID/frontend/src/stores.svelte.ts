// Svelte 5 runes-based reactive council state.
import type { Event, TurnRecord, ConnectionState } from './types';

type Snapshot = {
  runId: string;
  workspaceId: string;
  mode: string;
  topic: string;
  genre: string;
  personas: string[];
  personaWeights: Record<string, number>;
  turns: TurnRecord[];
  interventions: any[];
  nextPreview: { turn_index: number; persona: string; operation: string; reason: string; wasSteer: boolean } | null;
  runState: 'IDLE' | 'RUNNING' | 'PAUSED' | 'CANCELLING' | 'CANCELLED' | 'COMPLETED';
  completion: { form: string; reason: string; closing: string } | null;
  connState: ConnectionState;
  errors: string[];
};

// One global reactive store — Svelte 5 $state rune.
export const council = $state<Snapshot>({
  runId: '',
  workspaceId: 'default',
  mode: 'fast',
  topic: '',
  genre: '',
  personas: [],
  personaWeights: {},
  turns: [],
  interventions: [],
  nextPreview: null,
  runState: 'IDLE',
  completion: null,
  connState: 'idle',
  errors: []
});

export function resetCouncil(): void {
  council.runId = '';
  council.topic = '';
  council.genre = '';
  council.personas = [];
  council.personaWeights = {};
  council.turns = [];
  council.interventions = [];
  council.nextPreview = null;
  council.runState = 'IDLE';
  council.completion = null;
  council.errors = [];
}

export function applyEvent(evt: Event): void {
  switch (evt.kind) {
    case 'hello':
      council.runId = evt.run_id;
      if (evt.state_snapshot?.workspace_id) {
        council.workspaceId = evt.state_snapshot.workspace_id;
      }
      if (evt.state_snapshot?.persona_weights) {
        council.personaWeights = { ...evt.state_snapshot.persona_weights };
      }
      if (evt.state_snapshot?.state) {
        council.runState = evt.state_snapshot.state as any;
      }
      break;
    case 'run_started':
      council.runId = evt.run_id;
      council.workspaceId = evt.workspace_id;
      council.mode = evt.mode;
      council.runState = 'RUNNING';
      break;
    case 'situation_reading_done':
      council.topic = evt.topic;
      council.genre = evt.genre;
      break;
    case 'cast_selected':
      council.personas = evt.personas;
      // init weights = 1.0 if not set
      for (const p of evt.personas) {
        if (!(p in council.personaWeights)) council.personaWeights[p] = 1.0;
      }
      break;
    case 'route_previewed':
      council.nextPreview = {
        turn_index: evt.turn_index,
        persona: evt.next_persona,
        operation: evt.operation,
        reason: evt.reason,
        wasSteer: evt.was_user_steer
      };
      break;
    case 'turn_completed':
      council.turns.push({
        turn_index: evt.turn_index,
        persona_id: evt.persona_id,
        operation: evt.operation,
        utterance: evt.utterance,
        confidence: evt.confidence
      });
      council.nextPreview = null;
      break;
    case 'user_voice_injected':
      council.turns.push({
        turn_index: evt.turn_index,
        persona_id: 'USER_VOICE',
        operation: 'user_intervention',
        utterance: evt.utterance,
        was_user_steer: true
      });
      break;
    case 'closing_speech_start':
      council.completion = { form: evt.form, reason: '', closing: '' };
      break;
    case 'closing_speech_delta':
      if (council.completion) council.completion.closing += evt.delta;
      break;
    case 'closing_speech_complete':
      // no-op: closing уже накопился
      break;
    case 'paused':
      council.runState = 'PAUSED';
      break;
    case 'resumed':
      council.runState = 'RUNNING';
      break;
    case 'cancelled':
      council.runState = 'CANCELLED';
      break;
    case 'run_completed':
      council.runState = 'COMPLETED';
      break;
    case 'error':
      council.errors.push(evt.error);
      break;
    case 'intervention_accepted':
      // добавим в лог интервенций
      council.interventions.push({
        kind: (evt as any).kind_,
        intervention_id: evt.intervention_id,
        at: Date.now()
      });
      break;
  }
}

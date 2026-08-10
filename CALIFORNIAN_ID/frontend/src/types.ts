// Event types matching backend pipeline event_sink emissions.
export type Event =
  | { kind: 'hello'; run_id: string; author: string; state_snapshot: any }
  | { kind: 'run_started'; run_id: string; mode: string; workspace_id: string; input_chars?: number }
  | { kind: 'situation_reading_done'; topic: string; genre: string }
  | { kind: 'cast_selected'; personas: string[]; max_voices: number; max_turns: number }
  | { kind: 'route_previewed'; run_id: string; turn_index: number; next_persona: string; operation: string; reason: string; was_user_steer: boolean }
  | { kind: 'turn_completed'; turn_index: number; persona_id: string; operation: string; utterance: string; confidence?: number }
  | { kind: 'closing_speech_start'; provider: string; model: string; form: string }
  | { kind: 'closing_speech_delta'; delta: string }
  | { kind: 'closing_speech_complete'; chars: number }
  | { kind: 'run_completed'; turns: number; stopping_reason: string; completion_form: string; run_id: string; entrypoint?: string }
  | { kind: 'paused'; run_id: string; at_turn_index: number; reason: string }
  | { kind: 'resumed'; run_id: string; at_turn_index: number }
  | { kind: 'cancelled'; run_id: string; at_turn_index: number; reason: string }
  | { kind: 'checkpoint_reached'; run_id: string; at_turn_index: number }
  | { kind: 'checkpoint_timeout'; run_id: string; at_turn_index: number; note: string }
  | { kind: 'user_voice_injected'; run_id: string; turn_index: number; author: string; persona_hint: string; utterance: string }
  | { kind: 'intervention_accepted'; intervention_id: string; kind_: string }
  | { kind: 'state_snapshot'; run_state: any }
  | { kind: 'pong'; ts: number }
  | { kind: 'error'; error: string }
  | { kind: string; [k: string]: any };

export type TurnRecord = {
  turn_index: number;
  persona_id: string;
  operation: string;
  utterance: string;
  confidence?: number;
  was_user_steer?: boolean;
};

export type InterventionCmd =
  | 'pause' | 'resume' | 'cancel'
  | 'steer' | 'slider' | 'user_voice' | 'attach_file';

export type ConnectionState = 'idle' | 'connecting' | 'open' | 'closed' | 'error';

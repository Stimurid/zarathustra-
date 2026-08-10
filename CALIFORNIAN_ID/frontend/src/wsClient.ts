// B-5.5 Веха 4 — WebSocket клиент с auto-reconnect + exponential backoff.
import type { ConnectionState, Event, InterventionCmd } from './types';

type Listener = (evt: Event) => void;
type StateListener = (state: ConnectionState) => void;

export class WSClient {
  private ws: WebSocket | null = null;
  private url: string;
  private listeners = new Set<Listener>();
  private stateListeners = new Set<StateListener>();
  private state: ConnectionState = 'idle';
  private reconnectAttempts = 0;
  private manualClose = false;
  private pingTimer: number | null = null;

  constructor(runId: string, token?: string) {
    // Определяем ws:// vs wss:// по location.protocol.
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    // Веха 3 wire: WS сервер живёт на HTTP port + 1. Через Caddy — /ws/.
    // На проде Caddy проксирует /ws/* на 8086; локально — прямой connect.
    const wsHost = window.location.host;
    const q = token ? `?token=${encodeURIComponent(token)}` : '';
    this.url = `${scheme}://${wsHost}/ws/run/${encodeURIComponent(runId)}${q}`;
  }

  connect(): void {
    if (this.state === 'open' || this.state === 'connecting') return;
    this.manualClose = false;
    this.setState('connecting');
    try {
      this.ws = new WebSocket(this.url);
    } catch (e) {
      this.setState('error');
      this.scheduleReconnect();
      return;
    }
    this.ws.onopen = () => {
      this.setState('open');
      this.reconnectAttempts = 0;
      this.startPing();
    };
    this.ws.onclose = () => {
      this.stopPing();
      if (this.manualClose) {
        this.setState('closed');
      } else {
        this.setState('closed');
        this.scheduleReconnect();
      }
    };
    this.ws.onerror = () => this.setState('error');
    this.ws.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data) as Event;
        for (const l of this.listeners) l(data);
      } catch (e) { /* ignore */ }
    };
  }

  private scheduleReconnect(): void {
    if (this.manualClose) return;
    this.reconnectAttempts += 1;
    if (this.reconnectAttempts > 8) return;
    const delay = Math.min(30000, 500 * Math.pow(2, this.reconnectAttempts - 1));
    setTimeout(() => this.connect(), delay);
  }

  private startPing(): void {
    this.stopPing();
    this.pingTimer = window.setInterval(() => {
      this.send({ cmd: 'ping', ts: Date.now() });
    }, 15000);
  }

  private stopPing(): void {
    if (this.pingTimer !== null) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  send(msg: object): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  intervention(cmd: InterventionCmd, payload: object = {}): void {
    this.send({ cmd, payload });
  }

  close(): void {
    this.manualClose = true;
    this.stopPing();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setState('closed');
  }

  onEvent(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  onState(listener: StateListener): () => void {
    this.stateListeners.add(listener);
    listener(this.state);
    return () => this.stateListeners.delete(listener);
  }

  private setState(state: ConnectionState): void {
    if (this.state === state) return;
    this.state = state;
    for (const l of this.stateListeners) l(state);
  }
}

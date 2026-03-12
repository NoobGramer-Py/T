// Bridge to the Python brain over WebSocket.
// Handles connection lifecycle, message routing, and reconnection.

const BRAIN_URL         = "ws://127.0.0.1:7891/ws";
const RECONNECT_DELAY   = 3000;
const MAX_RECONNECT_WAIT = 30000;

export type BrainStatus = "connecting" | "online" | "offline";

export interface BrainMessage {
  type: string;
  [key: string]: unknown;
}

type MessageHandler = (msg: BrainMessage) => void;
type StatusHandler  = (status: BrainStatus) => void;

class BrainBridge {
  private ws:               WebSocket | null = null;
  private messageHandlers:  Set<MessageHandler> = new Set();
  private statusHandlers:   Set<StatusHandler>  = new Set();
  private status:           BrainStatus = "offline";
  private reconnectDelay:   number = RECONNECT_DELAY;
  private reconnectTimer:   ReturnType<typeof setTimeout> | null = null;
  private destroyed:        boolean = false;

  connect(): void {
    if (this.ws || this.destroyed) return;
    this._setStatus("connecting");
    console.log(`[bridge] connecting to ${BRAIN_URL}`);

    const ws = new WebSocket(BRAIN_URL);
    this.ws  = ws;

    ws.onopen = () => {
      console.log("[bridge] connected");
      this.reconnectDelay = RECONNECT_DELAY;
      this._setStatus("online");
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data as string) as BrainMessage;
        this.messageHandlers.forEach((h) => h(msg));
      } catch {
        // Malformed message — ignore
      }
    };

    ws.onclose = (event: CloseEvent) => {
      console.log(`[bridge] closed code=${event.code} reason=${event.reason}`);
      this.ws = null;
      if (!this.destroyed) {
        this._setStatus("offline");
        this._scheduleReconnect();
      }
    };

    ws.onerror = (event: Event) => {
      console.error("[bridge] error", event);
    };
  }

  send(payload: BrainMessage): boolean {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
      return true;
    }
    return false;
  }

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onStatus(handler: StatusHandler): () => void {
    this.statusHandlers.add(handler);
    return () => this.statusHandlers.delete(handler);
  }

  getStatus(): BrainStatus {
    return this.status;
  }

  destroy(): void {
    this.destroyed = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
    this.messageHandlers.clear();
    this.statusHandlers.clear();
  }

  private _setStatus(s: BrainStatus): void {
    if (this.status === s) return;
    this.status = s;
    this.statusHandlers.forEach((h) => h(s));
  }

  private _scheduleReconnect(): void {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, this.reconnectDelay);
    this.reconnectDelay = Math.min(this.reconnectDelay * 2, MAX_RECONNECT_WAIT);
  }
}

// Singleton — one bridge for the entire app lifetime
export const bridge = new BrainBridge();

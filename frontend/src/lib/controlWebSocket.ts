import { getWSBaseURL } from "./apiClient";

interface ConnectParams {
    interviewId: string;
    candidateToken: string;
    onOpen: () => void;
    onTerminate: (reason: string) => void;
    onError: (error: Event) => void;
    onClose: (event: CloseEvent) => void;
}

class ControlWebSocket {
    private ws: WebSocket | null = null;
    private heartbeatIntervalId: ReturnType<typeof setInterval> | null = null;
    private heartbeatIntervalSec: number = 10;

    connect(params: ConnectParams): void {
        if (this.ws) {
            if (
                this.ws.readyState === WebSocket.OPEN ||
                this.ws.readyState === WebSocket.CONNECTING
            ) {
                console.warn('[controlWebSocket] Already open or connecting. Skipping duplicate connect.');
                return;
            }
            this.ws.close();
            this.ws = null;
        }

        const { interviewId, candidateToken, onOpen, onTerminate, onError, onClose } = params;


        const wsBase = getWSBaseURL();
        const fullUrl = `${wsBase}/api/v1/proctoring/ws`;
        console.log(`[ControlWebSocket] Connecting to: ${fullUrl}`);
        
        try {
            this.ws = new WebSocket(fullUrl);
        } catch (error) {
            console.error("[ControlWebSocket] Failed to create WebSocket:", error);
            onError(error as Event);
            return;
        }

        this.ws.onopen = () => {
            console.log("[ControlWebSocket] WebSocket opened, sending HANDSHAKE");
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                try {
                    this.ws.send(JSON.stringify({
                        type: "HANDSHAKE",
                        interview_id: interviewId,
                        candidate_token: candidateToken,
                    }));
                } catch (error) {
                    console.error("[ControlWebSocket] Failed to send HANDSHAKE:", error);
                    onError(error as Event);
                }
            }
        };

        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                console.log("[ControlWebSocket] Received message:", message.type);

                if (message.type === "HANDSHAKE_ACK") {
                    this.heartbeatIntervalSec = message.heartbeat_interval_sec || 10;
                    this.startHeartbeat();
                    console.log("[ControlWebSocket] HANDSHAKE_ACK received, connection established");
                    onOpen();
                } else if (message.type === "HEARTBEAT_ACK") {
                    // Do nothing, heartbeat acknowledged
                } else if (message.type === "TERMINATE") {
                    this.stopHeartbeat();
                    const reason = message.payload?.reason || message.detail || "Unknown reason";
                    console.log("[ControlWebSocket] TERMINATE received:", reason);
                    onTerminate(reason);
                    this.ws?.close();
                } else if (message.type === "ERROR") {
                    console.error("[ControlWebSocket] Error from server:", message.detail);
                    const error = new Error(message.detail || "WebSocket error");
                    onError(error as any);
                }
            } catch (error) {
                console.error("[ControlWebSocket] Failed to parse message:", error);
                // Invalid JSON, ignore but log
            }
        };

        this.ws.onerror = (error) => {
            console.error("[ControlWebSocket] WebSocket error:", error);
            onError(error);
        };

        this.ws.onclose = (event) => {
            console.log(`[ControlWebSocket] WebSocket closed: code=${event.code}, reason=${event.reason || 'none'}`);
            this.stopHeartbeat();
            onClose(event);
        };
    }

    disconnect(): void {
        if (!this.ws || this.ws.readyState === WebSocket.CLOSED) return;
        this.stopHeartbeat();
        if (this.ws) {
            this.ws.onclose = null; // Prevent triggering onClose during manual disconnect
            this.ws.onerror = null;
            this.ws.close();
            this.ws = null;
        }
    }

    private startHeartbeat(): void {
        this.stopHeartbeat();
        this.heartbeatIntervalId = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: "HEARTBEAT" }));
            }
        }, this.heartbeatIntervalSec * 1000);
    }

    private stopHeartbeat(): void {
        if (this.heartbeatIntervalId) {
            clearInterval(this.heartbeatIntervalId);
            this.heartbeatIntervalId = null;
        }
    }

    getReadyState(): number {
        return this.ws?.readyState ?? WebSocket.CLOSED;
    }
}

export const controlWebSocket = new ControlWebSocket();

import { getWSBaseURL } from "./apiClient";

interface ConnectParams {
    questionId: string;
    onOpen: () => void;
    onPartialTranscript: (text: string) => void;
    onFinalTranscript: (text: string) => void;
    onAnswerReady: (transcriptId: string) => void;
    onError: (error: Event) => void;
    onClose: () => void;
}

class AnswerWebSocket {
    private _ws: WebSocket | null = null;
    private questionId: string | null = null;
    private _audioChunkCount: number = 0;
    
    get ws(): WebSocket | null {
        return this._ws;
    }

    connect(params: ConnectParams): void {
        const { questionId, onOpen, onPartialTranscript, onFinalTranscript, onAnswerReady, onError, onClose } = params;

        if (this._ws) {
            this.disconnect();
        }

        this.questionId = questionId;
        this._audioChunkCount = 0;

        const wsBase = getWSBaseURL();
        const fullUrl = `${wsBase}/api/v1/answer/ws`;
        console.log(`[AnswerWebSocket] Connecting to: ${fullUrl}`);
        this._ws = new WebSocket(fullUrl);

        this._ws.onopen = () => {
            if (this._ws && this._ws.readyState === WebSocket.OPEN && this.questionId) {
                this._ws.send(JSON.stringify({
                    type: "START_ANSWER",
                    question_id: this.questionId,
                }));
                onOpen();
            }
        };

        this._ws.onmessage = (event) => {
            if (!this.questionId) return;

            try {
                const message = JSON.parse(event.data);
                console.log("[AnswerWebSocket] Received message:", message.type);

                if (message.type === "STARTED") {
                    console.log("[AnswerWebSocket] Transcription started");
                } else if (message.type === "TRANSCRIPT_PARTIAL") {
                    console.log("[AnswerWebSocket] PARTIAL TRANSCRIPT:", message.text);
                    onPartialTranscript(message.text);
                } else if (message.type === "TRANSCRIPT_FINAL") {
                    console.log("[AnswerWebSocket] FINAL TRANSCRIPT:", message.text);
                    onFinalTranscript(message.text);
                } else if (message.type === "ANSWER_READY") {
                    console.log("[AnswerWebSocket] ANSWER READY:", message.transcript_id);
                    onAnswerReady(message.transcript_id);
                    this.disconnect();
                }
            } catch (error) {
                console.error("[AnswerWebSocket] Failed to parse message:", error);
            }
        };

        this._ws.onerror = (error) => {
            console.error("[AnswerWebSocket] WebSocket error:", error);
            onError(error);
        };

        this._ws.onclose = (event) => {
            console.log(`[AnswerWebSocket] WebSocket closed: code=${event.code}, reason=${event.reason || 'none'}`);
            onClose();
        };
    }

    sendAudio(data: ArrayBuffer): void {
        if (this._ws && this._ws.readyState === WebSocket.OPEN) {
            try {
                this._ws.send(data);
                // Log every 10th chunk to avoid spam
                this._audioChunkCount++;
                if (this._audioChunkCount % 10 === 0) {
                    console.log(`[AnswerWebSocket] Sent ${this._audioChunkCount} audio chunks`);
                }
            } catch (error) {
                console.error("[AnswerWebSocket] Error sending audio:", error);
            }
        }
    }

    endAnswer(): void {
        if (this._ws && this._ws.readyState === WebSocket.OPEN) {
            try {
                this._ws.send(JSON.stringify({
                    type: "END_ANSWER",
                }));
            } catch (error) {
                console.error("[AnswerWebSocket] Error ending answer:", error);
            }
        }
    }

    disconnect(): void {
        if (this._ws) {
            try {
                if (this._ws.readyState === WebSocket.OPEN || this._ws.readyState === WebSocket.CONNECTING) {
                    this._ws.close();
                }
            } catch (error) {
                // Ignore errors during disconnect
            }
            this._ws = null;
        }
        this.questionId = null;
    }
}

export const answerWebSocket = new AnswerWebSocket();

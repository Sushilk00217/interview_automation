import { apiClient } from "./apiClient";
import { controlWebSocket } from "./controlWebSocket";
import { proctoringEngine } from "./proctoringEngine";
import {
    InterviewState,
    QuestionResponse,
    EvaluationSubmitRequest,
    ProctoringEventRequest,
    EvaluationSubmitResponse,
    ProctoringEventResponse,
} from "@/types/api";

class InterviewService {
    private interviewId: string | null = null;
    private candidateToken: string | null = null;

    initialize(params: {
        interviewId: string;
        candidateToken: string;
        onConnected: () => void;
        onTerminated: (reason: string) => void;
        onError: (error: unknown) => void;
    }): void {
        this.interviewId = params.interviewId;
        this.candidateToken = params.candidateToken;

        apiClient.setInterviewId(this.interviewId);

        controlWebSocket.disconnect();

        const state = controlWebSocket.getReadyState();
        if (state !== WebSocket.CONNECTING && state !== WebSocket.OPEN) {
            controlWebSocket.connect({
                interviewId: this.interviewId!,
                candidateToken: this.candidateToken!,
                onOpen: () => {
                    console.log("[InterviewService] WebSocket connected");
                    params.onConnected();
                },
                onTerminate: (reason: string) => {
                    console.log("[InterviewService] Interview terminated:", reason);
                    proctoringEngine.stop();
                    params.onTerminated(reason);
                },
                onError: (error: Event) => {
                    console.error("[InterviewService] WebSocket error:", error);
                    // WebSocket errors are usually connection issues
                    // Log the error but don't immediately fail the interview
                    // The onClose handler will handle actual disconnections
                    const err = error instanceof Error ? error : new Error("WebSocket connection error. Please check your connection and try again.");
                    // Only report error if it's a critical connection failure
                    // Transient errors during connection are normal
                    console.warn("[InterviewService] WebSocket error (may be transient):", err.message);
                },
                onClose: (event: CloseEvent) => {
                    console.log(`[InterviewService] WebSocket Closed: ${event.code} - ${event.reason}`);
                    proctoringEngine.stop();
                    if (event.code === 1008) {
                        // Invalid session/token -> Terminate/Error
                        const error = new Error(`Session invalid or expired: ${event.reason || 'Invalid session'}`);
                        params.onError(error);
                    } else if (event.code !== 1000 && event.code !== 1001) {
                        // Normal closure codes are 1000 and 1001
                        // Other codes indicate an error
                        const error = new Error(`WebSocket connection closed unexpectedly: ${event.reason || `Code ${event.code}`}`);
                        params.onError(error);
                    }
                },
            });
        }
    }

    async startInterview(): Promise<InterviewState> {
        const response = await apiClient.post<{ state: InterviewState }, {}>(
            "/api/v1/session/start",
            {},
            true
        );

        if (response.state === "IN_PROGRESS") {
            try {
                await proctoringEngine.start();
            } catch (error) {
                controlWebSocket.disconnect();
                throw error;
            }
        }

        return response.state;
    }

    async getSections(): Promise<import("@/types/api").InterviewSection[]> {
        return apiClient.get<import("@/types/api").InterviewSection[]>("/api/v1/candidate/interview/sections", true);
    }

    async startSection(sectionType: string): Promise<InterviewState> {
        const response = await apiClient.post<any, { section_type: string }>(
            "/api/v1/candidate/interview/start-section",
            { section_type: sectionType },
            true
        );
        // Do not auto-start proctoring here; let InterviewStore sequence things.
        return response.state || "IN_PROGRESS";
    }

    async fetchNextQuestion(): Promise<QuestionResponse> {
        return apiClient.get<QuestionResponse>("/api/v1/question/next", true);
    }

    async submitAnswer(payload: EvaluationSubmitRequest): Promise<InterviewState> {
        const response = await apiClient.post<EvaluationSubmitResponse, EvaluationSubmitRequest>(
            "/api/v1/submit/submit",
            payload,
            true
        );

        if (response.state === "COMPLETED") {
            proctoringEngine.stop();
        }

        return response.state;
    }

    async sendProctoringEvent(event: ProctoringEventRequest): Promise<void> {
        await apiClient.post<ProctoringEventResponse, ProctoringEventRequest>(
            "/api/v1/proctoring/event",
            event,
            true
        );
    }

    async completeSection(): Promise<InterviewState> {
        const response = await apiClient.post<{ state: InterviewState }, {}>(
            "/api/v1/candidate/interview/complete-section",
            {},
            true
        );
        return response.state;
    }

    async completeInterview(): Promise<InterviewState> {
        const response = await apiClient.post<{ state: InterviewState }, {}>(
            "/api/v1/session/complete",
            {},
            true
        );

        if (response.state === "COMPLETED") {
            proctoringEngine.stop();
        }

        return response.state;
    }

    terminate(): void {
        proctoringEngine.stop();
        controlWebSocket.disconnect();
        apiClient.clearInterviewId();
        this.interviewId = null;
        this.candidateToken = null;
    }
}

export const interviewService = new InterviewService();

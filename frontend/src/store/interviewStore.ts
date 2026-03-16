import { create } from "zustand";
import { interviewService } from "@/lib/interviewService";
import {
    InterviewState,
    QuestionResponse,
    EvaluationSubmitRequest,
    ProctoringEventRequest,
} from "@/types/api";

interface InterviewStore {
    interviewId: string | null;
    candidateToken: string | null;
    state: InterviewState | null;
    currentQuestion: QuestionResponse | null;
    terminationReason: string | null;
    isSubmitting: boolean;
    isConnected: boolean;
    error: string | null;

    sections: import("@/types/api").InterviewSection[];
    currentSection: import("@/types/api").InterviewSection | null;

    initialize: (interviewId: string, candidateToken: string) => void;
    startInterview: () => Promise<void>;
    fetchNextQuestion: () => Promise<void>;
    submitAnswer: (payload: EvaluationSubmitRequest) => Promise<void>;
    sendProctoringEvent: (event: ProctoringEventRequest) => Promise<void>;
    completeSection: () => Promise<void>;
    completeInterview: () => Promise<void>;
    terminate: () => void;

    fetchSections?: () => Promise<void>;
    startSection: (sectionType: string) => Promise<void>;
}

export const useInterviewStore = create<InterviewStore>((set, get) => ({
    interviewId: null,
    candidateToken: null,
    state: null,
    currentQuestion: null,
    terminationReason: null,
    isSubmitting: false,
    isConnected: false,
    error: null,
    sections: [],
    currentSection: null,

    initialize: (interviewId: string, candidateToken: string) => {
        set({ interviewId, candidateToken, error: null });
        interviewService.initialize({
            interviewId,
            candidateToken,
            onConnected: () => {
                console.log("[InterviewStore] WebSocket Connected");
                set({ isConnected: true });
            },
            onTerminated: (reason: string) => {
                console.log("[InterviewStore] Terminated:", reason);
                set({ state: "TERMINATED", terminationReason: reason, isConnected: false, currentQuestion: null });
            },
            onError: (error: unknown) => {
                console.error("[InterviewStore] Error:", error);
                const errorMessage = error instanceof Error ? error.message : "Unknown error";
                set({ error: errorMessage, isConnected: false });
            },
        });
    },

    startInterview: async () => {
        set({ error: null });
        try {
            const state = await interviewService.startInterview();
            set({ state });

            // fetch sections initially
            if (state === "IN_PROGRESS" || state === "READY") {
                const sect = await interviewService.getSections();
                const active = sect.find(s => s.status === "in_progress" || s.is_current) || null;
                set({ sections: sect, currentSection: active });
                if (active) {
                    await get().fetchNextQuestion();
                }
            }
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : "Failed to start interview";
            set({ error: errorMessage });
        }
    },

    fetchNextQuestion: async () => {
        set({ error: null });
        if (get().state !== "IN_PROGRESS") return;

        try {
            const question = await interviewService.fetchNextQuestion();
            set({ currentQuestion: question, state: "QUESTION_ASKED" });
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : "Failed to fetch question";
            set({ error: errorMessage });
        }
    },

    submitAnswer: async (payload: EvaluationSubmitRequest) => {
        set({ isSubmitting: true, error: null });
        try {
            const state = await interviewService.submitAnswer(payload);
            if (state === "IN_PROGRESS") {
                set({ state });
                await get().fetchNextQuestion();
            } else if (state === "COMPLETED") {
                // Interview is fully completed - redirect handled by InterviewShell
                set({ state, currentQuestion: null, currentSection: null });
            } else if (state === "SECTION_COMPLETED") {
                // Clear immediately to trigger UI change to SectionSelector
                set({ state, currentQuestion: null, currentSection: null });

                // Refresh sections to get latest counts and statuses
                const sect = await interviewService.getSections();
                const active = sect.find(s => s.status === "in_progress" || s.is_current) || null;
                set({ sections: sect, currentSection: active });

                if (active) {
                    set({ state: "IN_PROGRESS" });
                    await get().fetchNextQuestion();
                } else {
                    set({ state: "READY" });
                }
            } else {
                set({ state });
            }
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : "Failed to submit answer";
            set({ error: errorMessage });
        } finally {
            set({ isSubmitting: false });
        }
    },

    sendProctoringEvent: async (event: ProctoringEventRequest) => {
        try {
            await interviewService.sendProctoringEvent(event);
        } catch (error) {
            // Silently log or handle if critical, but specs say no console logs.
            // Keeping error state consistent if meaningful.
            const errorMessage = error instanceof Error ? error.message : "Failed to send proctoring event";
            set({ error: errorMessage });
        }
    },

    completeSection: async () => {
        set({ isSubmitting: true, error: null });
        try {
            const state = await interviewService.completeSection();
            set({ state, currentQuestion: null, currentSection: null });

            // Refresh sections to get latest counts and statuses
            const sect = await interviewService.getSections();
            set({ sections: sect });
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : "Failed to complete section";
            set({ error: errorMessage });
        } finally {
            set({ isSubmitting: false });
        }
    },

    completeInterview: async () => {
        set({ isSubmitting: true, error: null });
        try {
            const state = await interviewService.completeInterview();
            set({ state: "COMPLETED" });
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : "Failed to complete interview";
            set({ error: errorMessage });
        } finally {
            set({ isSubmitting: false });
        }
    },

    terminate: () => {
        if (!get().interviewId && !get().isConnected) return; // already terminated, skip
        interviewService.terminate();
        set({
            interviewId: null,
            candidateToken: null,
            state: null,
            currentQuestion: null,
            terminationReason: null,
            isSubmitting: false,
            isConnected: false,
            error: null,
            sections: [],
            currentSection: null,
        });
    },

    // Optional explicit startSection handler
    startSection: async (sectionType: string) => {
        set({ error: null });
        try {
            const state = await interviewService.startSection(sectionType);
            set({ state });

            const sect = await interviewService.getSections();
            const active = sect.find(s => s.status === "in_progress" || s.is_current) || null;
            set({ sections: sect, currentSection: active });

            if (active) {
                await get().fetchNextQuestion();
            }
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : "Failed to start section";
            set({ error: errorMessage });
        }
    }
}));

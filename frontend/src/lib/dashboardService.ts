import { apiClient } from "./apiClient";

export interface InterviewSummary {
    interview_id: string;
    candidate_token: string;
    state: string;
    cheat_score: number;
    created_at: string;
}

export const dashboardService = {
    getInterviews: async (candidateToken?: string): Promise<InterviewSummary[]> => {
        let path = "/api/v1/dashboard/interviews";
        if (candidateToken) {
            path += `?candidate_token=${encodeURIComponent(candidateToken)}`;
        }
        return apiClient.get<InterviewSummary[]>(path);
    },

    createSession: async (candidateToken: string): Promise<any> => {
        return apiClient.post("/api/v1/session/init", { candidate_token: candidateToken });
    },

    getCandidates: async (): Promise<import("@/types/api").CandidateResponse[]> => {
        return apiClient.get<import("@/types/api").CandidateResponse[]>("/api/v1/auth/admin/candidates");
    },

    toggleCandidateLogin: async (candidateId: string): Promise<import("@/types/api").ToggleLoginResponse> => {
        return apiClient.post<import("@/types/api").ToggleLoginResponse, {}>(
            `/api/v1/auth/admin/candidates/${candidateId}/toggle-login`,
            {}
        );
    },
    reparseResume: async (candidateId: string): Promise<any> => {
        return apiClient.post(`/api/v1/auth/admin/candidates/${candidateId}/reparse-resume`, {});
    },
    deleteCandidate: async (candidateId: string): Promise<void> => {
        return apiClient.delete(`/api/v1/auth/admin/candidates/${candidateId}`);
    }
};

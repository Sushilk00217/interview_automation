// ─── Interview Scheduling API Types ──────────────────────────────────────────

export type InterviewStatus =
    | 'scheduled'
    | 'in_progress'
    | 'completed'
    | 'cancelled';

export interface InterviewTemplate {
    id: string;
    name: string;
    description: string;
    total_duration_sec: number;
    is_active: boolean;
    is_rule_based?: boolean;
}

export interface GeneratedQuestion {
    question_id?: string;
    question_text: string;
    category?: string;
    difficulty?: string;
    order: number;
    time_limit_sec: number;
}

export interface ApplyTemplateRequest {
    questions: {
        question_id?: string;
        question_text: string;
        order: number;
        time_limit_sec: number;
    }[];
}

export interface CandidateInterview {
    id: string;
    candidate_id: string;
    template_id: string;
    assigned_by: string;
    status: InterviewStatus;
    scheduled_at: string;
    created_at: string;
}

// Extend the existing CandidateResponse with interview info
export interface CandidateWithInterview {
    id: string;
    username: string;
    email: string;
    is_active: boolean;
    login_disabled: boolean;
    created_at: string;
    interview?: CandidateInterview | null;  // null = no interview yet
}

// ─── Request / Response shapes ───────────────────────────────────────────────

export interface ScheduleInterviewRequest {
    candidate_id: string;
    template_id: string;
    scheduled_at: string; // ISO 8601 UTC
}

export interface RescheduleInterviewRequest {
    scheduled_at: string; // ISO 8601 UTC
}

export interface CancelInterviewRequest {
    reason?: string;
}

export interface ScheduleInterviewResponse {
    id: string;
    candidate_id: string;
    template_id: string;
    assigned_by: string;
    status: 'scheduled';
    scheduled_at: string;
    created_at: string;
}

export interface RescheduleInterviewResponse {
    id: string;
    status: 'scheduled';
    scheduled_at: string;
    updated_at: string;
}

export interface CancelInterviewResponse {
    id: string;
    status: 'cancelled';
    cancelled_at: string;
    reason?: string;
}

// ─── Structured API error ────────────────────────────────────────────────────

export interface SchedulingApiError {
    status: number;
    detail: string;
}

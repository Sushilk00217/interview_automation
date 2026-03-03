// ─── Interview Scheduling API Types ──────────────────────────────────────────

export type InterviewStatus =
    | 'scheduled'
    | 'in_progress'
    | 'completed'
    | 'cancelled';

export interface InterviewTemplate {
    id: string;
    title: string;
    role_name?: string | null;
    description?: string | null;
    is_active: boolean;
    is_rule_based: boolean;
    is_default_for_role: boolean;
    created_at: string;
    updated_at: string;
    settings?: Record<string, any> | null;
}

export interface InterviewTemplateCreate {
    title: string;
    role_name?: string;
    description?: string;
    is_rule_based: boolean;
    is_active?: boolean;
    is_default_for_role?: boolean;
    settings?: Record<string, any>;
}

export interface InterviewTemplateUpdate {
    title?: string;
    role_name?: string;
    description?: string;
    is_rule_based?: boolean;
    is_active?: boolean;
    is_default_for_role?: boolean;
    settings?: Record<string, any>;
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

export interface InterviewSessionQuestionCreate {
    question_id?: string;
    custom_text?: string;
    order: number;
}

export interface ScheduleInterviewRequest {
    candidate_id: string;
    template_id: string;
    scheduled_at: string; // ISO 8601 UTC
    questions?: InterviewSessionQuestionCreate[];
}

export interface TemplatePreviewQuestion {
    question_id: string;
    text: string;
    originalText?: string; // Keep track of the text before editing
    difficulty: string;
    category: string;
}

export interface TemplatePreviewResponse {
    questions: TemplatePreviewQuestion[];
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

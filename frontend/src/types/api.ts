export type InterviewState =
    | "CREATED"
    | "RESUME_PARSED"
    | "READY"
    | "IN_PROGRESS"
    | "QUESTION_ASKED"
    | "ANSWER_SUBMITTED"
    | "EVALUATING"
    | "COMPLETED"
    | "TERMINATED"
    | "SECTION_COMPLETED";

export type QuestionCategory = "CONVERSATIONAL" | "STATIC" | "CODING";

export type AnswerMode = "TEXT" | "AUDIO" | "CODE";

export interface InterviewSection {
    id: string;
    section_type: "technical" | "coding" | "conversational";
    status: "pending" | "in_progress" | "completed";
    order_index: number;
    duration_minutes: number;
    is_current: boolean;
    total_questions: number;
    completed_questions: number;
}

export type Difficulty = "EASY" | "MEDIUM" | "HARD";

export type Recommendation = "PROCEED" | "REJECT" | "REVIEW";

export type FraudRisk = "LOW" | "MEDIUM" | "HIGH";

export type EventType = "TAB_SWITCH" | "MULTI_FACE" | "VOICE_MISMATCH";

export type ProctoringAction = "FLAG" | "TERMINATE" | "IGNORE";

export interface QuestionResponse {
    question_id: string;
    session_question_id?: string;
    type?: string;
    question_text?: string;
    prompt?: string; // fallback
    answer_mode: AnswerMode;
    time_limit_sec: number;
    question_number: number;
    total_questions: number;
    category?: string; // Added back for UI completeness
    difficulty?: string;
}

export interface EvaluationSubmitRequest {
    question_id: string;
    answer_type: AnswerMode;
    answer_payload: string;
}

export interface EvaluationSubmitResponse {
    state: InterviewState;
}

export interface SummaryResponse {
    final_score: number;
    recommendation: Recommendation;
    fraud_risk: FraudRisk;
    strengths: string[];
    gaps: string[];
    notes: string;
}

export interface ProctoringEventRequest {
    event_type: EventType;
    confidence: number;
}

export interface ProctoringEventResponse {
    action: ProctoringAction;
}

export interface CodeTemplateResponse {
    language: string;
    starter_code: string;
}

export interface ConversationPromptResponse {
    prompt: string;
    followup_allowed: boolean;
}

export interface ApiError {
    error_code: string;
    message: string;
    current_state?: InterviewState | null;
}

export interface AuthRequest {
    username: string;
    password: string;
}

export interface TokenResponse {
    access_token: string;
    token_type: string;
    username: string;
    role: "admin" | "candidate";
}

// Candidate Profile (all fields optional)
export interface CandidateProfile {
    first_name?: string;
    last_name?: string;
    phone?: string;
    resume_id?: string;
    experience_years?: number;
    skills?: string[];
}

// Full candidate registration payload for backend
export interface CandidateRegistration {
    username: string;
    email: string;
    password: string;
    role: "candidate";
    profile: CandidateProfile;
}

// Minimal request for admin to register candidate (frontend form)
export interface CandidateRegistrationRequest {
    username: string;
    email: string;
    password: string;
}

export interface CandidateResponse {
    id: string;
    username: string;
    email: string;
    is_active: boolean;
    login_disabled: boolean;
    created_at: string;
    job_description?: string;
    parse_status?: string | null;
    parsed_at?: string | null;
    resume_json?: any;
    jd_json?: any;
    role_name?: string | null;
    match_score?: number | null;
    password?: string;
}

export interface ToggleLoginResponse {
    message: string;
    candidate_id: string;
    email: string;
    login_disabled: boolean;
}

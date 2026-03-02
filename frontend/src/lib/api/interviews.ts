/**
 * interviews.ts — API helpers for interview scheduling, summary, and candidate flow
 */

import {
    ScheduleInterviewRequest,
    ScheduleInterviewResponse,
    RescheduleInterviewRequest,
    RescheduleInterviewResponse,
    CancelInterviewRequest,
    CancelInterviewResponse,
    InterviewTemplate,
    CandidateInterview,
    SchedulingApiError,
} from '@/types/interview';

// Re-export so consumers can import from this module
export type { SchedulingApiError };

const BASE_URL =
    process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

// ─── Auth token helper ────────────────────────────────────────────────────────

function getToken(): string | null {
    if (typeof window === 'undefined') return null;
    try {
        const raw = localStorage.getItem('auth-storage');
        if (!raw) return null;
        return JSON.parse(raw)?.state?.token ?? null;
    } catch {
        return null;
    }
}

function authHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
    };
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return headers;
}

// ─── Error parsing ────────────────────────────────────────────────────────────

async function parseError(res: Response): Promise<SchedulingApiError> {
    let detail = `Request failed with status ${res.status}`;
    try {
        const body = await res.json();
        if (body?.detail) detail = body.detail;
    } catch {
        // use default message
    }
    return { status: res.status, detail };
}

// ─── Templates ───────────────────────────────────────────────────────────────

export async function fetchInterviewTemplates(): Promise<InterviewTemplate[]> {
    const res = await fetch(`${BASE_URL}/api/v1/admin/interviews/templates`, {
        headers: authHeaders(),
    });
    if (!res.ok) throw await parseError(res);
    return res.json();
}

// ─── Candidate interviews (lookup by candidate_id) ───────────────────────────

export async function fetchCandidateInterview(
    candidateId: string
): Promise<CandidateInterview | null> {
    const res = await fetch(
        `${BASE_URL}/api/v1/admin/candidates/${candidateId}/interview`,
        { headers: authHeaders() }
    );
    if (res.status === 404) return null;
    if (!res.ok) throw await parseError(res);
    return res.json();
}

// ─── Schedule ─────────────────────────────────────────────────────────────────

export async function scheduleInterview(
    data: ScheduleInterviewRequest
): Promise<ScheduleInterviewResponse> {
    const res = await fetch(`${BASE_URL}/api/v1/admin/interviews/schedule`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify(data),
    });
    if (!res.ok) throw await parseError(res);
    return res.json();
}

// ─── Reschedule ───────────────────────────────────────────────────────────────

export async function rescheduleInterview(
    interviewId: string,
    data: RescheduleInterviewRequest
): Promise<RescheduleInterviewResponse> {
    const res = await fetch(
        `${BASE_URL}/api/v1/admin/interviews/${interviewId}/reschedule`,
        {
            method: 'PUT',
            headers: authHeaders(),
            body: JSON.stringify(data),
        }
    );
    if (!res.ok) throw await parseError(res);
    return res.json();
}

// ─── Cancel ───────────────────────────────────────────────────────────────────

export async function cancelInterview(
    interviewId: string,
    data?: CancelInterviewRequest
): Promise<CancelInterviewResponse> {
    const res = await fetch(
        `${BASE_URL}/api/v1/admin/interviews/${interviewId}/cancel`,
        {
            method: 'PUT',
            headers: authHeaders(),
            body: JSON.stringify(data ?? {}),
        }
    );
    if (!res.ok) throw await parseError(res);
    return res.json();
}

// ─── Admin interview summary (bulk, no curated_questions) ─────────────────────

export interface InterviewSummaryItem {
    interview_id: string;
    candidate_id: string;
    status: string;
    scheduled_at: string | null;
    overall_score: number | null;
}

export async function fetchInterviewSummary(): Promise<InterviewSummaryItem[]> {
    const res = await fetch(`${BASE_URL}/api/v1/admin/interviews/summary`, {
        headers: authHeaders(),
    });
    if (!res.ok) throw await parseError(res);
    return res.json();
}

// ─── Candidate: active interview ──────────────────────────────────────────────

export interface ActiveInterviewResponse {
    interview_id: string;
    session_id: string | null;
    status: 'scheduled' | 'in_progress';
    scheduled_at: string | null;
    can_start: boolean;
    face_verified?: boolean;
    voice_verified?: boolean;
}

export async function fetchActiveInterview(): Promise<ActiveInterviewResponse | null> {
    const res = await fetch(`${BASE_URL}/api/v1/candidate/interviews/active`, {
        headers: authHeaders(),
    });
    if (!res.ok) throw await parseError(res);
    const data = await res.json();
    return data ?? null;
}

// ─── Candidate: start interview ───────────────────────────────────────────────

export interface StartInterviewResponse {
    session_id: string;
    interview_id: string;
    status: 'in_progress';
}

export async function startInterview(
    interviewId: string
): Promise<StartInterviewResponse> {
    const res = await fetch(
        `${BASE_URL}/api/v1/candidate/interviews/${interviewId}/start`,
        {
            method: 'POST',
            headers: authHeaders(),
        }
    );
    if (!res.ok) throw await parseError(res);
    return res.json();
}

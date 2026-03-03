/**
 * templates.ts — API helpers for interview template management
 */
import {
    InterviewTemplate,
    InterviewTemplateCreate,
    InterviewTemplateUpdate,
    SchedulingApiError,
} from '@/types/interview';

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
const API_BASE = `${BASE_URL}/api/v1/admin/templates`;

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

// ─── API Functions ───────────────────────────────────────────────────────────

export const getTemplates = async (params?: { role?: string; active_only?: boolean }): Promise<InterviewTemplate[]> => {
    const url = new URL(API_BASE);
    if (params?.role) url.searchParams.append('role', params.role);
    if (params?.active_only !== undefined) url.searchParams.append('active_only', String(params.active_only));

    const res = await fetch(url.toString(), {
        headers: authHeaders(),
    });
    if (!res.ok) throw await parseError(res);
    return res.json();
};

export const createTemplate = async (data: InterviewTemplateCreate): Promise<InterviewTemplate> => {
    const res = await fetch(API_BASE, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify(data),
    });
    if (!res.ok) throw await parseError(res);
    return res.json();
};

export const updateTemplate = async (id: string, data: InterviewTemplateUpdate): Promise<InterviewTemplate> => {
    const res = await fetch(`${API_BASE}/${id}`, {
        method: 'PUT',
        headers: authHeaders(),
        body: JSON.stringify(data),
    });
    if (!res.ok) throw await parseError(res);
    return res.json();
};

export const deleteTemplate = async (id: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/${id}`, {
        method: 'DELETE',
        headers: authHeaders(),
    });
    if (!res.ok) throw await parseError(res);
};

export const toggleTemplateActive = async (id: string, isActive: boolean): Promise<InterviewTemplate> => {
    const url = new URL(`${API_BASE}/${id}/activate`);
    url.searchParams.append('is_active', String(isActive));

    const res = await fetch(url.toString(), {
        method: 'PATCH',
        headers: authHeaders(),
    });
    if (!res.ok) throw await parseError(res);
    return res.json();
};

export const getTemplate = async (id: string): Promise<InterviewTemplate> => {
    const res = await fetch(`${API_BASE}/${id}`, {
        headers: authHeaders(),
    });
    if (!res.ok) throw await parseError(res);
    return res.json();
};

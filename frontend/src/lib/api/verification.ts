/**
 * verification.ts — API helpers for candidate verification (face, voice samples)
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

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

function authHeaders(contentType: string = 'application/json'): Record<string, string> {
    const headers: Record<string, string> = {};
    if (contentType !== 'multipart/form-data') {
        headers['Content-Type'] = contentType;
    }
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return headers;
}

export interface VerificationStatus {
    face_verified: boolean;
    voice_verified: boolean;
    can_start_interview: boolean;
    face_sample_url?: string;
    voice_sample_url?: string;
    video_sample_url?: string;
}

export interface VerificationResponse {
    success: boolean;
    message: string;
    face_verified?: boolean;
    voice_verified?: boolean;
    face_sample_url?: string;
    voice_sample_url?: string;
    video_sample_url?: string;
}

export async function getVerificationStatus(): Promise<VerificationStatus> {
    const res = await fetch(`${BASE_URL}/api/v1/verification/status`, {
        headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`Failed to fetch verification status: ${res.statusText}`);
    return res.json();
}

export async function uploadFaceSample(file: File): Promise<VerificationResponse> {
    const formData = new FormData();
    formData.append('photo', file);
    
    const token = getToken();
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    
    const res = await fetch(`${BASE_URL}/api/v1/verification/face-sample`, {
        method: 'POST',
        headers,
        body: formData,
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(error.detail || 'Failed to upload face sample');
    }
    return res.json();
}

export async function uploadVideoSample(file: File): Promise<VerificationResponse> {
    const formData = new FormData();
    formData.append('video', file);
    
    const token = getToken();
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    
    const res = await fetch(`${BASE_URL}/api/v1/verification/video-sample`, {
        method: 'POST',
        headers,
        body: formData,
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(error.detail || 'Failed to upload video sample');
    }
    return res.json();
}

export async function uploadVoiceSample(file: File): Promise<VerificationResponse> {
    const formData = new FormData();
    formData.append('audio', file);
    
    const token = getToken();
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    
    const res = await fetch(`${BASE_URL}/api/v1/verification/voice-sample`, {
        method: 'POST',
        headers,
        body: formData,
    });
    if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(error.detail || 'Failed to upload voice sample');
    }
    return res.json();
}

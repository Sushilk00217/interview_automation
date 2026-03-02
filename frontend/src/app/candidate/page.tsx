'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { useInterviewStore } from '@/store/interviewStore';
import {
    fetchActiveInterview,
    startInterview,
    ActiveInterviewResponse,
    SchedulingApiError,
} from '@/lib/api/interviews';
import {
    getVerificationStatus,
    uploadFaceSample,
    uploadVoiceSample,
    uploadVideoSample,
    VerificationStatus,
} from '@/lib/api/verification';
import MediaCapture from '@/components/verification/MediaCapture';

// ─── Status badge ─────────────────────────────────────────────────────────────

const STATUS_STYLES: Record<string, string> = {
    scheduled: 'bg-blue-100 text-blue-800',
    in_progress: 'bg-yellow-100 text-yellow-800',
    completed: 'bg-green-100 text-green-800',
    cancelled: 'bg-gray-100 text-gray-600',
};
const STATUS_LABELS: Record<string, string> = {
    scheduled: 'Scheduled',
    in_progress: 'In Progress',
    completed: 'Completed',
    cancelled: 'Cancelled',
};

// ─── Main page ────────────────────────────────────────────────────────────────

export default function CandidatePage() {
    const router = useRouter();
    const { user, isAuthenticated, logout, _hasHydrated } = useAuthStore();
    const initializeInterview = useInterviewStore((s) => s.initialize);

    const [interview, setInterview] = useState<ActiveInterviewResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [startLoading, setStartLoading] = useState(false);
    const [error, setError] = useState('');
    const [verificationStatus, setVerificationStatus] = useState<VerificationStatus | null>(null);
    const [verificationLoading, setVerificationLoading] = useState(true);
    const [uploading, setUploading] = useState({ photo: false, video: false, audio: false });

    /** Read JWT from localStorage—same key used by authStore & API helpers. */
    const getJwt = (): string => {
        try {
            const raw = localStorage.getItem('auth-storage');
            return JSON.parse(raw ?? '{}')?.state?.token ?? '';
        } catch {
            return '';
        }
    };

    // ─── Auth guard + data fetch ────────────────────────────────────────────
    const fetchData = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const [interviewData, verificationData] = await Promise.all([
                fetchActiveInterview(),
                getVerificationStatus().catch(() => null),
            ]);
            setInterview(interviewData);
            setVerificationStatus(verificationData);
        } catch (err: any) {
            const apiErr = err as SchedulingApiError;
            if (apiErr.status === 401 || apiErr.status === 403) {
                logout();
                router.push('/login/candidate');
                return;
            }
            setError('Failed to load interview details. Please try again.');
        } finally {
            setLoading(false);
            setVerificationLoading(false);
        }
    }, [logout, router]);

    const fetchVerificationStatus = useCallback(async () => {
        try {
            const status = await getVerificationStatus();
            setVerificationStatus(status);
        } catch (err) {
            console.error('Failed to fetch verification status:', err);
        }
    }, []);

    const handlePhotoCapture = async (file: File) => {
        setUploading(prev => ({ ...prev, photo: true }));
        setError('');
        try {
            await uploadFaceSample(file);
            await fetchVerificationStatus();
            // Refresh interview data to update can_start status
            const interviewData = await fetchActiveInterview();
            setInterview(interviewData);
        } catch (err: any) {
            setError(err.message || 'Failed to upload photo');
        } finally {
            setUploading(prev => ({ ...prev, photo: false }));
        }
    };

    const handleVideoCapture = async (file: File) => {
        setUploading(prev => ({ ...prev, video: true }));
        setError('');
        try {
            await uploadVideoSample(file);
            await fetchVerificationStatus();
        } catch (err: any) {
            setError(err.message || 'Failed to upload video');
        } finally {
            setUploading(prev => ({ ...prev, video: false }));
        }
    };

    const handleVoiceCapture = async (file: File) => {
        setUploading(prev => ({ ...prev, audio: true }));
        setError('');
        try {
            await uploadVoiceSample(file);
            await fetchVerificationStatus();
            // Refresh interview data to update can_start status
            const interviewData = await fetchActiveInterview();
            setInterview(interviewData);
        } catch (err: any) {
            setError(err.message || 'Failed to upload voice sample');
        } finally {
            setUploading(prev => ({ ...prev, audio: false }));
        }
    };

    useEffect(() => {
        if (!_hasHydrated) return;  // wait for localStorage rehydration
        if (!isAuthenticated || !user) {
            router.push('/login/candidate');
            return;
        }
        if (user.role !== 'candidate') {
            router.push(user.role === 'admin' ? '/admin' : '/login/candidate');
            return;
        }
        fetchData();
    }, [_hasHydrated, isAuthenticated, user, router, fetchData]);


    // ─── Start / Rejoin interview ────────────────────────────────────────────
    const handleStart = async () => {
        if (!interview) return;
        
        // Check verification status before starting
        if (!verificationStatus?.can_start_interview) {
            setError('Please complete identity verification (upload photo and voice sample) before starting the interview.');
            return;
        }
        setStartLoading(true);
        setError('');
        try {
            let sessionId: string;

            if (interview.status === 'in_progress' && interview.session_id) {
                sessionId = interview.session_id; // rejoin existing session
            } else {
                const result = await startInterview(interview.interview_id);
                sessionId = result.session_id;
            }

            // Seed the interviewStore so /interview page has what it needs:
            //   interviewId  → session_id (used as the WS room identifier)
            //   candidateToken → JWT (used for WS auth)
            const jwt = getJwt();
            initializeInterview(sessionId, jwt);

            router.push('/interview');
        } catch (err: any) {
            const apiErr = err as SchedulingApiError;
            if (apiErr.status === 401 || apiErr.status === 403) {
                logout();
                router.push('/login/candidate');
                return;
            }
            setError(apiErr.detail || 'Failed to start interview. Please try again.');
        } finally {
            setStartLoading(false);
        }
    };

    const handleLogout = () => { logout(); router.push('/login/candidate'); };

    // ─── Render ───────────────────────────────────────────────────────────────

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
                    <p className="text-gray-600">Loading your dashboard…</p>
                </div>
            </div>
        );
    }

    if (!user) return null;

    const ivStatus = interview?.status;
    const isInProgress = ivStatus === 'in_progress';
    const statusKey = ivStatus ?? '';

    // Format scheduled_at in local timezone
    const scheduledDisplay = interview?.scheduled_at
        ? new Date(interview.scheduled_at).toLocaleString(undefined, {
            dateStyle: 'full',
            timeStyle: 'short',
        })
        : null;

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Header */}
            <header className="bg-white shadow-sm border-b border-gray-200">
                <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
                    <div className="flex justify-between items-center">
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900">Candidate Dashboard</h1>
                            <p className="text-sm text-gray-600 mt-0.5">Welcome, {user.username}</p>
                        </div>
                        <button
                            onClick={handleLogout}
                            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium text-sm"
                        >
                            Logout
                        </button>
                    </div>
                </div>
            </header>

            {/* Main */}
            <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
                {error && (
                    <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">{error}</div>
                )}

                {/* Verification Section */}
                {!verificationLoading && (
                    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                        <div className="px-6 py-4 border-b border-gray-100">
                            <h2 className="text-base font-semibold text-gray-900">Identity Verification</h2>
                            <p className="text-sm text-gray-600 mt-1">
                                Please upload your photo and voice sample to verify your identity before starting the interview.
                            </p>
                        </div>
                        <div className="p-6 space-y-4">
                            <MediaCapture
                                type="photo"
                                onCapture={handlePhotoCapture}
                                isUploading={uploading.photo}
                                isVerified={verificationStatus?.face_verified || false}
                            />
                            <MediaCapture
                                type="audio"
                                onCapture={handleVoiceCapture}
                                isUploading={uploading.audio}
                                isVerified={verificationStatus?.voice_verified || false}
                            />
                            
                            {verificationStatus?.can_start_interview && (
                                <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800 flex items-center gap-2">
                                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clipRule="evenodd" />
                                    </svg>
                                    <span>All verification samples uploaded successfully. You can now start your interview.</span>
                                </div>
                            )}
                            {!verificationStatus?.can_start_interview && (
                                <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
                                    Please complete identity verification (upload photo and voice sample) before starting the interview.
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Interview card */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                    <div className="px-6 py-4 border-b border-gray-100">
                        <h2 className="text-base font-semibold text-gray-900">Your Interview</h2>
                    </div>

                    {interview ? (
                        <div className="p-6 space-y-5">
                            {/* Status row */}
                            <div className="flex items-center justify-between">
                                <span className="text-sm font-medium text-gray-500">Status</span>
                                <span className={`px-3 py-1 rounded-full text-xs font-semibold ${STATUS_STYLES[statusKey] ?? 'bg-gray-100 text-gray-600'}`}>
                                    {STATUS_LABELS[statusKey] ?? statusKey}
                                </span>
                            </div>

                            {/* Scheduled At */}
                            {scheduledDisplay && (
                                <div className="flex items-center justify-between">
                                    <span className="text-sm font-medium text-gray-500">
                                        {isInProgress ? 'Started' : 'Scheduled For'}
                                    </span>
                                    <span className="text-sm text-gray-900 font-medium">{scheduledDisplay}</span>
                                </div>
                            )}

                            {/* Interview ID */}
                            <div className="flex items-center justify-between">
                                <span className="text-sm font-medium text-gray-500">Interview ID</span>
                                <span className="text-xs font-mono text-gray-400">{interview.interview_id}</span>
                            </div>

                            {/* can_start gate */}
                            {interview.can_start && verificationStatus?.can_start_interview ? (
                                <button
                                    onClick={handleStart}
                                    disabled={startLoading}
                                    className="w-full py-3 px-6 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors shadow-sm flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {startLoading ? (
                                        <>
                                            <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                            </svg>
                                            {isInProgress ? 'Rejoining…' : 'Starting…'}
                                        </>
                                    ) : (
                                        <>
                                            {isInProgress ? 'Rejoin Interview' : 'Start Interview'}
                                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
                                                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                                            </svg>
                                        </>
                                    )}
                                </button>
                            ) : (
                                <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800 flex items-start gap-2">
                                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 flex-shrink-0 mt-0.5">
                                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm.75-13a.75.75 0 00-1.5 0v5c0 .414.336.75.75.75h4a.75.75 0 000-1.5h-3.25V5z" clipRule="evenodd" />
                                    </svg>
                                    <div className="flex-1">
                                        {interview.scheduled_at && new Date(interview.scheduled_at) > new Date() ? (
                                            <span>
                                                Your interview is scheduled for <strong>{scheduledDisplay}</strong>. The Start button will unlock at that time.
                                            </span>
                                        ) : (
                                            <span>
                                                {!verificationStatus?.can_start_interview 
                                                    ? "Please complete identity verification (upload photo and voice sample) before starting the interview."
                                                    : "Please wait for the scheduled time to start the interview."
                                                }
                                            </span>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="p-6 space-y-4">
                            <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg flex items-center justify-between">
                                <div>
                                    <p className="font-medium text-gray-700 text-sm">No Active Interview</p>
                                    <p className="text-xs text-gray-400 mt-0.5">Contact HR if you believe this is an error.</p>
                                </div>
                                <div className="w-3 h-3 bg-gray-300 rounded-full" />
                            </div>
                            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-800 text-sm flex items-start gap-2">
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 flex-shrink-0 mt-0.5">
                                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                                </svg>
                                Waiting for interview assignment by your recruiter…
                            </div>
                        </div>
                    )}
                </div>

                {/* Guidelines */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                    <div className="flex items-start gap-3">
                        <div className="p-2 bg-blue-50 text-blue-600 rounded-lg flex-shrink-0">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
                            </svg>
                        </div>
                        <div>
                            <h3 className="text-sm font-semibold text-gray-900 mb-2">Interview Guidelines</h3>
                            <ul className="text-sm text-gray-600 space-y-1.5">
                                {[
                                    'Ensure a stable internet connection.',
                                    'Find a quiet environment with good lighting.',
                                    'Camera and microphone must be ready and working.',
                                    'Once started, complete the session without interruption.',
                                ].map(tip => (
                                    <li key={tip} className="flex items-start gap-2">
                                        <span className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-1.5 flex-shrink-0" />
                                        <span>{tip}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}

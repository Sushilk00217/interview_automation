'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { authService } from '@/lib/authService';
import { dashboardService } from '@/lib/dashboardService';
import {
    cancelInterview,
    fetchInterviewSummary,
    InterviewSummaryItem,
    SchedulingApiError,
} from '@/lib/api/interviews';
import { API_BASE_URL } from '@/lib/apiClient';
import { CandidateResponse } from '@/types/api';
import ScheduleInterviewModal from '@/components/admin/ScheduleInterviewModal';
import CancelInterviewDialog from '@/components/admin/CancelInterviewDialog';
import ResumePreviewModal from '@/components/admin/ResumePreviewModal';
import InterviewReportModal from '@/components/admin/InterviewReportModal';
import CredentialsCard from '@/components/admin/CredentialsCard';
import { Toast, useToast } from '@/components/ui/Toast';

// --- Types ----------------------------------------------------------------------

interface DashboardStats {
    total_interviews: number;
    completed: number;
    pending: number;
    flagged: number;
}

interface CandidateRow extends CandidateResponse {
    summary: InterviewSummaryItem | null;
}

// --- Status badge ---------------------------------------------------------------

const STATUS_STYLES: Record<string, string> = {
    scheduled: 'bg-blue-100 text-blue-800',
    in_progress: 'bg-yellow-100 text-yellow-800',
    completed: 'bg-green-100 text-green-800',
    cancelled: 'bg-gray-100 text-gray-600',
    none: 'bg-slate-100 text-slate-500',
};

const STATUS_LABELS: Record<string, string> = {
    scheduled: 'Scheduled',
    in_progress: 'In Progress',
    completed: 'Completed',
    cancelled: 'Cancelled',
    none: 'No Interview',
};

function InterviewStatusBadge({ status }: { status: string }) {
    const key = status in STATUS_STYLES ? status : 'none';
    return (
        <span className={`px-2.5 py-1 rounded-full text-xs font-semibold whitespace-nowrap ${STATUS_STYLES[key]}`}>
            {STATUS_LABELS[key]}
        </span>
    );
}

const RESUME_STATUS_STYLES: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800',
    success: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    none: 'bg-gray-100 text-gray-500',
};

const RESUME_STATUS_LABELS: Record<string, string> = {
    pending: 'Parsing',
    success: 'Parsed',
    failed: 'Failed',
    none: 'Not Started',
};

function ResumeStatusBadge({ status }: { status?: string | null }) {
    const key = status && status in RESUME_STATUS_STYLES ? status : 'none';
    return (
        <span className={`px-2.5 py-1 rounded-full text-xs font-semibold whitespace-nowrap ${RESUME_STATUS_STYLES[key]}`}>
            {RESUME_STATUS_LABELS[key]}
        </span>
    );
}

function MatchScoreBadge({ score }: { score?: number | null }) {
    if (score == null) return <span className="text-gray-300 text-xs">-</span>;
    const style = score >= 85 ? 'bg-green-100 text-green-800' :
        score >= 70 ? 'bg-yellow-100 text-yellow-800' :
            'bg-red-100 text-red-800';
    return (
        <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${style}`}>
            {score.toFixed(1)}
        </span>
    );
}

// --- Main page ------------------------------------------------------------------

export default function AdminDashboardPage() {
    const router = useRouter();
    const { user, isAuthenticated, logout, _hasHydrated } = useAuthStore();
    const toast = useToast();

    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [candidates, setCandidates] = useState<CandidateRow[]>([]);
    const [totalCandidates, setTotalCandidates] = useState(0);
    const [limit, setLimit] = useState(10);
    const [offset, setOffset] = useState(0);
    const [search, setSearch] = useState('');
    const [sortBy, setSortBy] = useState('created_at');
    const [order, setOrder] = useState('desc');

    const [statsLoading, setStatsLoading] = useState(true);
    const [candidatesLoading, setCandidatesLoading] = useState(true);
    const [error, setError] = useState('');

    // -- Register modal ----------------------------------------------------------
    const [showRegisterModal, setShowRegisterModal] = useState(false);
    const [registerLoading, setRegisterLoading] = useState(false);
    const [registerError, setRegisterError] = useState('');
    const [registerSuccess, setRegisterSuccess] = useState('');
    const [candidateName, setCandidateName] = useState('');
    const [email, setEmail] = useState('');
    const [jobDescription, setJobDescription] = useState('');
    const [resumeFile, setResumeFile] = useState<File | null>(null);
    const [registeredData, setRegisteredData] = useState<{username: string, password?: string} | null>(null);

    // -- Schedule / Reschedule ---------------------------------------------------
    const [scheduleTarget, setScheduleTarget] = useState<CandidateRow | null>(null);
    const [scheduleMode, setScheduleMode] = useState<'schedule' | 'reschedule'>('schedule');

    // -- Cancel ------------------------------------------------------------------
    const [cancelTarget, setCancelTarget] = useState<CandidateRow | null>(null);
    const [summaryTarget, setSummaryTarget] = useState<CandidateRow | null>(null);
    const [reportTarget, setReportTarget] = useState<{ interviewId: string; candidateName: string } | null>(null);
    const [previewTarget, setPreviewTarget] = useState<CandidateRow | null>(null);
    const [cancelLoading, setCancelLoading] = useState(false);

    // --- Auth guard -------------------------------------------------------------
    useEffect(() => {
        if (!_hasHydrated) return;  // wait for localStorage rehydration
        if (!isAuthenticated || !user) { router.push('/login/admin'); return; }
        if (user.role !== 'admin' && user.role !== 'hr') {
            router.push(user.role === 'candidate' ? '/candidate' : '/login/admin');
            return;
        }
        fetchStats();
    }, [_hasHydrated, isAuthenticated, user, router]);


    const fetchStats = async () => {
        setStatsLoading(true);
        try {
            const baseUrl = API_BASE_URL;
            const currentToken = useAuthStore.getState().token;
            const authHeader: Record<string, string> = currentToken ? { 'Authorization': `Bearer ${currentToken}` } : {};

            const res = await fetch(`${baseUrl}/api/v1/dashboard/stats`, {
                headers: {
                    ...authHeader,
                    'Content-Type': 'application/json'
                }
            });
            if (res.ok) {
                setStats(await res.json());
            } else {
                setStats({ total_interviews: 0, completed: 0, pending: 0, flagged: 0 });
            }
        } catch (err) {
            console.error(err);
            setStats({ total_interviews: 0, completed: 0, pending: 0, flagged: 0 });
        } finally {
            setStatsLoading(false);
        }
    };

    const fetchCandidates = useCallback(async () => {
        setCandidatesLoading(true);
        setError('');
        try {
            const baseUrl = API_BASE_URL;
            const currentToken = useAuthStore.getState().token;
            const authHeader: Record<string, string> = currentToken ? { 'Authorization': `Bearer ${currentToken}` } : {};

            const params = new URLSearchParams({
                limit: limit.toString(),
                offset: offset.toString(),
                search: search,
                sort_by: sortBy,
                order: order
            });

            const [candidatesRes, summaryRes] = await Promise.all([
                fetch(`${baseUrl}/api/v1/auth/admin/candidates?${params.toString()}`, { headers: authHeader }).then(async r => {
                    if (!r.ok) throw new Error('Failed to fetch candidates');
                    return r.json();
                }),
                fetch(`${baseUrl}/api/v1/admin/interviews/summary?${params.toString()}`, { headers: authHeader }).then(async r => {
                    if (!r.ok) return { data: [] };
                    return r.json();
                }).catch(() => ({ data: [] })),
            ]);

            setTotalCandidates(candidatesRes.total || 0);

            let summaryData: InterviewSummaryItem[] = summaryRes?.data ?? [];
            if (!Array.isArray(summaryData)) {
                summaryData = [];
            }

            // Build a map: candidate_id -> most-relevant interview summary
            // Priority: scheduled > in_progress > completed > cancelled
            const PRIORITY: Record<string, number> = {
                scheduled: 4, in_progress: 3, completed: 2, cancelled: 1,
            };
            const summaryMap = new Map<string, InterviewSummaryItem>();
            for (const item of summaryData as InterviewSummaryItem[]) {
                const existing = summaryMap.get(item.candidate_id);
                if (!existing || (PRIORITY[item.status] ?? 0) > (PRIORITY[existing.status] ?? 0)) {
                    summaryMap.set(item.candidate_id, item);
                }
            }

            const rows: CandidateRow[] = (candidatesRes.data || []).map((c: any) => ({
                ...c,
                summary: summaryMap.get(c.id) ?? null,
            }));
            setCandidates(rows);
        } catch (err: any) {
            setError(err.message || 'Failed to load candidates.');
        } finally {
            setCandidatesLoading(false);
        }
    }, [limit, offset, search]);

    const fetchData = useCallback(() => {
        fetchStats();
        fetchCandidates();
    }, [fetchCandidates]);

    useEffect(() => {
        if (isAuthenticated) {
            fetchCandidates();
        }
    }, [isAuthenticated, limit, offset, search, sortBy, order, fetchCandidates]);

    // Automatically poll for updates if any candidates are currently being parsed
    useEffect(() => {
        const hasPending = candidates.some(c => c.parse_status === 'pending');
        if (hasPending) {
            const interval = setInterval(() => {
                fetchData();
            }, 5000); // Poll every 5 seconds (fetches both stats and candidates)
            return () => clearInterval(interval);
        }
    }, [candidates, fetchData]);

    // --- Handlers ---------------------------------------------------------------

    const handleLogout = () => { logout(); router.push('/login/admin'); };
    const handleAuthError = () => { logout(); router.push('/login/admin'); };

    const handleToggleLogin = async (candidateId: string) => {
        if (!confirm('Toggle login access for this candidate?')) return;
        try {
            const response = await dashboardService.toggleCandidateLogin(candidateId);
            setCandidates(prev =>
                prev.map(c => c.id === candidateId ? { ...c, login_disabled: response.login_disabled } : c)
            );
            toast.success(response.login_disabled ? 'Login disabled.' : 'Login enabled.');
        } catch (err: any) {
            toast.error(err.message || 'Failed to toggle login status.');
        }
    };

    const handleReparseResume = async (candidateId: string) => {
        try {
            await dashboardService.reparseResume(candidateId);
            toast.success('Reparsing started...');
            fetchCandidates();
        } catch (err: any) {
            toast.error(err.message || 'Failed to trigger reparsing.');
        }
    };

    const handleDeleteCandidate = async (candidateId: string, candidateName: string) => {
        if (!confirm(`Are you absolutely sure you want to delete "${candidateName}" and all associated data? This cannot be undone.`)) {
            return;
        }
        try {
            await dashboardService.deleteCandidate(candidateId);
            toast.success(`Candidate "${candidateName}" deleted.`);
            fetchData();
        } catch (err: any) {
            toast.error(err.message || 'Failed to delete candidate.');
        }
    };

    const onScheduleSuccess = (interviewId?: string) => {
        setScheduleTarget(null);
        toast.success(scheduleMode === 'schedule' ? 'Interview scheduled!' : 'Interview rescheduled!');
        fetchData();
    };

    const handleConfirmCancel = async () => {
        if (!cancelTarget?.summary) return;
        setCancelLoading(true);
        try {
            await cancelInterview(cancelTarget.summary.interview_id);
            toast.success('Interview cancelled.');
            setCancelTarget(null);
            fetchData();
        } catch (err: any) {
            const apiErr = err as SchedulingApiError;
            if (apiErr.status === 401 || apiErr.status === 403) { handleAuthError(); return; }
            toast.error(apiErr.detail || 'Failed to cancel interview.');
        } finally {
            setCancelLoading(false);
        }
    };

    const openRegisterModal = () => {
        setShowRegisterModal(true);
        setRegisterError(''); setRegisterSuccess('');
        setCandidateName(''); setEmail(''); setJobDescription(''); setResumeFile(null);
        setRegisteredData(null);
    };

    const handleRegisterCandidate = async (e: React.FormEvent) => {
        e.preventDefault();
        setRegisterError(''); setRegisterSuccess('');
        if (!candidateName || !email || !jobDescription || !resumeFile) {
            setRegisterError('All fields (Name, Email, JD, Resume) are required.'); return;
        }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            setRegisterError('Please enter a valid email address.'); return;
        }
        setRegisterLoading(true);
        try {
            const formData = new FormData();
            formData.append('candidate_name', candidateName);
            formData.append('candidate_email', email);
            formData.append('job_description', jobDescription);
            formData.append('resume', resumeFile);
            const response = await authService.registerCandidateWithResume(formData);
            setRegisteredData({
                username: response.username,
                password: response.password
            });
            setRegisterSuccess(`"${candidateName}" registered successfully!`);
            fetchData();
        } catch (err: any) {
            setRegisterError(err.message || 'Registration failed. Please try again.');
        } finally {
            setRegisterLoading(false);
        }
    };

    // --- Render -----------------------------------------------------------------

    if ((statsLoading || candidatesLoading) && candidates.length === 0) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
                    <p className="text-gray-600">Loading dashboard...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50">

            {/* -- Candidate Summary Modal -------------------------------------------- */}
            {summaryTarget && summaryTarget.summary?.overall_score != null && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
                    <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 relative animate-in fade-in zoom-in-95">
                        {/* Close */}
                        <button
                            onClick={() => setSummaryTarget(null)}
                            className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>

                        {/* Header */}
                        <div className="mb-5">
                            <h2 className="text-lg font-bold text-gray-900">Interview Results</h2>
                            <p className="text-sm text-gray-500 mt-0.5">{summaryTarget.username} - {summaryTarget.email}</p>
                        </div>

                        {/* Score ring */}
                        <div className="flex flex-col items-center mb-6">
                            {(() => {
                                const score = summaryTarget.summary!.overall_score!;
                                const color = score >= 85 ? '#10b981' : score >= 70 ? '#f59e0b' : '#ef4444';
                                const r = 44;
                                const circ = 2 * Math.PI * r;
                                const dash = circ * (score / 100);
                                return (
                                    <div className="relative flex items-center justify-center w-28 h-28">
                                        <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 100 100">
                                            <circle cx="50" cy="50" r={r} fill="none" stroke="#e5e7eb" strokeWidth="9" />
                                            <circle cx="50" cy="50" r={r} fill="none" stroke={color} strokeWidth="9"
                                                strokeDasharray={`${dash} ${circ}`} strokeLinecap="round" />
                                        </svg>
                                        <div className="z-10 text-center">
                                            <p className="text-2xl font-extrabold text-gray-900">{score.toFixed(1)}</p>
                                            <p className="text-xs text-gray-400">/ 100</p>
                                        </div>
                                    </div>
                                );
                            })()}
                            <p className="mt-2 text-sm text-gray-500">Overall Score</p>
                        </div>

                        {/* Status badge */}
                        <div className="flex justify-center mb-5">
                            {(() => {
                                const score = summaryTarget.summary!.overall_score!;
                                const label = score >= 85 ? 'Strong - Proceed' : score >= 70 ? 'Recommend Review' : 'Needs Improvement';
                                const cls = score >= 85
                                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                    : score >= 70
                                        ? 'bg-amber-50 text-amber-700 border-amber-200'
                                        : 'bg-red-50 text-red-700 border-red-200';
                                return (
                                    <span className={`px-4 py-1.5 rounded-full text-xs font-semibold border ${cls}`}>
                                        {label}
                                    </span>
                                );
                            })()}
                        </div>

                        {/* Meta */}
                        <div className="space-y-2 text-sm border-t border-gray-100 pt-4">
                            <div className="flex justify-between text-gray-600">
                                <span>Status</span>
                                <span className="font-medium capitalize">{summaryTarget.summary?.status}</span>
                            </div>
                            {summaryTarget.summary?.scheduled_at && (
                                <div className="flex justify-between text-gray-600">
                                    <span>Scheduled</span>
                                    <span className="font-medium">{new Date(summaryTarget.summary.scheduled_at).toLocaleString()}</span>
                                </div>
                            )}
                        </div>

                        {/* Close button */}
                        <button
                            onClick={() => setSummaryTarget(null)}
                            className="mt-5 w-full py-2.5 bg-gray-900 text-white rounded-xl text-sm font-semibold hover:bg-gray-700 transition-colors"
                        >
                            Close
                        </button>
                    </div>
                </div>
            )}

            <Toast toasts={toast.toasts} onDismiss={toast.dismiss} />

            {/* Header */}
            <header className="bg-white shadow-sm border-b border-gray-200">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
                    <div className="flex justify-between items-center">
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
                            <p className="text-sm text-gray-600 mt-0.5">Welcome, {user?.username}</p>
                        </div>
                        <div className="flex items-center gap-3">
                            <button
                                onClick={openRegisterModal}
                                className="px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium flex items-center gap-2 shadow-sm text-sm"
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                                </svg>
                                Register Candidate
                            </button>
                            <button
                                onClick={() => router.push('/admin/templates')}
                                className="px-5 py-2.5 bg-white border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium flex items-center gap-2 shadow-sm text-sm"
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4 text-blue-600">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                                </svg>
                                Manage Templates
                            </button>
                            <button onClick={handleLogout} className="px-4 py-2.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium text-sm">
                                Logout
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {error && (
                    <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">{error}</div>
                )}

                {/* Stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                    {[
                        { label: 'Total Interviews', value: stats?.total_interviews ?? 0, color: 'text-gray-900' },
                        { label: 'Completed', value: stats?.completed ?? 0, color: 'text-green-600' },
                        { label: 'Pending Review', value: stats?.pending ?? 0, color: 'text-yellow-600' },
                        { label: 'Candidates', value: totalCandidates, color: 'text-blue-600' },
                    ].map(s => (
                        <div key={s.label} className="bg-white p-5 rounded-lg shadow-sm border border-gray-200">
                            <p className="text-xs font-medium text-gray-700 mb-1">{s.label}</p>
                            <p className={`text-3xl font-bold ${s.color}`}>{s.value}</p>
                        </div>
                    ))}
                </div>

                <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                    <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center bg-white flex-wrap gap-4">
                        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
                            <h2 className="text-lg font-semibold text-gray-900">Registered Candidates ({totalCandidates})</h2>
                            <div className="flex items-center gap-2">
                                <div className="relative">
                                    <span className="absolute inset-y-0 left-0 flex items-center pl-3">
                                        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                                    </span>
                                    <input
                                        type="text"
                                        placeholder="Search candidates..."
                                        value={search}
                                        onChange={(e) => { setSearch(e.target.value); setOffset(0); }}
                                        className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 w-full sm:w-64"
                                    />
                                </div>
                                <select
                                    value={`${sortBy}:${order}`}
                                    onChange={(e) => {
                                        const [s, o] = e.target.value.split(':');
                                        setSortBy(s);
                                        setOrder(o);
                                        setOffset(0);
                                    }}
                                    className="px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                    <option value="created_at:desc">Newest First</option>
                                    <option value="match_score:desc">Match Score (High → Low)</option>
                                    <option value="match_score:asc">Match Score (Low → High)</option>
                                    <option value="username:asc">Name (A-Z)</option>
                                </select>
                            </div>
                        </div>
                        <button onClick={fetchCandidates} disabled={candidatesLoading} className="text-sm text-blue-600 hover:text-blue-800 font-medium disabled:opacity-50 flex items-center gap-1">
                            {candidatesLoading ? (
                                <><svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg> Refreshing...</>
                            ) : 'Refresh'}
                        </button>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead className="bg-gray-50 text-xs uppercase tracking-wider text-gray-700">
                                <tr>
                                    <th className="px-6 py-3 text-left">Name</th>
                                    <th className="px-6 py-3 text-left">Email</th>
                                    <th className="px-6 py-3 text-left">Resume Status</th>
                                    <th className="px-6 py-3 text-left">Match Score</th>
                                    <th className="px-6 py-3 text-left">Interview Status</th>
                                    <th className="px-6 py-3 text-left">Interview Score</th>
                                    <th className="px-6 py-3 text-left">Hiring Signal</th>
                                    <th className="px-6 py-3 text-left">Scheduled At</th>
                                    <th className="px-6 py-3 text-left">Login</th>
                                    <th className="px-6 py-3 text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {candidates.length === 0 ? (
                                    <tr>
                                        <td colSpan={7} className="px-6 py-10 text-center text-gray-600 font-medium">No candidates found.</td>
                                    </tr>
                                ) : (
                                    candidates.map(candidate => {
                                        const s = candidate.summary;
                                        const ivStatus = s?.status ?? 'none';
                                        const canReschedule = ivStatus === 'scheduled';
                                        const canCancel = s && ivStatus !== 'completed' && ivStatus !== 'cancelled';
                                        const canSchedule = !s || ivStatus === 'cancelled' || ivStatus === 'completed';

                                        return (
                                            <tr key={candidate.id} className="hover:bg-gray-50 transition-colors">
                                                <td className="px-6 py-4 font-medium text-gray-900 whitespace-nowrap">{candidate.username}</td>
                                                <td className="px-6 py-4 text-gray-700 whitespace-nowrap">{candidate.email}</td>
                                                <td className="px-6 py-4"><ResumeStatusBadge status={candidate.parse_status} /></td>
                                                <td className="px-6 py-4"><MatchScoreBadge score={candidate.match_score} /></td>
                                                <td className="px-6 py-4"><InterviewStatusBadge status={ivStatus} /></td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    {s?.overall_score != null ? (
                                                        <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold ${s.overall_score >= 85 ? 'bg-emerald-100 text-emerald-800' :
                                                            s.overall_score >= 70 ? 'bg-amber-100 text-amber-800' :
                                                                'bg-red-100 text-red-800'
                                                            }`}>
                                                            {s.overall_score.toFixed(1)}
                                                        </span>
                                                    ) : (
                                                        <span className="text-gray-300 text-xs">-</span>
                                                    )}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    {(candidate.match_score != null && s?.overall_score != null) ? (
                                                        <span className="font-bold text-gray-900 bg-gray-100 px-2 py-1 rounded">
                                                            {(candidate.match_score * 0.6 + s.overall_score * 0.4).toFixed(1)}%
                                                        </span>
                                                    ) : <span className="text-gray-300 text-xs">-</span>}
                                                </td>
                                                <td className="px-6 py-4 text-gray-700 whitespace-nowrap">
                                                    {s?.scheduled_at ? new Date(s.scheduled_at).toLocaleString() : '-'}
                                                </td>
                                                <td className="px-6 py-4">
                                                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${!candidate.login_disabled ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-600'}`}>
                                                        {!candidate.login_disabled ? 'Enabled' : 'Disabled'}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 text-right whitespace-nowrap">
                                                    <div className="flex items-center justify-end gap-2">
                                                        {canSchedule && (
                                                            <div className="relative group">
                                                                <button
                                                                    onClick={() => { setScheduleMode('schedule'); setScheduleTarget(candidate); }}
                                                                    disabled={candidate.parse_status !== 'success'}
                                                                    className="px-3 py-1.5 bg-blue-600 text-white rounded-md text-xs font-semibold hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:bg-gray-400"
                                                                >
                                                                    Schedule
                                                                </button>
                                                                {candidate.parse_status !== 'success' && (
                                                                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-48 p-2 bg-gray-900 text-white text-[10px] rounded shadow-lg z-10 text-center">
                                                                        {candidate.parse_status === 'pending' ? 'Resume still parsing' : 'Parsing failed. Reprocess first'}
                                                                        <div className="absolute top-full left-1/2 -translate-x-1/2 border-8 border-transparent border-t-gray-900"></div>
                                                                    </div>
                                                                )}
                                                            </div>
                                                        )}
                                                        {candidate.parse_status === 'failed' && (
                                                            <button
                                                                onClick={() => handleReparseResume(candidate.id)}
                                                                className="px-3 py-1.5 bg-orange-100 text-orange-700 rounded-md text-xs font-semibold hover:bg-orange-200 transition-colors"
                                                            >
                                                                Reprocess Resume
                                                            </button>
                                                        )}
                                                        {canReschedule && (
                                                            <button
                                                                onClick={() => { setScheduleMode('reschedule'); setScheduleTarget(candidate); }}
                                                                className="px-3 py-1.5 bg-indigo-100 text-indigo-700 rounded-md text-xs font-semibold hover:bg-indigo-200 transition-colors"
                                                            >
                                                                Reschedule
                                                            </button>
                                                        )}
                                                        {canCancel && (
                                                            <button
                                                                onClick={() => setCancelTarget(candidate)}
                                                                className="px-3 py-1.5 bg-red-50 text-red-700 rounded-md text-xs font-semibold hover:bg-red-100 transition-colors"
                                                            >
                                                                Cancel
                                                            </button>
                                                        )}
                                                        {ivStatus === 'completed' && s?.interview_id && (
                                                            <button
                                                                onClick={() => setReportTarget({ interviewId: s.interview_id, candidateName: candidate.username })}
                                                                className="px-3 py-1.5 bg-purple-50 text-purple-700 rounded-md text-xs font-semibold hover:bg-purple-100 transition-colors"
                                                            >
                                                                View Results
                                                            </button>
                                                        )}
                                                        {candidate.parse_status === 'success' && candidate.resume_json && (
                                                            <button
                                                                onClick={() => setPreviewTarget(candidate)}
                                                                className="px-3 py-1.5 bg-blue-50 text-blue-700 rounded-md text-xs font-semibold hover:bg-blue-100 transition-colors"
                                                            >
                                                                View Resume
                                                            </button>
                                                        )}
                                                        <button
                                                            onClick={() => handleToggleLogin(candidate.id)}
                                                            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${candidate.login_disabled ? 'bg-green-50 text-green-700 hover:bg-green-100' : 'bg-orange-50 text-orange-700 hover:bg-orange-100'}`}
                                                        >
                                                            {candidate.login_disabled ? 'Enable Login' : 'Disable Login'}
                                                        </button>
                                                        <button
                                                            onClick={() => handleDeleteCandidate(candidate.id, candidate.username)}
                                                            className="px-3 py-1.5 bg-red-600 text-white rounded-md text-xs font-semibold hover:bg-red-700 transition-colors shadow-sm"
                                                            title="Delete Candidate and all data"
                                                        >
                                                            Delete
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        );
                                    })
                                )}
                            </tbody>
                        </table>
                    </div>
                    {/* Pagination Controls */}
                    <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex items-center justify-between flex-wrap gap-4">
                        <div className="flex items-center gap-2 text-sm text-gray-600">
                            <span>Show</span>
                            <select
                                value={limit}
                                onChange={(e) => { setLimit(Number(e.target.value)); setOffset(0); }}
                                className="border border-gray-300 rounded px-2 py-1 bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                            >
                                <option value={5}>5</option>
                                <option value={10}>10</option>
                                <option value={20}>20</option>
                                <option value={50}>50</option>
                            </select>
                            <span>entries per page</span>
                        </div>
                        <div className="flex items-center gap-4 text-sm">
                            <span className="text-gray-600">
                                Showing {candidates.length > 0 ? offset + 1 : 0} to {Math.min(offset + limit, totalCandidates)} of {totalCandidates} entries
                            </span>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => setOffset(Math.max(0, offset - limit))}
                                    disabled={offset === 0 || candidatesLoading}
                                    className="px-3 py-1.5 border border-gray-300 rounded hover:bg-white disabled:opacity-50 disabled:hover:bg-transparent transition-colors font-medium text-gray-700 bg-gray-100"
                                >
                                    Previous
                                </button>
                                <button
                                    onClick={() => setOffset(offset + limit)}
                                    disabled={offset + limit >= totalCandidates || candidatesLoading}
                                    className="px-3 py-1.5 border border-gray-300 rounded hover:bg-white disabled:opacity-50 disabled:hover:bg-transparent transition-colors font-medium text-gray-700 bg-gray-100"
                                >
                                    Next
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </main>

            {/* Schedule / Reschedule Modal */}
            {scheduleTarget && (
                <ScheduleInterviewModal
                    mode={scheduleMode}
                    candidateId={scheduleTarget.id}
                    candidateName={scheduleTarget.username}
                    roleName={scheduleTarget.role_name}
                    interviewId={scheduleTarget.summary?.interview_id}
                    existingScheduledAt={scheduleTarget.summary?.scheduled_at ?? undefined}
                    onClose={() => setScheduleTarget(null)}
                    onSuccess={onScheduleSuccess}
                    onAuthError={handleAuthError}
                />
            )}

            {/* Resume Preview Modal */}
            {previewTarget && (
                <ResumePreviewModal
                    candidate={previewTarget}
                    onClose={() => setPreviewTarget(null)}
                />
            )}


            {/* Interview Report Modal */}
            {reportTarget && (
                <InterviewReportModal
                    interviewId={reportTarget.interviewId}
                    candidateName={reportTarget.candidateName}
                    onClose={() => setReportTarget(null)}
                    onAuthError={handleAuthError}
                />
            )}

            {/* Cancel Dialog */}
            {cancelTarget && (
                <CancelInterviewDialog
                    candidateName={cancelTarget.username}
                    onConfirm={handleConfirmCancel}
                    onCancel={() => setCancelTarget(null)}
                    loading={cancelLoading}
                />
            )}

            {/* Register Modal */}
            {showRegisterModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
                    <div className="bg-white rounded-xl w-full max-w-md p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
                        <div className="flex justify-between items-center mb-5">
                            <h2 className="text-xl font-bold text-gray-900">Register New Candidate</h2>
                            <button onClick={() => setShowRegisterModal(false)} disabled={registerLoading} className="text-gray-400 hover:text-gray-600">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>

                        {registerSuccess && <div className="mb-4 p-3 bg-green-50 border border-green-200 text-green-700 rounded-lg text-sm">{registerSuccess}</div>}
                        {registerError && <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">{registerError}</div>}

                        {!registeredData ? (
                            <form onSubmit={handleRegisterCandidate} className="space-y-4">
                                {[
                                    { label: 'Candidate Name', value: candidateName, setter: setCandidateName, placeholder: 'Full Name', type: 'text' },
                                    { label: 'Email', value: email, setter: setEmail, placeholder: 'Email address', type: 'email' },
                                ].map(({ label, value, setter, placeholder, type }) => (
                                    <div key={label}>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
                                        <input
                                            type={type} value={value} onChange={e => setter(e.target.value)}
                                            placeholder={placeholder} required disabled={registerLoading}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        />
                                    </div>
                                ))}
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Job Description</label>
                                    <textarea
                                        value={jobDescription} onChange={e => setJobDescription(e.target.value)}
                                        rows={3} placeholder="Paste Job Description here..." required disabled={registerLoading}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Resume (PDF/Doc)</label>
                                    <input
                                        type="file" accept=".pdf,.doc,.docx" required disabled={registerLoading}
                                        onChange={e => setResumeFile(e.target.files?.[0] ?? null)}
                                        className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                                    />
                                </div>
                                <div className="flex gap-3 pt-2">
                                    <button type="button" onClick={() => setShowRegisterModal(false)} disabled={registerLoading} className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm font-medium transition-colors disabled:opacity-50">Cancel</button>
                                    <button type="submit" disabled={registerLoading} className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-semibold transition-colors disabled:opacity-50 flex items-center justify-center gap-2">
                                        {registerLoading ? (
                                            <><svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>Registering...</>
                                        ) : 'Register Candidate'}
                                    </button>
                                </div>
                            </form>
                        ) : (
                            <CredentialsCard 
                                username={registeredData.username} 
                                password={registeredData.password} 
                            />
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

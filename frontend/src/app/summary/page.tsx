'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { useInterviewStore } from '@/store/interviewStore';
import { API_BASE_URL } from '@/lib/apiClient';

// â”€â”€â”€ Types â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

interface SummaryData {
    final_score: number;
    recommendation: 'PROCEED' | 'REVIEW' | 'REJECT';
    fraud_risk: 'LOW' | 'MEDIUM' | 'HIGH';
    strengths: string[];
    gaps: string[];
    notes: string;
    completed_at: string | null;
}

// â”€â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const RECOMMENDATION_CONFIG = {
    PROCEED: { label: 'Proceed to Next Round', bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', dot: 'bg-emerald-500' },
    REVIEW: { label: 'Pending Review', bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', dot: 'bg-amber-500' },
    REJECT: { label: 'Not Selected', bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', dot: 'bg-red-500' },
};

const FRAUD_RISK_CONFIG = {
    LOW: { label: 'Low Risk', color: 'text-emerald-600' },
    MEDIUM: { label: 'Medium Risk', color: 'text-amber-600' },
    HIGH: { label: 'High Risk', color: 'text-red-600' },
};

function ScoreRing({ score }: { score: number }) {
    const pct = score / 100;
    const r = 52;
    const circ = 2 * Math.PI * r;
    const dash = circ * pct;
    const color = score >= 85 ? '#10b981' : score >= 70 ? '#f59e0b' : '#ef4444';

    return (
        <div className="relative flex items-center justify-center w-36 h-36">
            <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 120 120">
                <circle cx="60" cy="60" r={r} fill="none" stroke="#e5e7eb" strokeWidth="10" />
                <circle
                    cx="60" cy="60" r={r} fill="none"
                    stroke={color} strokeWidth="10"
                    strokeDasharray={`${dash} ${circ}`}
                    strokeLinecap="round"
                    style={{ transition: 'stroke-dasharray 1s ease' }}
                />
            </svg>
            <div className="text-center z-10">
                <p className="text-3xl font-extrabold text-gray-900">{score}</p>
                <p className="text-xs text-gray-400 font-medium">/ 100</p>
            </div>
        </div>
    );
}

// â”€â”€â”€ Main Page â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export default function SummaryPage() {
    const router = useRouter();
    const { user, isAuthenticated, logout, _hasHydrated } = useAuthStore();
    const interviewId = useInterviewStore((s) => s.interviewId);
    const candidateToken = useInterviewStore((s) => s.candidateToken);
    const terminate = useInterviewStore((s) => s.terminate);

    const [summary, setSummary] = useState<SummaryData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const fetchSummary = useCallback(async () => {
        if (!interviewId || !candidateToken) {
            // Nothing in store â€” redirect to candidate dashboard
            router.replace('/candidate');
            return;
        }

        const base = API_BASE_URL;
        try {
            const res = await fetch(`${base}/api/v1/session/summary`, {
                headers: {
                    Authorization: `Bearer ${candidateToken}`,
                    'X-Interview-Id': interviewId,
                },
            });
            if (!res.ok) {
                const body = await res.json().catch(() => ({}));
                throw new Error(body.detail || `Error ${res.status}`);
            }
            const data: SummaryData = await res.json();
            setSummary(data);
        } catch (err: any) {
            setError(err.message || 'Failed to load summary.');
        } finally {
            setLoading(false);
        }
    }, [interviewId, candidateToken, router]);

    useEffect(() => {
        if (!_hasHydrated) return;  // wait for localStorage rehydration
        if (!isAuthenticated || !user) { router.push('/login/candidate'); return; }
        if (user.role !== 'candidate') { router.push('/candidate'); return; }
        fetchSummary();
    }, [_hasHydrated, isAuthenticated, user, router, fetchSummary]);

    const handleReturnToDashboard = () => {
        terminate(); // Clear interview store
        router.push('/candidate');
    };

    // â”€â”€â”€ Loading â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
                    <p className="text-gray-500 text-sm">Generating your resultsâ€¦</p>
                </div>
            </div>
        );
    }

    // â”€â”€â”€ Error â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if (error || !summary) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 gap-6">
                <div className="bg-white rounded-xl shadow-sm border border-red-200 p-8 max-w-md w-full text-center">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 text-red-400 mx-auto mb-3" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                    </svg>
                    <h2 className="text-lg font-semibold text-gray-800 mb-1">Could not load summary</h2>
                    <p className="text-sm text-gray-500 mb-5">{error || 'No summary data available.'}</p>
                    <button
                        onClick={handleReturnToDashboard}
                        className="px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 transition-colors"
                    >
                        Back to Dashboard
                    </button>
                </div>
            </div>
        );
    }

    const rec = RECOMMENDATION_CONFIG[summary.recommendation] ?? RECOMMENDATION_CONFIG.REVIEW;
    const risk = FRAUD_RISK_CONFIG[summary.fraud_risk] ?? FRAUD_RISK_CONFIG.LOW;
    const completedDisplay = summary.completed_at
        ? new Date(summary.completed_at).toLocaleString(undefined, { dateStyle: 'full', timeStyle: 'short' })
        : null;

    return (
        <div className="min-h-screen bg-[#f8fafc] text-slate-900 font-sans antialiased pb-12">
            {/* Background Decorations */}
            <div className="fixed inset-0 pointer-events-none overflow-hidden select-none">
                <div className="absolute -top-[10%] -left-[10%] w-[40%] h-[40%] bg-blue-100/40 rounded-full blur-[120px]" />
                <div className="absolute top-[20%] -right-[5%] w-[30%] h-[30%] bg-emerald-100/30 rounded-full blur-[120px]" />
                <div className="absolute -bottom-[10%] left-[20%] w-[50%] h-[50%] bg-indigo-50/50 rounded-full blur-[120px]" />
            </div>

            {/* Header */}
            <header className="sticky top-0 z-20 bg-white/70 backdrop-blur-md border-b border-slate-200/60 shadow-sm">
                <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shadow-lg shadow-blue-200">
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-white" viewBox="0 0 20 20" fill="currentColor">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                            </svg>
                        </div>
                        <div>
                            <h1 className="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-900 to-slate-700">Interview Complete</h1>
                            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-widest leading-none mt-1">Status: Results Processed</p>
                        </div>
                    </div>
                    {completedDisplay && (
                        <div className="px-3 py-1 bg-slate-100/50 border border-slate-200/50 rounded-full hidden sm:block">
                            <span className="text-[11px] font-medium text-slate-500">{completedDisplay}</span>
                        </div>
                    )}
                </div>
            </header>

            <main className="relative z-10 max-w-4xl mx-auto px-6 py-10 space-y-8">

                {/* Hero Card */}
                <div className="bg-white/80 backdrop-blur-xl rounded-[2rem] shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-white/40 overflow-hidden group">
                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 via-indigo-500 to-emerald-500 opacity-80" />

                    <div className="p-8 sm:p-10 flex flex-col md:flex-row items-center gap-10">
                        {/* Score Section */}
                        <div className="relative">
                            <div className="absolute inset-0 bg-blue-100/20 rounded-full blur-2xl scale-110 opacity-50 group-hover:opacity-80 transition-opacity duration-500" />
                            <ScoreRing score={Math.round(summary.final_score)} />
                            <div className="mt-4 text-center">
                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em]">Competency Match</p>
                            </div>
                        </div>

                        {/* Summary Info */}
                        <div className="flex-1 space-y-6 text-center md:text-left">
                            <div className="space-y-3">
                                <div className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-full border text-xs font-bold uppercase tracking-wider ${rec.bg} ${rec.text} ${rec.border} shadow-sm transition-transform hover:scale-105 cursor-default`}>
                                    <span className={`w-2 h-2 rounded-full animate-pulse ${rec.dot}`} />
                                    {rec.label}
                                </div>

                                <h2 className="text-2xl font-extrabold text-slate-800 leading-tight">
                                    Overall Performance Summary
                                </h2>

                                <p className="text-slate-600 leading-relaxed text-sm max-w-2xl">
                                    {summary.notes || "No detailed notes available."}
                                </p>
                            </div>

                            <div className="flex flex-wrap items-center justify-center md:justify-start gap-6 pt-2 border-t border-slate-100">
                                <div className="flex items-center gap-2.5">
                                    <div className="w-8 h-8 rounded-full bg-slate-50 flex items-center justify-center border border-slate-100">
                                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.03l-.53.53c-1.508 1.508-1.508 3.953 0 5.461L4.087 13.2a11.95 11.95 0 001.218 5.72l.983 2.193a1 1 0 001.691.138l2.5-2.5a1 1 0 00-.022-1.428L8 15.3l.006-.006a11.96 11.96 0 011.667-1.666L9.68 13.5l.3-.3a11.956 11.956 0 014.04-2.583" />
                                        </svg>
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Integrity Check</span>
                                        <span className={`text-xs font-bold ${risk.color}`}>{risk.label}</span>
                                    </div>
                                </div>

                                <div className="flex items-center gap-2.5">
                                    <div className="w-8 h-8 rounded-full bg-slate-50 flex items-center justify-center border border-slate-100">
                                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Interview Time</span>
                                        <span className="text-xs font-bold text-slate-600">45 Minutes</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Analysis Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Strengths */}
                    <div className="bg-white/70 backdrop-blur-lg rounded-3xl p-8 border border-white/50 shadow-sm hover:shadow-md transition-all duration-300">
                        <div className="flex items-center gap-3 mb-6">
                            <div className="w-10 h-10 rounded-2xl bg-emerald-50 flex items-center justify-center text-emerald-600 shadow-inner">
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                                </svg>
                            </div>
                            <h3 className="text-lg font-bold text-slate-800">Key Strengths</h3>
                        </div>
                        <ul className="space-y-4">
                            {summary.strengths.length > 0 ? (
                                summary.strengths.map((s, i) => (
                                    <li key={i} className="flex items-start gap-3 group">
                                        <div className="mt-1.5 w-4 h-4 rounded-full bg-emerald-100 flex items-center justify-center flex-shrink-0 transition-transform group-hover:scale-110">
                                            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                                        </div>
                                        <span className="text-sm font-medium text-slate-600 leading-normal group-hover:text-slate-900 transition-colors">{s}</span>
                                    </li>
                                ))
                            ) : (
                                <p className="text-slate-400 text-sm italic">No specific strengths identified.</p>
                            )}
                        </ul>
                    </div>

                    {/* Improvement Gaps */}
                    <div className="bg-white/70 backdrop-blur-lg rounded-3xl p-8 border border-white/50 shadow-sm hover:shadow-md transition-all duration-300">
                        <div className="flex items-center gap-3 mb-6">
                            <div className="w-10 h-10 rounded-2xl bg-amber-50 flex items-center justify-center text-amber-600 shadow-inner">
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                </svg>
                            </div>
                            <h3 className="text-lg font-bold text-slate-800">Areas to Improve</h3>
                        </div>
                        <ul className="space-y-4">
                            {summary.gaps.length > 0 ? (
                                summary.gaps.map((g, i) => (
                                    <li key={i} className="flex items-start gap-3 group">
                                        <div className="mt-1.5 w-4 h-4 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0 transition-transform group-hover:scale-110">
                                            <div className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                                        </div>
                                        <span className="text-sm font-medium text-slate-600 leading-normal group-hover:text-slate-900 transition-colors">{g}</span>
                                    </li>
                                ))
                            ) : (
                                <p className="text-slate-400 text-sm italic">No significant gaps identified.</p>
                            )}
                        </ul>
                    </div>
                </div>

                {/* Footer Section (What's Next) */}
                <div className="relative overflow-hidden bg-slate-900 rounded-[2.5rem] p-8 sm:p-10 shadow-2xl">
                    <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl -mr-32 -mt-32" />
                    <div className="absolute bottom-0 left-0 w-48 h-48 bg-indigo-500/10 rounded-full blur-3xl -ml-24 -mb-24" />

                    <div className="relative flex flex-col md:flex-row items-center gap-8 justify-between">
                        <div className="flex-1 space-y-3 text-center md:text-left">
                            <h4 className="text-xl font-bold text-white">Next Steps</h4>
                            <p className="text-slate-400 text-sm leading-relaxed max-w-sm">
                                Your full evaluation has been sent to the recruitment team. They will review all materials and reach out within 3-5 business days.
                            </p>
                        </div>

                        <button
                            onClick={handleReturnToDashboard}
                            className="group flex items-center gap-3 px-8 py-4 bg-white text-slate-900 rounded-2xl font-bold hover:bg-slate-50 transition-all duration-300 shadow-[0_10px_20px_rgba(0,0,0,0.1)] active:scale-95"
                        >
                            Return to Dashboard
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                            </svg>
                        </button>
                    </div>
                </div>

                <div className="text-center pt-4">
                    <p className="text-[11px] font-medium text-slate-400 uppercase tracking-widest">
                        Confidential &bull; Automated Interview Systems &bull; v2.4.0
                    </p>
                </div>
            </main>
        </div>
    );
}

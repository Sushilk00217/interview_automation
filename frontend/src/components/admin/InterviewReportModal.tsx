'use client';

import { useState, useEffect } from 'react';
import { fetchInterviewReport, InterviewReport, SchedulingApiError } from '@/lib/api/interviews';

interface InterviewReportModalProps {
    interviewId: string;
    candidateName: string;
    onClose: () => void;
    onAuthError: () => void;
}

export default function InterviewReportModal({
    interviewId,
    candidateName,
    onClose,
    onAuthError,
}: InterviewReportModalProps) {
    const [report, setReport] = useState<InterviewReport | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        loadReport();
    }, [interviewId]);

    const loadReport = async () => {
        setLoading(true);
        setError('');
        try {
            const data = await fetchInterviewReport(interviewId);
            setReport(data);
        } catch (err: any) {
            const apiErr = err as SchedulingApiError;
            if (apiErr.status === 401 || apiErr.status === 403) {
                onAuthError();
                return;
            }
            setError(apiErr.detail || 'Failed to load report');
        } finally {
            setLoading(false);
        }
    };

    const getScoreColor = (score: number) => {
        if (score >= 8) return 'text-green-600';
        if (score >= 6.5) return 'text-blue-600';
        if (score >= 5) return 'text-yellow-600';
        return 'text-red-600';
    };

    const getRecommendationColor = (recommendation: string) => {
        if (recommendation === 'STRONG_HIRE' || recommendation === 'HIRE') return 'bg-green-50 text-green-700 border-green-200';
        if (recommendation === 'CONSIDER') return 'bg-yellow-50 text-yellow-700 border-yellow-200';
        return 'bg-red-50 text-red-700 border-red-200';
    };

    return (
        <div
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50 overflow-y-auto"
            onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
        >
            <div className="bg-white rounded-xl w-full max-w-5xl shadow-2xl max-h-[90vh] flex flex-col my-8">
                {/* Header */}
                <div className="bg-gradient-to-r from-purple-600 to-indigo-600 px-6 py-5 flex-shrink-0">
                    <div className="flex justify-between items-center">
                        <div>
                            <h2 className="text-xl font-bold text-white">Interview Report</h2>
                            <p className="text-purple-100 text-sm mt-0.5">{candidateName}</p>
                        </div>
                        <button
                            onClick={onClose}
                            className="text-purple-200 hover:text-white transition-colors p-1 rounded"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                </div>

                {/* Body */}
                <div className="flex-1 overflow-y-auto p-6">
                    {loading ? (
                        <div className="flex items-center justify-center py-12">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
                        </div>
                    ) : error ? (
                        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
                            {error}
                        </div>
                    ) : report ? (
                        <div className="space-y-6">
                            {/* Overall Score */}
                            <div className="bg-gradient-to-br from-purple-50 to-indigo-50 rounded-lg p-6 border border-purple-200">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-2">Overall Score</h3>
                                        <div className="flex items-baseline gap-2">
                                            <span className={`text-4xl font-bold ${getScoreColor(report.overall_score)}`}>
                                                {report.overall_score.toFixed(1)}
                                            </span>
                                            <span className="text-gray-500 text-lg">/ 10</span>
                                        </div>
                                        <p className="text-sm text-gray-600 mt-2">
                                            Answered {report.answered_questions} of {report.total_questions} questions
                                        </p>
                                    </div>
                                    <div className="text-right">
                                        <div className={`px-4 py-2 rounded-full text-sm font-semibold border ${getRecommendationColor(report.recommendation)}`}>
                                            {report.recommendation.replace('_', ' ')}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Recommendation */}
                            <div className="bg-white border border-gray-200 rounded-lg p-4">
                                <h3 className="text-sm font-semibold text-gray-700 mb-2">Recommendation</h3>
                                <p className="text-gray-600 text-sm">{report.recommendation_reason}</p>
                            </div>

                            {/* Strengths & Weaknesses */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                                    <h3 className="text-sm font-semibold text-green-800 mb-2">Strengths</h3>
                                    <ul className="space-y-1">
                                        {report.strengths.length > 0 ? (
                                            report.strengths.map((strength, idx) => (
                                                <li key={idx} className="text-sm text-green-700 flex items-start gap-2">
                                                    <span className="text-green-500 mt-0.5">✓</span>
                                                    <span>{strength}</span>
                                                </li>
                                            ))
                                        ) : (
                                            <li className="text-sm text-green-600 italic">No specific strengths identified</li>
                                        )}
                                    </ul>
                                </div>
                                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                                    <h3 className="text-sm font-semibold text-red-800 mb-2">Areas for Improvement</h3>
                                    <ul className="space-y-1">
                                        {report.weaknesses.length > 0 ? (
                                            report.weaknesses.map((weakness, idx) => (
                                                <li key={idx} className="text-sm text-red-700 flex items-start gap-2">
                                                    <span className="text-red-500 mt-0.5">•</span>
                                                    <span>{weakness}</span>
                                                </li>
                                            ))
                                        ) : (
                                            <li className="text-sm text-red-600 italic">No specific weaknesses identified</li>
                                        )}
                                    </ul>
                                </div>
                            </div>

                            {/* Question Breakdown */}
                            <div>
                                <h3 className="text-lg font-semibold text-gray-900 mb-4">Question-by-Question Breakdown</h3>
                                <div className="space-y-4">
                                    {report.question_breakdown.map((q, idx) => (
                                        <div key={q.question_id} className="bg-white border border-gray-200 rounded-lg p-5 hover:border-purple-300 transition-colors">
                                            <div className="flex justify-between items-start mb-3">
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-2 mb-2">
                                                        <span className="bg-purple-100 text-purple-700 text-xs font-bold px-2 py-1 rounded">
                                                            Q{idx + 1} • {q.question_type.toUpperCase()}
                                                        </span>
                                                        {q.score !== null && (
                                                            <span className={`text-lg font-bold ${getScoreColor(q.score)}`}>
                                                                {q.score.toFixed(1)}/10
                                                            </span>
                                                        )}
                                                    </div>
                                                    <p className="text-gray-800 font-medium mb-2">{q.question_text}</p>
                                                </div>
                                            </div>
                                            
                                            <div className="mt-3 pt-3 border-t border-gray-100">
                                                <p className="text-sm text-gray-600 mb-2">
                                                    <span className="font-semibold">Answer:</span> {q.answer_text || 'Audio answer'}
                                                </p>
                                                {q.feedback && (
                                                    <div className="bg-blue-50 border border-blue-200 rounded p-3 mt-2">
                                                        <p className="text-sm text-blue-800">
                                                            <span className="font-semibold">Feedback:</span> {q.feedback}
                                                        </p>
                                                    </div>
                                                )}
                                                {(q.strengths.length > 0 || q.weaknesses.length > 0) && (
                                                    <div className="grid grid-cols-2 gap-3 mt-3">
                                                        {q.strengths.length > 0 && (
                                                            <div>
                                                                <p className="text-xs font-semibold text-green-700 mb-1">Strengths:</p>
                                                                <ul className="space-y-1">
                                                                    {q.strengths.map((s, i) => (
                                                                        <li key={i} className="text-xs text-green-600">✓ {s}</li>
                                                                    ))}
                                                                </ul>
                                                            </div>
                                                        )}
                                                        {q.weaknesses.length > 0 && (
                                                            <div>
                                                                <p className="text-xs font-semibold text-red-700 mb-1">Improvements:</p>
                                                                <ul className="space-y-1">
                                                                    {q.weaknesses.map((w, i) => (
                                                                        <li key={i} className="text-xs text-red-600">• {w}</li>
                                                                    ))}
                                                                </ul>
                                                            </div>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Proctoring Summary */}
                            {report.proctoring_summary && (
                                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                                    <h3 className="text-sm font-semibold text-gray-700 mb-2">Proctoring Summary</h3>
                                    <div className="grid grid-cols-3 gap-4 text-sm">
                                        <div>
                                            <span className="text-gray-600">Face Alerts:</span>
                                            <span className="ml-2 font-semibold">{report.proctoring_summary.face_verification_alerts}</span>
                                        </div>
                                        <div>
                                            <span className="text-gray-600">Voice Alerts:</span>
                                            <span className="ml-2 font-semibold">{report.proctoring_summary.voice_verification_alerts}</span>
                                        </div>
                                        {report.proctoring_summary.termination_reason && (
                                            <div className="col-span-3">
                                                <span className="text-gray-600">Termination Reason:</span>
                                                <span className="ml-2 text-red-600">{report.proctoring_summary.termination_reason}</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    ) : null}
                </div>

                {/* Footer */}
                <div className="border-t border-gray-200 px-6 py-4 flex justify-end flex-shrink-0">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-semibold hover:bg-gray-700 transition-colors"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
}

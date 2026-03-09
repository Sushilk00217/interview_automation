'use client';

import { useState, useEffect } from 'react';
import { InterviewTemplate } from '@/types/interview';
import { scheduleInterview, rescheduleInterview, previewTemplate } from '@/lib/api/interviews';
import { getTemplates } from '@/lib/api/templates';
import { SchedulingApiError, TemplatePreviewQuestion } from '@/types/interview';

type ModalMode = 'schedule' | 'reschedule';

interface ScheduleInterviewModalProps {
    /** 'schedule' opens a blank form; 'reschedule' prefills scheduled_at */
    mode: ModalMode;
    candidateId: string;
    candidateName: string;
    /** Required when mode === 'reschedule' */
    interviewId?: string;
    /** Prefill datetime for reschedule */
    existingScheduledAt?: string;
    onClose: () => void;
    onSuccess: (interviewId?: string) => void;
    onAuthError: () => void;
}

export default function ScheduleInterviewModal({
    mode,
    candidateId,
    candidateName,
    roleName,
    interviewId,
    existingScheduledAt,
    onClose,
    onSuccess,
    onAuthError,
}: ScheduleInterviewModalProps & { roleName?: string | null }) {
    const [templates, setTemplates] = useState<InterviewTemplate[]>([]);
    const [templateId, setTemplateId] = useState('');
    // ... rest of the component
    // Default to current local datetime in "YYYY-MM-DDTHH:mm" format
    const nowLocal = () => {
        const d = new Date();
        // Offset by timezone so the value matches the local time in the input
        d.setSeconds(0, 0);
        const offset = d.getTimezoneOffset() * 60000;
        return new Date(d.getTime() - offset).toISOString().slice(0, 16);
    };

    const [previewQuestions, setPreviewQuestions] = useState<TemplatePreviewQuestion[]>([]);
    const [previewCodingProblems, setPreviewCodingProblems] = useState<{ problem_id: string; title: string; difficulty: string }[]>([]);
    const [previewConvRounds, setPreviewConvRounds] = useState<number>(0);
    const [previewLoading, setPreviewLoading] = useState(false);
    const [draftInterviewId, setDraftInterviewId] = useState<string | null>(null);
    const [regeneratingId, setRegeneratingId] = useState<string | null>(null);
    const [regenComment, setRegenComment] = useState('');
    const [showRegenPrompt, setShowRegenPrompt] = useState<string | null>(null);

    // ─── Fetch preview when templateId changes ───────────────────────────────
    useEffect(() => {
        if (mode !== 'schedule' || !templateId) {
            setPreviewQuestions([]);
            setPreviewCodingProblems([]);
            setPreviewConvRounds(0);
            return;
        }

        setPreviewLoading(true);
        previewTemplate(templateId, candidateId)
            .then((data) => {
                setDraftInterviewId(data.interview_id || null);
                // Technical questions
                const rawQuestions = data.technical_section?.questions ?? [];
                setPreviewQuestions(rawQuestions.map(q => ({ ...q, originalText: q.text })));
                // Coding problems
                setPreviewCodingProblems(data.coding_section?.problems ?? []);
                // Conversational rounds
                setPreviewConvRounds(data.conversational_section?.rounds ?? 0);
            })
            .catch((err: SchedulingApiError) => {
                setError(`Failed to load template preview: ${err.detail || 'Unknown error'}`);
                setPreviewQuestions([]);
                setPreviewCodingProblems([]);
                setPreviewConvRounds(0);
                setDraftInterviewId(null);
            })
            .finally(() => setPreviewLoading(false));
    }, [templateId, mode, candidateId]);

    const [scheduledAt, setScheduledAt] = useState(nowLocal);
    const [loading, setLoading] = useState(false);
    const [templatesLoading, setTemplatesLoading] = useState(false);
    const [error, setError] = useState('');
    const [editingIdx, setEditingIdx] = useState<number | null>(null);
    const [tempEditText, setTempEditText] = useState('');

    // ─── Prefill for reschedule ───────────────────────────────────────────────
    useEffect(() => {
        if (mode === 'reschedule' && existingScheduledAt) {
            setScheduledAt(new Date(existingScheduledAt).toISOString().slice(0, 16));
        }
    }, [mode, existingScheduledAt]);

    // ─── Load templates (schedule mode only) ─────────────────────────────────
    useEffect(() => {
        if (mode !== 'schedule') return;
        setTemplatesLoading(true);

        // Fetch templates, potentially filtered by role
        getTemplates()
            .then((data) => {
                const active = data.filter((t) => t.is_active);
                setTemplates(active);

                // PART 6: Auto-select logic
                if (active.length > 0 && !templateId) {
                    // 1. Try to find default for role
                    const defaultForRole = active.find(t => t.role_name === roleName && t.is_default_for_role);
                    if (defaultForRole) {
                        setTemplateId(defaultForRole.id);
                    } else {
                        // 2. Fallback to first available
                        setTemplateId(active[0].id);
                    }
                }
            })
            .catch((err: SchedulingApiError) => {
                if (err.status === 401 || err.status === 403) onAuthError();
                setTemplates([]);
                setTemplateId('');
            })
            .finally(() => setTemplatesLoading(false));
    }, [mode, onAuthError, templateId, roleName]);

    // ─── Accessibility: Close on Escape ───────────────────────────────────────
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && !loading) onClose();
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [onClose, loading]);

    const handleRegenerate = async (questionId: string) => {
        if (!draftInterviewId) return;
        setRegeneratingId(questionId);
        try {
            const importApi = await import('@/lib/api/interviews');
            const newQ = await importApi.regenerateQuestion(draftInterviewId, questionId, regenComment);

            setPreviewQuestions(prev => prev.map(q =>
                q.question_id === questionId ? { ...newQ, originalText: newQ.text } : q
            ));
            setShowRegenPrompt(null);
            setRegenComment('');
        } catch (err: any) {
            setError(`Failed to regenerate question: ${err.detail || err.message}`);
        } finally {
            setRegeneratingId(null);
        }
    };

    // ─── Submit ───────────────────────────────────────────────────────────────
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (!scheduledAt) {
            setError('Please select a date and time.');
            return;
        }

        if (mode === 'schedule' && !templateId) {
            setError('Please select an interview template.');
            return;
        }

        setLoading(true);
        try {
            const isoAt = new Date(scheduledAt).toISOString();

            if (mode === 'schedule') {
                const questions = [
                    ...previewQuestions.map((q, idx) => ({
                        question_id: q.question_id,
                        custom_text: q.text !== q.originalText ? q.text : undefined,
                        order: idx + 1
                    })),
                    ...previewCodingProblems.map((p, idx) => ({
                        question_id: p.problem_id,
                        order: previewQuestions.length + idx + 1
                    }))
                ];
                const response = await scheduleInterview({
                    candidate_id: candidateId,
                    template_id: templateId,
                    scheduled_at: isoAt,
                    questions,
                    draft_interview_id: draftInterviewId || undefined
                });
                onSuccess(response.id); // Pass interview ID to show questions modal
            } else {
                if (!interviewId) throw new Error('Missing interview ID for reschedule');
                await rescheduleInterview(interviewId, { scheduled_at: isoAt });
                onSuccess();
            }
        } catch (err: any) {
            const apiErr = err as SchedulingApiError;
            if (apiErr.status === 401 || apiErr.status === 403) {
                onAuthError();
                return;
            }
            if (apiErr.status === 409) {
                setError('Candidate already has an active interview (scheduled or in progress).');
            } else {
                setError(apiErr.detail || 'An unexpected error occurred.');
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50 overflow-hidden"
            onClick={(e) => { if (e.target === e.currentTarget && !loading) onClose(); }}
        >
            <div className="bg-white rounded-xl w-full max-w-3xl shadow-2xl overflow-hidden max-h-[95vh] flex flex-col">
                {/* Header */}
                <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-5">
                    <div className="flex justify-between items-start">
                        <div>
                            <h2 className="text-xl font-bold text-white">
                                {mode === 'schedule' ? 'Schedule Interview' : 'Reschedule Interview'}
                            </h2>
                            <p className="text-blue-100 text-sm mt-0.5">Candidate: <span className="font-semibold">{candidateName}</span></p>
                        </div>
                        <button
                            onClick={onClose}
                            disabled={loading}
                            className="text-blue-200 hover:text-white transition-colors p-1 rounded"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                </div>

                {/* Body - Scrollable */}
                <form onSubmit={handleSubmit} className="p-6 space-y-5 overflow-y-auto flex-1">
                    {/* Error banner */}
                    {error && (
                        <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                            <svg className="w-4 h-4 mt-0.5 shrink-0 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
                            </svg>
                            <span>{error}</span>
                        </div>
                    )}

                    {/* Template selector (schedule only) */}
                    {mode === 'schedule' && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1.5">
                                Interview Template <span className="text-red-500">*</span>
                            </label>
                            {templatesLoading ? (
                                <div className="flex items-center gap-2 text-sm text-gray-500 py-2">
                                    <svg className="animate-spin w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                    </svg>
                                    Loading templates…
                                </div>
                            ) : (
                                <select
                                    value={templateId}
                                    onChange={(e) => setTemplateId(e.target.value)}
                                    required
                                    disabled={loading}
                                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white disabled:bg-gray-50"
                                >
                                    {templates.length === 0 && (
                                        <option value="" className="text-gray-900">No active templates available</option>
                                    )}
                                    {templates.map((t) => (
                                        <option key={t.id} value={t.id} className="text-gray-900">
                                            {t.title}
                                        </option>
                                    ))}
                                </select>
                            )}
                        </div>
                    )}

                    {/* ── Preview Panel ── */}
                    {mode === 'schedule' && templateId && (
                        <div className="space-y-3">
                            <p className="text-xs font-bold uppercase tracking-widest text-gray-400">Interview Preview</p>

                            {previewLoading ? (
                                <div className="text-sm text-gray-500 italic flex items-center gap-2">
                                    <svg className="animate-spin h-4 w-4 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    Generating preview...
                                </div>
                            ) : (
                                <div className="space-y-3">

                                    {/* ── Technical Questions ── */}
                                    {previewQuestions.length > 0 && (
                                        <div>
                                            <div className="flex items-center gap-2 mb-2">
                                                <span className="w-2 h-2 rounded-full bg-blue-500 shrink-0" />
                                                <p className="text-xs font-bold text-gray-700 uppercase tracking-wide">
                                                    Technical Questions ({previewQuestions.length})
                                                </p>
                                            </div>
                                            <div className="space-y-3 max-h-80 overflow-y-auto pr-2 custom-scrollbar">
                                                {previewQuestions.map((q, idx) => (
                                                    <div key={idx} className="group relative bg-white border hover:border-blue-200 rounded-lg p-3 transition-all duration-200 shadow-sm">
                                                        <div className="flex justify-between items-center mb-1.5">
                                                            <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
                                                                Q{idx + 1} • {q.difficulty} • {q.category}
                                                            </span>
                                                            <div className="flex items-center gap-2">
                                                                {editingIdx !== idx && (
                                                                    <>
                                                                        <button type="button" onClick={() => setShowRegenPrompt(q.question_id)}
                                                                            disabled={regeneratingId === q.question_id}
                                                                            className="text-[10px] font-bold text-emerald-600 hover:text-emerald-700 uppercase disabled:opacity-50">
                                                                            {regeneratingId === q.question_id ? 'Regenerating...' : 'Regenerate'}
                                                                        </button>
                                                                        <button type="button" onClick={() => { setEditingIdx(idx); setTempEditText(q.text || (q as any).prompt); }}
                                                                            className="text-[10px] font-bold text-blue-500 hover:text-blue-700 uppercase">
                                                                            Edit
                                                                        </button>
                                                                    </>
                                                                )}
                                                                <button type="button"
                                                                    onClick={() => setPreviewQuestions(prev => prev.filter((_, i) => i !== idx))}
                                                                    className="text-gray-300 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100"
                                                                    title="Remove question">
                                                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                                    </svg>
                                                                </button>
                                                            </div>
                                                        </div>
                                                        {editingIdx === idx ? (
                                                            <div className="space-y-2">
                                                                <textarea autoFocus value={tempEditText}
                                                                    onChange={(e) => setTempEditText(e.target.value)}
                                                                    className="w-full text-sm text-gray-700 bg-white border border-blue-100 rounded p-2 focus:ring-1 focus:ring-blue-500 outline-none resize-none"
                                                                    rows={3} />
                                                                <div className="flex justify-end gap-2">
                                                                    <button type="button" onClick={() => setEditingIdx(null)}
                                                                        className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1">Cancel</button>
                                                                    <button type="button"
                                                                        onClick={async () => {
                                                                            const updated = previewQuestions.map((item, i) => i === idx ? { ...item, text: tempEditText } : item);
                                                                            setPreviewQuestions(updated);
                                                                            setEditingIdx(null);

                                                                            // PERSIST to backend draft if it exists
                                                                            if (draftInterviewId) {
                                                                                const { updateInterviewQuestions } = await import('@/lib/api/interviews');
                                                                                try {
                                                                                    await updateInterviewQuestions(draftInterviewId, updated.map((q, i) => ({
                                                                                        question_id: q.question_id,
                                                                                        order: i + 1,
                                                                                        prompt: q.text,
                                                                                        question_type: 'static',
                                                                                        difficulty: q.difficulty as any,
                                                                                        time_limit_sec: 60 // Default
                                                                                    })));
                                                                                } catch (err) {
                                                                                    console.error("Failed to persist edits to draft:", err);
                                                                                }
                                                                            }
                                                                        }}
                                                                        className="text-xs bg-blue-500 text-white px-2 py-1 rounded hover:bg-blue-600">Save</button>
                                                                </div>
                                                            </div>
                                                        ) : showRegenPrompt === q.question_id ? (
                                                            <div className="space-y-2 p-2 bg-emerald-50 rounded border border-emerald-100 animate-in fade-in slide-in-from-top-1">
                                                                <p className="text-[10px] font-bold text-emerald-700 uppercase">Regeneration Instructions (Optional)</p>
                                                                <textarea
                                                                    value={regenComment}
                                                                    onChange={(e) => setRegenComment(e.target.value)}
                                                                    placeholder="e.g. Make it more advanced, focus on React hooks..."
                                                                    className="w-full text-xs text-gray-700 bg-white border border-emerald-200 rounded p-2 focus:ring-1 focus:ring-emerald-500 outline-none resize-none"
                                                                    rows={2}
                                                                />
                                                                <div className="flex justify-end gap-2">
                                                                    <button type="button" onClick={() => setShowRegenPrompt(null)}
                                                                        className="text-[10px] font-bold text-gray-400 hover:text-gray-600 uppercase">Cancel</button>
                                                                    <button type="button"
                                                                        onClick={() => handleRegenerate(q.question_id)}
                                                                        className="text-[10px] font-bold bg-emerald-600 text-white px-2 py-1 rounded hover:bg-emerald-700 uppercase">
                                                                        Regenerate Now
                                                                    </button>
                                                                </div>
                                                            </div>
                                                        ) : (
                                                            <p className="text-sm text-gray-700 font-medium leading-relaxed whitespace-pre-wrap">{q.text || (q as any).prompt}</p>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* ── Coding Problems ── */}
                                    {previewCodingProblems.length > 0 && (
                                        <div>
                                            <div className="flex items-center gap-2 mb-2">
                                                <span className="w-2 h-2 rounded-full bg-purple-500 shrink-0" />
                                                <p className="text-xs font-bold text-gray-700 uppercase tracking-wide">
                                                    Coding Problems ({previewCodingProblems.length})
                                                </p>
                                            </div>
                                            <div className="overflow-hidden border border-purple-100 rounded-lg shadow-sm">
                                                <table className="w-full text-left border-collapse">
                                                    <thead>
                                                        <tr className="bg-purple-50/50">
                                                            <th className="px-3 py-2 text-[10px] font-bold text-purple-700 uppercase tracking-wider">#</th>
                                                            <th className="px-3 py-2 text-[10px] font-bold text-purple-700 uppercase tracking-wider">Problem Title</th>
                                                            <th className="px-3 py-2 text-[10px] font-bold text-purple-700 uppercase tracking-wider text-right">Difficulty</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody className="divide-y divide-purple-50">
                                                        {previewCodingProblems.map((p, idx) => {
                                                            const diffColor: Record<string, string> = {
                                                                easy: 'text-green-600 bg-green-50 border-green-100',
                                                                medium: 'text-amber-600 bg-amber-50 border-amber-100',
                                                                hard: 'text-red-600 bg-red-50 border-red-100',
                                                            };
                                                            const colorClass = diffColor[p.difficulty?.toLowerCase()] || 'text-gray-600 bg-gray-50 border-gray-100';
                                                            return (
                                                                <tr key={idx} className="hover:bg-purple-50/30 transition-colors">
                                                                    <td className="px-3 py-2.5 text-xs text-gray-500 font-medium">{idx + 1}</td>
                                                                    <td className="px-3 py-2.5 text-sm font-semibold text-gray-800">{p.title}</td>
                                                                    <td className="px-3 py-2.5 text-right">
                                                                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border ${colorClass}`}>
                                                                            {p.difficulty}
                                                                        </span>
                                                                    </td>
                                                                </tr>
                                                            );
                                                        })}
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                    )}

                                    {/* ── Conversational Section ── */}
                                    {previewConvRounds > 0 && (
                                        <div>
                                            <div className="flex items-center gap-2 mb-2">
                                                <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
                                                <p className="text-xs font-bold text-gray-700 uppercase tracking-wide">Conversational Interview</p>
                                            </div>
                                            <div className="flex items-start gap-3 bg-emerald-50 border border-emerald-100 rounded-lg px-4 py-3">
                                                <svg className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-3 3-3-3z" />
                                                </svg>
                                                <p className="text-sm text-emerald-800">
                                                    <span className="font-bold">{previewConvRounds} AI-driven round{previewConvRounds !== 1 ? 's' : ''}</span>
                                                    {' '}based on candidate resume and job description.
                                                </p>
                                            </div>
                                        </div>
                                    )}

                                    {/* Empty state — nothing in any section */}
                                    {previewQuestions.length === 0 && previewCodingProblems.length === 0 && previewConvRounds === 0 && (
                                        <div className="text-center py-6 border-2 border-dashed border-gray-100 rounded-lg">
                                            <p className="text-xs text-gray-400">No preview available for this template.</p>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Date & Time picker */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1.5">
                            {mode === 'reschedule' ? 'New ' : ''}Date & Time (IST / Local) <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="datetime-local"
                            value={scheduledAt}
                            onChange={(e) => setScheduledAt(e.target.value)}
                            required
                            disabled={loading}
                            className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50"
                        />
                        <p className="mt-1 text-xs text-gray-600">Defaults to now — adjust as needed.</p>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-3 pt-2">
                        <button
                            type="button"
                            onClick={onClose}
                            disabled={loading}
                            className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium disabled:opacity-50"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={loading || (mode === 'schedule' && !templateId)}
                            className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                        >
                            {loading ? (
                                <>
                                    <svg className="animate-spin w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                    </svg>
                                    {mode === 'schedule' ? 'Scheduling…' : 'Rescheduling…'}
                                </>
                            ) : mode === 'schedule' ? (
                                'Schedule Interview'
                            ) : (
                                'Confirm Reschedule'
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

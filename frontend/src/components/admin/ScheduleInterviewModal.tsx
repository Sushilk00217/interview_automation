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
    onSuccess: () => void;
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
    const [previewLoading, setPreviewLoading] = useState(false);

    // ─── Fetch preview when templateId changes ───────────────────────────────
    useEffect(() => {
        if (mode !== 'schedule' || !templateId) {
            setPreviewQuestions([]); // Clear preview if templateId is not selected or mode is not schedule
            return;
        }

        setPreviewLoading(true);
        previewTemplate(templateId)
            .then((data) => {
                // Store original text for comparison on submission
                const augmented = data.questions.map(q => ({
                    ...q,
                    originalText: q.text
                }));
                setPreviewQuestions(augmented);
            })
            .catch((err: SchedulingApiError) => {
                setError(`Failed to load template preview: ${err.detail}`);
                setPreviewQuestions([]);
            })
            .finally(() => setPreviewLoading(false));
    }, [templateId, mode]);

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
                const questions = previewQuestions.map((q, idx) => ({
                    question_id: q.question_id,
                    // Fix: send custom_text ONLY if modified.
                    custom_text: q.text !== q.originalText ? q.text : undefined,
                    order: idx + 1
                }));
                await scheduleInterview({
                    candidate_id: candidateId,
                    template_id: templateId,
                    scheduled_at: isoAt,
                    questions
                });
            } else {
                if (!interviewId) throw new Error('Missing interview ID for reschedule');
                await rescheduleInterview(interviewId, { scheduled_at: isoAt });
            }
            onSuccess();
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
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-xl w-full max-w-md shadow-2xl overflow-hidden">
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

                {/* Body */}
                <form onSubmit={handleSubmit} className="p-6 space-y-5">
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

                    {/* Preview Questions (Editable List) */}
                    {mode === 'schedule' && templateId && (
                        <div className="space-y-3">
                            <label className="block text-sm font-medium text-gray-700">
                                Interview Questions ({previewQuestions.length})
                            </label>

                            {previewLoading ? (
                                <div className="text-sm text-gray-500 italic flex items-center gap-2">
                                    <svg className="animate-spin h-4 w-4 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    Generating preview...
                                </div>
                            ) : (
                                <div className="space-y-3 max-h-60 overflow-y-auto pr-2 custom-scrollbar border border-gray-100 rounded-lg p-3 bg-gray-50">
                                    {previewQuestions.map((q, idx) => (
                                        <div key={idx} className="group relative bg-white border hover:border-blue-200 rounded-lg p-3 transition-all duration-200 shadow-sm">
                                            <div className="flex justify-between items-center mb-2">
                                                <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
                                                    Q{idx + 1} • {q.difficulty} • {q.category}
                                                </span>
                                                <div className="flex items-center gap-2">
                                                    {editingIdx !== idx && (
                                                        <button
                                                            type="button"
                                                            onClick={() => {
                                                                setEditingIdx(idx);
                                                                setTempEditText(q.text);
                                                            }}
                                                            className="text-[10px] font-bold text-blue-500 hover:text-blue-700 uppercase"
                                                        >
                                                            Edit
                                                        </button>
                                                    )}
                                                    <button
                                                        type="button"
                                                        onClick={() => setPreviewQuestions(prev => prev.filter((_, i) => i !== idx))}
                                                        className="text-gray-300 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100"
                                                        title="Remove question"
                                                    >
                                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                        </svg>
                                                    </button>
                                                </div>
                                            </div>

                                            {editingIdx === idx ? (
                                                <div className="space-y-2">
                                                    <textarea
                                                        autoFocus
                                                        value={tempEditText}
                                                        onChange={(e) => setTempEditText(e.target.value)}
                                                        className="w-full text-sm text-gray-700 bg-white border border-blue-100 rounded p-2 focus:ring-1 focus:ring-blue-500 outline-none resize-none"
                                                        rows={3}
                                                    />
                                                    <div className="flex justify-end gap-2">
                                                        <button
                                                            type="button"
                                                            onClick={() => setEditingIdx(null)}
                                                            className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1"
                                                        >
                                                            Cancel
                                                        </button>
                                                        <button
                                                            type="button"
                                                            onClick={() => {
                                                                setPreviewQuestions(prev => prev.map((item, i) => i === idx ? { ...item, text: tempEditText } : item));
                                                                setEditingIdx(null);
                                                            }}
                                                            className="text-xs bg-blue-500 text-white px-2 py-1 rounded hover:bg-blue-600"
                                                        >
                                                            Save
                                                        </button>
                                                    </div>
                                                </div>
                                            ) : (
                                                <p className="text-sm text-gray-700 font-medium leading-relaxed whitespace-pre-wrap">
                                                    {q.text}
                                                </p>
                                            )}
                                        </div>
                                    ))}

                                    {previewQuestions.length === 0 && (
                                        <div className="text-center py-6 border-2 border-dashed border-gray-100 rounded-lg">
                                            <p className="text-xs text-gray-400">No questions selected.</p>
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

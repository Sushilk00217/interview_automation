'use client';

import { useState, useEffect, useCallback } from 'react';
import { InterviewTemplate, GeneratedQuestion } from '@/types/interview';
import {
    fetchInterviewTemplates,
    scheduleInterview,
    rescheduleInterview,
    generateTemplatePreview,
    applyTemplateToInterview
} from '@/lib/api/interviews';
import { SchedulingApiError } from '@/types/interview';
import QuestionBankSelector from './QuestionBankSelector';

// Dnd Kit Imports
import {
    DndContext,
    closestCenter,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
    DragEndEvent
} from '@dnd-kit/core';
import {
    arrayMove,
    SortableContext,
    sortableKeyboardCoordinates,
    verticalListSortingStrategy,
    useSortable
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical, Trash2, Replace, Edit3, Check, X } from 'lucide-react';

type ModalMode = 'schedule' | 'reschedule';

interface ScheduleInterviewModalProps {
    mode: ModalMode;
    candidateId: string;
    candidateName: string;
    interviewId?: string;
    existingScheduledAt?: string;
    onClose: () => void;
    onSuccess: () => void;
    onAuthError: () => void;
}

// ─── Sortable Item Component ──────────────────────────────────────────────────
interface SortableQuestionItemProps {
    id: string; // for dnd
    index: number;
    question: GeneratedQuestion;
    onRemove: (index: number) => void;
    onReplace: (index: number) => void;
    onUpdateText: (index: number, newText: string) => void;
}

function SortableQuestionItem({ id, index, question, onRemove, onReplace, onUpdateText }: SortableQuestionItemProps) {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging
    } = useSortable({ id: id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        zIndex: isDragging ? 10 : 1,
    };

    const [isEditing, setIsEditing] = useState(false);
    const [editText, setEditText] = useState(question.question_text);

    const handleSave = () => {
        onUpdateText(index, editText);
        setIsEditing(false);
    };

    return (
        <div
            ref={setNodeRef}
            style={style}
            className={`flex items-start gap-3 p-4 bg-white border rounded-xl transition-all ${isDragging ? 'shadow-lg border-blue-400 opacity-60' : 'border-gray-100 hover:border-gray-200 shadow-sm'
                }`}
        >
            <button
                type="button"
                {...attributes}
                {...listeners}
                className="mt-1 cursor-grab active:cursor-grabbing text-gray-400 hover:text-gray-600"
            >
                <GripVertical size={18} />
            </button>

            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1.5 overflow-x-auto pb-1 no-scrollbar">
                    <span className="text-[10px] font-bold bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">Q{index + 1}</span>
                    {question.difficulty && (
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${question.difficulty === 'EASY' ? 'bg-green-100 text-green-700' :
                                question.difficulty === 'MEDIUM' ? 'bg-amber-100 text-amber-700' :
                                    'bg-red-100 text-red-700'
                            }`}>
                            {question.difficulty}
                        </span>
                    )}
                    {question.category && (
                        <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 uppercase whitespace-nowrap">
                            {question.category}
                        </span>
                    )}
                </div>

                {isEditing ? (
                    <div className="space-y-2">
                        <textarea
                            value={editText}
                            onChange={(e) => setEditText(e.target.value)}
                            className="w-full p-2 text-sm border border-blue-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                            rows={3}
                        />
                        <div className="flex gap-2 justify-end">
                            <button onClick={() => setIsEditing(false)} className="p-1 px-3 text-xs bg-gray-100 rounded-md hover:bg-gray-200 transition-colors flex items-center gap-1">
                                <X size={12} /> Cancel
                            </button>
                            <button onClick={handleSave} className="p-1 px-3 text-xs bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors flex items-center gap-1">
                                <Check size={12} /> Save
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="group relative">
                        <p className="text-sm text-gray-800 leading-relaxed pr-8">{question.question_text}</p>
                        <button
                            onClick={() => setIsEditing(true)}
                            className="absolute top-0 right-0 p-1 text-gray-400 hover:text-blue-600 opacity-0 group-hover:opacity-100 transition-all"
                        >
                            <Edit3 size={14} />
                        </button>
                    </div>
                )}
            </div>

            <div className="flex flex-col gap-2">
                <button
                    type="button"
                    onClick={() => onReplace(index)}
                    title="Replace with question bank"
                    className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all"
                >
                    <Replace size={16} />
                </button>
                <button
                    type="button"
                    onClick={() => onRemove(index)}
                    title="Remove question"
                    className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all"
                >
                    <Trash2 size={16} />
                </button>
            </div>
        </div>
    );
}

// ─── Main Modal Component ─────────────────────────────────────────────────────

export default function ScheduleInterviewModal({
    mode,
    candidateId,
    candidateName,
    interviewId,
    existingScheduledAt,
    onClose,
    onSuccess,
    onAuthError,
}: ScheduleInterviewModalProps) {
    const [templates, setTemplates] = useState<InterviewTemplate[]>([]);
    const [templateId, setTemplateId] = useState('');
    const [generatedQuestions, setGeneratedQuestions] = useState<GeneratedQuestion[]>([]);

    const [replacingIndex, setReplacingIndex] = useState<number | null>(null);
    const [isBankOpen, setIsBankOpen] = useState(false);

    const nowLocal = () => {
        const d = new Date();
        d.setSeconds(0, 0);
        const offset = d.getTimezoneOffset() * 60000;
        return new Date(d.getTime() - offset).toISOString().slice(0, 16);
    };

    const [scheduledAt, setScheduledAt] = useState(nowLocal);
    const [loading, setLoading] = useState(false);
    const [templatesLoading, setTemplatesLoading] = useState(false);
    const [questionsLoading, setQuestionsLoading] = useState(false);
    const [error, setError] = useState('');

    const sensors = useSensors(
        useSensor(PointerSensor),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    // ─── Prefill for reschedule ───────────────────────────────────────────────
    useEffect(() => {
        if (mode === 'reschedule' && existingScheduledAt) {
            setScheduledAt(new Date(existingScheduledAt).toISOString().slice(0, 16));
        }
    }, [mode, existingScheduledAt]);

    // ─── Load templates ─────────────────────────────────────────────────────
    useEffect(() => {
        if (mode !== 'schedule') return;
        setTemplatesLoading(true);
        fetchInterviewTemplates()
            .then((data) => {
                const active = data.filter((t) => t.is_active);
                setTemplates(active);
                if (active.length > 0) setTemplateId(active[0].id);
            })
            .catch((err: SchedulingApiError) => {
                if (err.status === 401 || err.status === 403) onAuthError();
                setTemplates([]);
            })
            .finally(() => setTemplatesLoading(false));
    }, [mode, onAuthError]);

    // ─── Fetch Preview Questions ──────────────────────────────────────────────
    useEffect(() => {
        if (!templateId || mode !== 'schedule') return;

        const fetchPreview = async () => {
            setQuestionsLoading(true);
            setError('');
            try {
                const data = await generateTemplatePreview(templateId);
                setGeneratedQuestions(data);
            } catch (err: any) {
                setError(err.detail || 'Failed to generate question preview.');
                setGeneratedQuestions([]);
            } finally {
                setQuestionsLoading(false);
            }
        };

        fetchPreview();
    }, [templateId, mode]);

    // ─── Handlers ─────────────────────────────────────────────────────────────
    const handleDragEnd = (event: DragEndEvent) => {
        const { active, over } = event;
        if (over && active.id !== over.id) {
            setGeneratedQuestions((items) => {
                const oldIndex = items.findIndex((i) => (i.question_id || i.order.toString()) === active.id);
                const newIndex = items.findIndex((i) => (i.question_id || i.order.toString()) === over.id);
                return arrayMove(items, oldIndex, newIndex);
            });
        }
    };

    const removeQuestion = (index: number) => {
        setGeneratedQuestions(prev => prev.filter((_, i) => i !== index));
    };

    const replaceQuestion = (index: number) => {
        setReplacingIndex(index);
        setIsBankOpen(true);
    };

    const handleBankSelect = (newQuestion: GeneratedQuestion) => {
        if (replacingIndex !== null) {
            setGeneratedQuestions(prev => {
                const updated = [...prev];
                updated[replacingIndex] = {
                    ...newQuestion,
                    order: replacingIndex // Maintain order
                };
                return updated;
            });
        }
        setIsBankOpen(false);
        setReplacingIndex(null);
    };

    const updateQuestionText = (index: number, newText: string) => {
        setGeneratedQuestions(prev => {
            const updated = [...prev];
            updated[index].question_text = newText;
            return updated;
        });
    };

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
                // 1. Create Interview
                const interview = await scheduleInterview({
                    candidate_id: candidateId,
                    template_id: templateId,
                    scheduled_at: isoAt
                });

                // 2. Apply Custom Questions (Immutable Snapshot)
                const payload = {
                    questions: generatedQuestions.map((q, idx) => ({
                        question_id: q.question_id,
                        question_text: q.question_text,
                        order: idx,
                        time_limit_sec: q.time_limit_sec || 120
                    }))
                };

                await applyTemplateToInterview(interview.id, payload);

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
            setError(apiErr.detail || 'An unexpected error occurred.');
        } finally {
            setLoading(false);
        }
    };

    const selectedTemplate = templates.find(t => t.id === templateId);

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
                {/* Header */}
                <div className="bg-gradient-to-r from-blue-700 via-blue-600 to-indigo-700 px-8 py-6 shrink-0">
                    <div className="flex justify-between items-start">
                        <div>
                            <h2 className="text-2xl font-bold text-white tracking-tight">
                                {mode === 'schedule' ? 'Schedule Interview' : 'Reschedule Interview'}
                            </h2>
                            <p className="text-blue-100/90 text-sm mt-1">
                                Candidate: <span className="font-semibold text-white">{candidateName}</span>
                            </p>
                        </div>
                        <button
                            onClick={onClose}
                            disabled={loading}
                            className="bg-white/10 hover:bg-white/20 text-white transition-all p-2 rounded-xl"
                        >
                            <X size={20} />
                        </button>
                    </div>
                </div>

                {/* Body */}
                <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-8 space-y-8 bg-gray-50/50 no-scrollbar">
                    {/* Error banner */}
                    {error && (
                        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-100 rounded-xl text-sm text-red-700 animate-in fade-in slide-in-from-top-2">
                            <X className="w-5 h-5 text-red-500 shrink-0" />
                            <span>{error}</span>
                        </div>
                    )}

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Template selector (schedule only) */}
                        {mode === 'schedule' && (
                            <div className="space-y-2">
                                <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 ml-1">
                                    Template Plan
                                    {selectedTemplate && (
                                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${selectedTemplate.is_rule_based ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
                                            }`}>
                                            {selectedTemplate.is_rule_based ? 'Dynamic Rule' : 'Fixed Set'}
                                        </span>
                                    )}
                                </label>
                                {templatesLoading ? (
                                    <div className="h-[46px] flex items-center gap-3 bg-white border border-gray-200 rounded-xl px-4 animate-pulse">
                                        <div className="w-4 h-4 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
                                        <span className="text-sm text-gray-400 font-medium">Loading templates...</span>
                                    </div>
                                ) : (
                                    <select
                                        value={templateId}
                                        onChange={(e) => setTemplateId(e.target.value)}
                                        required
                                        disabled={loading}
                                        className="w-full h-[46px] px-4 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none transition-all cursor-pointer shadow-sm"
                                    >
                                        {templates.length === 0 && <option value="">No active templates</option>}
                                        {templates.map((t) => (
                                            <option key={t.id} value={t.id}>{t.name}</option>
                                        ))}
                                    </select>
                                )}
                            </div>
                        )}

                        {/* Date & Time picker */}
                        <div className="space-y-2">
                            <label className="text-sm font-semibold text-gray-700 ml-1">
                                {mode === 'reschedule' ? 'New ' : ''}Session Time (IST)
                            </label>
                            <input
                                type="datetime-local"
                                value={scheduledAt}
                                onChange={(e) => setScheduledAt(e.target.value)}
                                required
                                disabled={loading}
                                className="w-full h-[46px] px-4 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none transition-all shadow-sm"
                            />
                        </div>
                    </div>

                    {/* Question Customization (Only for schedule mode) */}
                    {mode === 'schedule' && (
                        <div className="space-y-4">
                            <div className="flex justify-between items-center">
                                <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
                                    Planned Questions
                                    <span className="text-xs font-normal bg-gray-200 text-gray-600 px-2.5 py-1 rounded-lg">
                                        {generatedQuestions.length} Questions
                                    </span>
                                </h3>
                                <p className="text-[11px] text-gray-500 italic">Drag to reorder questions</p>
                            </div>

                            {questionsLoading ? (
                                <div className="space-y-3">
                                    {[1, 2, 3].map(i => (
                                        <div key={i} className="h-24 bg-gray-100 rounded-xl animate-pulse" />
                                    ))}
                                </div>
                            ) : generatedQuestions.length > 0 ? (
                                <DndContext
                                    sensors={sensors}
                                    collisionDetection={closestCenter}
                                    onDragEnd={handleDragEnd}
                                >
                                    <SortableContext
                                        items={generatedQuestions.map(q => q.question_id || q.order.toString())}
                                        strategy={verticalListSortingStrategy}
                                    >
                                        <div className="space-y-3">
                                            {generatedQuestions.map((q, idx) => (
                                                <SortableQuestionItem
                                                    key={q.question_id || q.order.toString()}
                                                    id={q.question_id || q.order.toString()}
                                                    index={idx}
                                                    question={q}
                                                    onRemove={removeQuestion}
                                                    onReplace={replaceQuestion}
                                                    onUpdateText={updateQuestionText}
                                                />
                                            ))}
                                        </div>
                                    </SortableContext>
                                </DndContext>
                            ) : !templateId ? (
                                <div className="p-8 border-2 border-dashed border-gray-200 rounded-2xl text-center">
                                    <p className="text-sm text-gray-400">Please select a template to generate questions</p>
                                </div>
                            ) : (
                                <div className="p-8 border-2 border-dashed border-gray-200 rounded-2xl text-center">
                                    <p className="text-sm text-gray-400">No questions found in this template</p>
                                </div>
                            )}
                        </div>
                    )}
                </form>

                {/* Footer Actions */}
                <div className="p-8 bg-white border-t border-gray-100 shrink-0 flex gap-4">
                    <button
                        type="button"
                        onClick={onClose}
                        disabled={loading}
                        className="flex-1 h-12 border border-gray-200 text-gray-600 rounded-xl hover:bg-gray-50 transition-all font-semibold text-sm disabled:opacity-50"
                    >
                        Discard
                    </button>
                    <button
                        type="button"
                        onClick={handleSubmit}
                        disabled={loading || (mode === 'schedule' && !templateId) || (mode === 'schedule' && questionsLoading)}
                        className="flex-[2] h-12 bg-blue-600 text-white rounded-xl hover:bg-blue-700 shadow-xl shadow-blue-500/20 active:scale-[0.98] transition-all font-bold text-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3"
                    >
                        {loading ? (
                            <>
                                <div className="w-5 h-5 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                                <span>{mode === 'schedule' ? 'Applying Plan...' : 'Rescheduling...'}</span>
                            </>
                        ) : (
                            <>
                                <span>{mode === 'schedule' ? 'Finalize & Schedule' : 'Confirm Reschedule'}</span>
                            </>
                        )}
                    </button>
                </div>
            </div>

            {/* Question Bank Modal */}
            {isBankOpen && (
                <QuestionBankSelector
                    onSelect={handleBankSelect}
                    onClose={() => {
                        setIsBankOpen(false);
                        setReplacingIndex(null);
                    }}
                />
            )}
        </div>
    );
}

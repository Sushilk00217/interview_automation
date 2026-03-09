'use client';

import { useState } from 'react';
import { InterviewTemplate } from '@/types/interview';

interface TemplateFormProps {
    initialData?: InterviewTemplate;
    onSubmit: (data: any) => Promise<void>;
    onCancel: () => void;
}

// ─── Section collapse state ───────────────────────────────────────────────────

function SectionHeader({
    title,
    description,
    color,
    isOpen,
    onToggle,
}: {
    title: string;
    description: string;
    color: string;
    isOpen: boolean;
    onToggle: () => void;
}) {
    return (
        <button
            type="button"
            onClick={onToggle}
            className="w-full flex items-center justify-between p-4 rounded-xl bg-white border hover:bg-gray-50 transition-colors text-left"
        >
            <div className="flex items-center gap-3">
                <span className={`w-2.5 h-2.5 rounded-full ${color}`} />
                <div>
                    <p className="text-sm font-bold text-gray-900">{title}</p>
                    <p className="text-xs text-gray-500">{description}</p>
                </div>
            </div>
            <svg
                className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
                fill="none" viewBox="0 0 24 24" stroke="currentColor"
            >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
        </button>
    );
}

// ─── Main Form ────────────────────────────────────────────────────────────────

export default function TemplateForm({ initialData, onSubmit, onCancel }: TemplateFormProps) {
    // Basic fields
    const [title, setTitle] = useState(initialData?.title || '');
    const [roleName, setRoleName] = useState(initialData?.role_name || '');
    const [description, setDescription] = useState(initialData?.description || '');
    const [isActive, setIsActive] = useState(initialData?.is_active ?? true);
    const [isDefaultForRole, setIsDefaultForRole] = useState(initialData?.is_default_for_role ?? false);

    // Section collapse states
    const [techOpen, setTechOpen] = useState(true);
    const [codingOpen, setCodingOpen] = useState(true);
    const [convOpen, setConvOpen] = useState(true);

    // ── Technical config ──
    // Prefer technical_config; fall back to the legacy settings field
    const legacyDist = initialData?.settings?.difficulty_distribution || {};
    const techCfg = initialData?.technical_config || legacyDist;
    const [easyCount, setEasyCount] = useState<number>(techCfg?.easy ?? techCfg?.EASY ?? 0);
    const [mediumCount, setMediumCount] = useState<number>(techCfg?.medium ?? techCfg?.MEDIUM ?? 0);
    const [hardCount, setHardCount] = useState<number>(techCfg?.hard ?? techCfg?.HARD ?? 0);
    const [techDuration, setTechDuration] = useState<number>(techCfg?.duration_minutes ?? 20);
    const [questionSource, setQuestionSource] = useState<string>(techCfg?.question_source || 'ai_generated');

    // ── Coding config ──
    const initCoding = initialData?.coding_config || {};
    const [codingCount, setCodingCount] = useState<number>(initCoding?.count ?? 0);
    const [codingDifficulties, setCodingDifficulties] = useState<string[]>(initCoding?.difficulty ?? []);
    const [codingDuration, setCodingDuration] = useState<number>(initCoding?.duration_minutes ?? 40);

    // ── Conversational config ──
    const initConv = initialData?.conversational_config || {};
    const [convRounds, setConvRounds] = useState<number>(initConv?.rounds ?? 0);
    const [convDuration, setConvDuration] = useState<number>(initConv?.duration_minutes ?? 15);

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const toggleCodingDiff = (d: string) =>
        setCodingDifficulties(prev => prev.includes(d) ? prev.filter(x => x !== d) : [...prev, d]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        // ── Validation ──────────────────────────────────────────────────────────
        if (easyCount < 0 || mediumCount < 0 || hardCount < 0) {
            setError('Technical question counts cannot be negative.');
            return;
        }
        if (codingCount < 0) {
            setError('Coding problem count cannot be negative.');
            return;
        }
        if (convRounds < 0) {
            setError('Conversational rounds cannot be negative.');
            return;
        }
        // If coding section is partially configured, require both fields
        if ((codingCount > 0 && codingDifficulties.length === 0)) {
            setError('Select at least one difficulty level for the Coding section.');
            return;
        }

        setLoading(true);

        // ── technical_config: always flat {easy, medium, hard, duration_minutes} ──
        const technical_config = {
            easy: Number(easyCount),
            medium: Number(mediumCount),
            hard: Number(hardCount),
            duration_minutes: Number(techDuration),
            question_source: questionSource,
        };

        // ── coding_config: null if nothing configured, difficulties lowercased ──
        const coding_config = codingCount > 0 && codingDifficulties.length > 0
            ? {
                count: Number(codingCount),
                difficulty: codingDifficulties.map(d => d.toLowerCase()),
                duration_minutes: Number(codingDuration),
            }
            : null;

        // ── conversational_config: null if no rounds ─────────────────────────────
        const conversational_config = convRounds > 0
            ? {
                rounds: Number(convRounds),
                duration_minutes: Number(convDuration),
            }
            : null;

        // ── Payload: no legacy settings ──────────────────────────────────────────
        const payload: any = {
            title,
            role_name: roleName || null,
            description: description || null,
            is_active: isActive,
            is_default_for_role: isDefaultForRole,
            technical_config,
            coding_config,
            conversational_config,
        };

        try {
            await onSubmit(payload);
        } catch (err: any) {
            setError(err.response?.data?.detail || err.detail || 'Failed to save template');
        } finally {
            setLoading(false);
        }
    };

    const difficultyOptions = ['easy', 'medium', 'hard'];

    return (
        <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
                <div className="p-3 bg-red-50 text-red-700 text-sm rounded-lg border border-red-200">
                    {error}
                </div>
            )}

            {/* ── Basic info ── */}
            <div className="space-y-4">
                <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-1">Title</label>
                    <input
                        type="text" required value={title} onChange={e => setTitle(e.target.value)}
                        className="w-full px-4 py-2 text-gray-900 bg-white rounded-lg border focus:ring-2 focus:ring-blue-500 outline-none"
                    />
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-semibold text-gray-700 mb-1">Target Role</label>
                        <input
                            type="text" value={roleName} onChange={e => setRoleName(e.target.value)}
                            placeholder="e.g. Software Engineer"
                            className="w-full px-4 py-2 text-gray-900 bg-white rounded-lg border focus:ring-2 focus:ring-blue-500 outline-none"
                        />
                    </div>
                    <div className="flex items-center space-x-4 pt-6">
                        <label className="flex items-center cursor-pointer">
                            <input type="checkbox" checked={isActive} onChange={e => setIsActive(e.target.checked)} className="rounded text-blue-600" />
                            <span className="ml-2 text-sm text-gray-700">Active</span>
                        </label>
                        <label className="flex items-center cursor-pointer">
                            <input type="checkbox" checked={isDefaultForRole} onChange={e => setIsDefaultForRole(e.target.checked)} className="rounded text-blue-600" />
                            <span className="ml-2 text-sm text-gray-700">Default for Role</span>
                        </label>
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-1">Description</label>
                    <textarea
                        value={description} onChange={e => setDescription(e.target.value)}
                        className="w-full px-4 py-2 text-gray-900 bg-white rounded-lg border focus:ring-2 focus:ring-blue-500 outline-none h-20 resize-none"
                    />
                </div>

            </div>

            {/* ═══════════════════════════════════════════════════════════ */}
            {/* INTERVIEW SECTIONS                                          */}
            {/* ═══════════════════════════════════════════════════════════ */}
            <div className="space-y-3">
                <p className="text-xs font-bold uppercase tracking-widest text-gray-400">Interview Sections</p>

                {/* ── TECHNICAL SECTION ── */}
                <div className="rounded-xl border overflow-hidden">
                    <SectionHeader
                        title="Technical Section"
                        description="Knowledge-based Q&A questions"
                        color="bg-blue-500"
                        isOpen={techOpen}
                        onToggle={() => setTechOpen(o => !o)}
                    />
                    {techOpen && (
                        <div className="p-4 bg-gray-50 border-t space-y-3">
                            <div className="flex items-center gap-4 mb-4">
                                <label className="text-xs font-bold text-gray-500 uppercase">Question Source:</label>
                                <div className="flex bg-gray-200 p-1 rounded-lg">
                                    <button
                                        type="button"
                                        onClick={() => setQuestionSource('ai_generated')}
                                        className={`px-3 py-1.5 text-[10px] font-bold rounded-md transition-all ${questionSource === 'ai_generated' ? 'bg-white shadow text-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
                                    >
                                        AI GENERATED
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => setQuestionSource('question_bank')}
                                        className={`px-3 py-1.5 text-[10px] font-bold rounded-md transition-all ${questionSource === 'question_bank' ? 'bg-white shadow text-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
                                    >
                                        QUESTION BANK
                                    </button>
                                </div>
                            </div>
                            <p className="text-xs text-gray-500">
                                Set how many questions to pull per difficulty level.
                            </p>
                            <div className="grid grid-cols-4 gap-3">
                                {([['Easy', easyCount, setEasyCount], ['Medium', mediumCount, setMediumCount], ['Hard', hardCount, setHardCount]] as [string, number, (v: number) => void][]).map(([label, val, setter]) => (
                                    <div key={label}>
                                        <label className="block text-xs font-bold text-gray-500 uppercase mb-1">{label}</label>
                                        <input
                                            type="number" min={0} value={val}
                                            onChange={e => setter(Number(e.target.value))}
                                            className="w-full px-3 py-2 text-gray-900 bg-white rounded-lg border text-sm"
                                        />
                                    </div>
                                ))}
                                <div>
                                    <label className="block text-xs font-bold text-gray-500 uppercase mb-1 text-blue-600">Duration (min)</label>
                                    <input
                                        type="number" min={1} value={techDuration}
                                        onChange={e => setTechDuration(Number(e.target.value))}
                                        className="w-full px-3 py-2 text-gray-900 bg-white rounded-lg border border-blue-200 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
                                    />
                                </div>
                            </div>
                            <p className="text-xs text-gray-400">
                                Config: {JSON.stringify({ easy: Number(easyCount), medium: Number(mediumCount), hard: Number(hardCount) })}
                            </p>
                        </div>
                    )}
                </div>

                {/* ── CODING SECTION ── */}
                <div className="rounded-xl border overflow-hidden">
                    <SectionHeader
                        title="Coding Section"
                        description="Algorithm and coding challenges"
                        color="bg-purple-500"
                        isOpen={codingOpen}
                        onToggle={() => setCodingOpen(o => !o)}
                    />
                    {codingOpen && (
                        <div className="p-4 bg-gray-50 border-t space-y-4">
                            <div className="flex gap-4">
                                <div>
                                    <label className="block text-xs font-bold text-gray-500 uppercase mb-1">
                                        Number of Problems
                                    </label>
                                    <input
                                        type="number" min={0} value={codingCount}
                                        onChange={e => setCodingCount(Number(e.target.value))}
                                        placeholder="0"
                                        className="w-32 px-3 py-2 text-gray-900 bg-white rounded-lg border text-sm"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-gray-500 uppercase mb-1 text-purple-600">
                                        Duration (min)
                                    </label>
                                    <input
                                        type="number" min={1} value={codingDuration}
                                        onChange={e => setCodingDuration(Number(e.target.value))}
                                        className="w-32 px-3 py-2 text-gray-900 bg-white rounded-lg border border-purple-200 text-sm focus:ring-1 focus:ring-purple-500 outline-none"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase mb-2">
                                    Difficulty Filter
                                </label>
                                <div className="flex gap-2">
                                    {difficultyOptions.map(d => {
                                        const active = codingDifficulties.includes(d);
                                        const colors: Record<string, string> = {
                                            easy: active ? 'bg-green-50 border-green-400 text-green-700' : 'bg-white text-gray-500',
                                            medium: active ? 'bg-amber-50 border-amber-400 text-amber-700' : 'bg-white text-gray-500',
                                            hard: active ? 'bg-red-50 border-red-400 text-red-700' : 'bg-white text-gray-500',
                                        };
                                        return (
                                            <button
                                                key={d} type="button"
                                                onClick={() => toggleCodingDiff(d)}
                                                className={`px-4 py-2 text-xs font-bold rounded-lg border transition-all capitalize ${colors[d]}`}
                                            >
                                                {d}
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>
                            <p className="text-xs text-gray-400">
                                Config: {JSON.stringify({ count: Number(codingCount), difficulty: codingDifficulties })}
                            </p>
                        </div>
                    )}
                </div>

                {/* ── CONVERSATIONAL SECTION ── */}
                <div className="rounded-xl border overflow-hidden">
                    <SectionHeader
                        title="Conversational Section"
                        description="LLM-powered behavioral and experience questions"
                        color="bg-emerald-500"
                        isOpen={convOpen}
                        onToggle={() => setConvOpen(o => !o)}
                    />
                    {convOpen && (
                        <div className="p-4 bg-gray-50 border-t space-y-3">
                            <p className="text-xs text-gray-500">
                                Conversational questions are generated live by Ai during the interview.
                                Set how many rounds the session should include.
                            </p>
                            <div className="flex gap-4">
                                <div>
                                    <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Number of Rounds</label>
                                    <input
                                        type="number" min={0} value={convRounds}
                                        onChange={e => setConvRounds(Number(e.target.value))}
                                        placeholder="0"
                                        className="w-32 px-3 py-2 text-gray-900 bg-white rounded-lg border text-sm"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-gray-500 uppercase mb-1 text-emerald-600">Duration (min)</label>
                                    <input
                                        type="number" min={1} value={convDuration}
                                        onChange={e => setConvDuration(Number(e.target.value))}
                                        className="w-32 px-3 py-2 text-gray-900 bg-white rounded-lg border border-emerald-200 text-sm focus:ring-1 focus:ring-emerald-500 outline-none"
                                    />
                                </div>
                            </div>
                            <p className="text-xs text-gray-400">
                                Config: {JSON.stringify({ rounds: Number(convRounds) })}
                            </p>
                        </div>
                    )}
                </div>
            </div>

            {/* ── Actions ── */}
            <div className="flex space-x-3 pt-4 border-t">
                <button
                    type="button" onClick={onCancel}
                    className="flex-1 px-4 py-2 border rounded-xl hover:bg-gray-50 text-sm font-semibold transition-colors"
                >
                    Cancel
                </button>
                <button
                    type="submit" disabled={loading}
                    className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 text-sm font-bold shadow-lg shadow-blue-200 transition-all active:scale-95 disabled:opacity-50"
                >
                    {loading ? 'Saving...' : initialData ? 'Update Template' : 'Create Template'}
                </button>
            </div>
        </form>
    );
}

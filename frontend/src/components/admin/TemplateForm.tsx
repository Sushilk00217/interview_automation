'use client';

import { useState } from 'react';
import { InterviewTemplateCreate, InterviewTemplateUpdate, InterviewTemplate } from '@/types/interview';

interface TemplateFormProps {
    initialData?: InterviewTemplate;
    onSubmit: (data: any) => Promise<void>;
    onCancel: () => void;
}

export default function TemplateForm({ initialData, onSubmit, onCancel }: TemplateFormProps) {
    const [title, setTitle] = useState(initialData?.title || '');
    const [roleName, setRoleName] = useState(initialData?.role_name || '');
    const [description, setDescription] = useState(initialData?.description || '');
    const [isRuleBased, setIsRuleBased] = useState(initialData?.is_rule_based ?? false);
    const [isActive, setIsActive] = useState(initialData?.is_active ?? true);
    const [isDefaultForRole, setIsDefaultForRole] = useState(initialData?.is_default_for_role ?? false);

    // Settings for rule-based
    const [easyCount, setEasyCount] = useState(initialData?.settings?.difficulty_distribution?.EASY || 0);
    const [mediumCount, setMediumCount] = useState(initialData?.settings?.difficulty_distribution?.MEDIUM || 0);
    const [hardCount, setHardCount] = useState(initialData?.settings?.difficulty_distribution?.HARD || 0);
    const [categoryFilters, setCategoryFilters] = useState<string[]>(initialData?.settings?.category_filters || []);

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        const payload: any = {
            title,
            role_name: roleName || null,
            description: description || null,
            is_rule_based: isRuleBased,
            is_active: isActive,
            is_default_for_role: isDefaultForRole,
            settings: isRuleBased ? {
                difficulty_distribution: {
                    EASY: Number(easyCount),
                    MEDIUM: Number(mediumCount),
                    HARD: Number(hardCount)
                },
                category_filters: categoryFilters
            } : initialData?.settings || {}
        };

        try {
            await onSubmit(payload);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to save template');
        } finally {
            setLoading(false);
        }
    };

    const categories = ["PYTHON", "SQL", "MACHINE_LEARNING", "DATA_STRUCTURES", "SYSTEM_DESIGN", "STATISTICS"];

    return (
        <form onSubmit={handleSubmit} className="space-y-6">
            {error && <div className="p-3 bg-red-50 text-red-700 text-sm rounded-lg border border-red-200">{error}</div>}

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
                        className="w-full px-4 py-2 text-gray-900 bg-white rounded-lg border focus:ring-2 focus:ring-blue-500 outline-none h-24 resize-none"
                    />
                </div>

                <div className="p-4 bg-gray-50 rounded-xl border border-gray-100 space-y-4">
                    <div className="flex items-center justify-between">
                        <h3 className="text-sm font-bold text-gray-900">Logic Type</h3>
                        <div className="flex bg-white p-1 rounded-lg border">
                            <button
                                type="button" onClick={() => setIsRuleBased(false)}
                                className={`px-4 py-1.5 text-xs font-semibold rounded-md transition-all ${!isRuleBased ? 'bg-blue-600 text-white shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                            >
                                Fixed
                            </button>
                            <button
                                type="button" onClick={() => setIsRuleBased(true)}
                                className={`px-4 py-1.5 text-xs font-semibold rounded-md transition-all ${isRuleBased ? 'bg-blue-600 text-white shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                            >
                                Rule-Based
                            </button>
                        </div>
                    </div>

                    {isRuleBased ? (
                        <div className="space-y-4 animate-in fade-in slide-in-from-top-2 duration-300">
                            <div className="grid grid-cols-3 gap-4">
                                <div>
                                    <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Easy</label>
                                    <input type="number" value={easyCount} onChange={e => setEasyCount(Number(e.target.value))} className="w-full px-3 py-2 text-gray-900 bg-white rounded-lg border" />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Medium</label>
                                    <input type="number" value={mediumCount} onChange={e => setMediumCount(Number(e.target.value))} className="w-full px-3 py-2 text-gray-900 bg-white rounded-lg border" />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Hard</label>
                                    <input type="number" value={hardCount} onChange={e => setHardCount(Number(e.target.value))} className="w-full px-3 py-2 text-gray-900 bg-white rounded-lg border" />
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase mb-2">Categories</label>
                                <div className="grid grid-cols-2 gap-2">
                                    {categories.map(cat => (
                                        <button
                                            key={cat} type="button"
                                            onClick={() => setCategoryFilters(prev => prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat])}
                                            className={`px-3 py-2 text-xs text-left rounded-lg border transition-all ${categoryFilters.includes(cat) ? 'bg-blue-50 border-blue-200 text-blue-700 font-semibold' : 'bg-white hover:bg-gray-50'}`}
                                        >
                                            {cat}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="text-center py-4">
                            <p className="text-sm text-gray-500">Fixed templates use a pre-defined set of questions.</p>
                            {/* Question picker could be added here later */}
                        </div>
                    )}
                </div>
            </div>

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
                    {loading ? 'Saving...' : 'Save Template'}
                </button>
            </div>
        </form>
    );
}

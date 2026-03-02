'use client';

import { useState, useEffect } from 'react';
import { getTemplates, toggleTemplateActive, deleteTemplate, createTemplate, updateTemplate } from '@/lib/api/templates';
import { InterviewTemplate } from '@/types/interview';
import TemplateForm from '@/components/admin/TemplateForm';
import Link from 'next/link';

export default function TemplatesPage() {
    const [templates, setTemplates] = useState<InterviewTemplate[]>([]);
    const [loading, setLoading] = useState(true);
    const [modal, setModal] = useState<{ open: boolean; data?: InterviewTemplate }>({ open: false });

    const loadTemplates = async () => {
        setLoading(true);
        try {
            const data = await getTemplates();
            setTemplates(data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadTemplates();
    }, []);

    const handleToggle = async (id: string, current: boolean) => {
        try {
            await toggleTemplateActive(id, !current);
            setTemplates(prev => prev.map(t => t.id === id ? { ...t, is_active: !current } : t));
        } catch (err) {
            alert('Failed to update status');
        }
    };

    const handleDelete = async (id: string) => {
        if (!confirm('Are you sure? This will soft-delete the template.')) return;
        try {
            await deleteTemplate(id);
            setTemplates(prev => prev.map(t => t.id === id ? { ...t, is_active: false } : t));
        } catch (err) {
            alert('Delete failed');
        }
    };

    const handleFormSubmit = async (payload: any) => {
        if (modal.data) {
            await updateTemplate(modal.data.id, payload);
        } else {
            await createTemplate(payload);
        }
        setModal({ open: false });
        loadTemplates();
    };

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
            <div className="flex justify-between items-end">
                <div>
                    <Link href="/admin" className="inline-flex items-center text-sm font-medium text-gray-500 hover:text-gray-900 hover:underline mb-2 transition-colors">
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
                        Back to Dashboard
                    </Link>
                    <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">Interview Templates</h1>
                    <p className="text-gray-500 text-sm mt-1">Manage role-specific and rule-based scheduling configurations.</p>
                </div>
                <button
                    onClick={() => setModal({ open: true })}
                    className="bg-blue-600 text-white px-6 py-2.5 rounded-xl font-bold shadow-lg shadow-blue-200 hover:bg-blue-700 transition-all active:scale-95 flex items-center space-x-2"
                >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                    <span>Create Template</span>
                </button>
            </div>

            <div className="bg-white rounded-2xl border shadow-sm overflow-hidden">
                <table className="w-full text-left border-collapse">
                    <thead className="bg-gray-50 border-b">
                        <tr>
                            <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Template</th>
                            <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Role</th>
                            <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Type</th>
                            <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Default</th>
                            <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Status</th>
                            <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                        {loading ? (
                            <tr><td colSpan={6} className="px-6 py-12 text-center text-gray-400 italic">Loading templates...</td></tr>
                        ) : templates.length === 0 ? (
                            <tr><td colSpan={6} className="px-6 py-12 text-center text-gray-400 italic">No templates found.</td></tr>
                        ) : templates.map(t => (
                            <tr key={t.id} className="hover:bg-gray-50/50 transition-colors group">
                                <td className="px-6 py-4">
                                    <div className="font-bold text-gray-900">{t.title}</div>
                                    <div className="text-xs text-gray-400 line-clamp-1">{t.description || 'No description'}</div>
                                </td>
                                <td className="px-6 py-4">
                                    <span className="text-sm text-gray-600 bg-gray-100 px-2 py-1 rounded-md font-medium">
                                        {t.role_name || 'Generic'}
                                    </span>
                                </td>
                                <td className="px-6 py-4">
                                    <span className={`text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded-full ${t.is_rule_based ? 'bg-purple-50 text-purple-600 border border-purple-100' : 'bg-blue-50 text-blue-600 border border-blue-100'}`}>
                                        {t.is_rule_based ? 'Rule-Based' : 'Fixed'}
                                    </span>
                                </td>
                                <td className="px-6 py-4 text-center">
                                    {t.is_default_for_role && (
                                        <div className="inline-flex items-center justify-center text-amber-600 bg-amber-50 px-2 py-1 rounded-md text-[10px] font-bold uppercase border border-amber-100">
                                            Default
                                        </div>
                                    )}
                                </td>
                                <td className="px-6 py-4 text-center">
                                    <button
                                        onClick={() => handleToggle(t.id, t.is_active)}
                                        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none ${t.is_active ? 'bg-green-500' : 'bg-gray-200'}`}
                                    >
                                        <span className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${t.is_active ? 'translate-x-5' : 'translate-x-1'}`} />
                                    </button>
                                </td>
                                <td className="px-6 py-4 text-right space-x-2">
                                    <button
                                        onClick={() => setModal({ open: true, data: t })}
                                        className="text-gray-400 hover:text-blue-600 transition-colors"
                                    >
                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
                                    </button>
                                    <button
                                        onClick={() => handleDelete(t.id)}
                                        className="text-gray-300 hover:text-red-500 transition-colors"
                                    >
                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {modal.open && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
                    <div className="bg-white rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
                        <div className="bg-gray-50 px-6 py-4 border-b flex justify-between items-center">
                            <h2 className="text-lg font-bold text-gray-900">{modal.data ? 'Edit Template' : 'New Template'}</h2>
                            <button onClick={() => setModal({ open: false })} className="text-gray-400 hover:text-gray-600 transition-colors">
                                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                            </button>
                        </div>
                        <div className="p-6">
                            <TemplateForm
                                initialData={modal.data}
                                onSubmit={handleFormSubmit}
                                onCancel={() => setModal({ open: false })}
                            />
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

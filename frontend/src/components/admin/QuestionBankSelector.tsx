'use client';

import { useState, useEffect } from 'react';
import { GeneratedQuestion } from '@/types/interview';

interface QuestionBankSelectorProps {
    onSelect: (question: GeneratedQuestion) => void;
    onClose: () => void;
}

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

function getToken(): string | null {
    if (typeof window === 'undefined') return null;
    try {
        const raw = localStorage.getItem('auth-storage');
        if (!raw) return null;
        return JSON.parse(raw)?.state?.token ?? null;
    } catch {
        return null;
    }
}

export default function QuestionBankSelector({ onSelect, onClose }: QuestionBankSelectorProps) {
    const [questions, setQuestions] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');

    useEffect(() => {
        const token = getToken();
        fetch(`${BASE_URL}/api/v1/admin/questions`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        })
            .then(res => res.json())
            .then(data => {
                setQuestions(data);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, []);

    const filtered = questions.filter(q =>
        q.text.toLowerCase().includes(search.toLowerCase()) ||
        q.category.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-[60]">
            <div className="bg-white rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[80vh]">
                <div className="p-6 border-b border-gray-100 flex justify-between items-center">
                    <div>
                        <h3 className="text-xl font-bold text-gray-900">Question Bank</h3>
                        <p className="text-sm text-gray-500">Select a question to replace the current one</p>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-500">
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <div className="p-4 bg-gray-50 border-b border-gray-100">
                    <div className="relative">
                        <input
                            type="text"
                            placeholder="Search by question text or category..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 bg-white border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 outline-none transition-all"
                        />
                        <svg className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-12 text-gray-400">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mb-4"></div>
                            <p>Loading questions...</p>
                        </div>
                    ) : filtered.length === 0 ? (
                        <div className="text-center py-12 text-gray-500">
                            No questions found matching your search.
                        </div>
                    ) : (
                        filtered.map(q => (
                            <div
                                key={q.id}
                                onClick={() => onSelect({
                                    question_id: q.id,
                                    question_text: q.text,
                                    category: q.category,
                                    difficulty: q.difficulty,
                                    order: 0,
                                    time_limit_sec: 120
                                })}
                                className="group p-4 border border-gray-100 rounded-xl hover:border-blue-200 hover:bg-blue-50/30 cursor-pointer transition-all flex justify-between items-center"
                            >
                                <div className="flex-1 pr-4">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${q.difficulty === 'EASY' ? 'bg-green-100 text-green-700' :
                                                q.difficulty === 'MEDIUM' ? 'bg-amber-100 text-amber-700' :
                                                    'bg-red-100 text-red-700'
                                            }`}>
                                            {q.difficulty}
                                        </span>
                                        <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 uppercase">
                                            {q.category}
                                        </span>
                                    </div>
                                    <p className="text-sm text-gray-900 line-clamp-2">{q.text}</p>
                                </div>
                                <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                                    <span className="text-blue-600 font-medium text-sm flex items-center gap-1">
                                        Select
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                                        </svg>
                                    </span>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}

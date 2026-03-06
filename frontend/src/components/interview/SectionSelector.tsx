"use client";

import { useInterviewStore } from "@/store/interviewStore";
import { useEffect } from "react";
import { interviewService } from "@/lib/interviewService";

export default function SectionSelector() {
    const sections = useInterviewStore(s => s.sections);
    const startSection = useInterviewStore(s => s.startSection);
    const error = useInterviewStore(s => s.error);

    // If sections wasn't fetched yet for some reason, fetch them.
    useEffect(() => {
        if (sections.length === 0) {
            interviewService.getSections().then(sect => {
                useInterviewStore.setState({ sections: sect });
            }).catch(e => console.error(e));
        }
    }, [sections.length]);

    // Format status for display
    const formatStatus = (status: string) => {
        return status.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    };

    return (
        <div className="flex flex-col items-center justify-center min-h-screen p-6">
            <div className="w-full max-w-3xl glass-card rounded-2xl p-8 animate-fadeIn">
                <div className="mb-10 text-center">
                    <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">Interview Sections</h1>
                    <p className="text-gray-600 text-sm mt-2 font-medium">Please complete all the sections below to finalize your assessment.</p>
                </div>

                {error && (
                    <div className="mb-8 bg-red-50/80 backdrop-blur-sm text-red-700 border border-red-200 p-4 rounded-xl text-sm font-semibold flex items-center gap-3">
                        <svg className="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd"></path></svg>
                        {error}
                    </div>
                )}

                <div className="grid gap-6">
                    {sections.map(section => {
                        const progress = section.total_questions > 0
                            ? (section.completed_questions / section.total_questions) * 100
                            : 0;

                        const statusColors: Record<string, string> = {
                            completed: "bg-emerald-100 text-emerald-700 border-emerald-200",
                            in_progress: "bg-amber-100 text-amber-700 border-amber-200",
                            pending: "bg-slate-100 text-slate-500 border-slate-200"
                        };

                        const iconColors: Record<string, string> = {
                            technical: "text-blue-500",
                            coding: "text-purple-500",
                            conversational: "text-emerald-500"
                        };

                        return (
                            <div
                                key={section.id}
                                className="group relative bg-white/40 backdrop-blur-md border border-white/50 rounded-2xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-6 transition-all duration-300 hover:shadow-xl hover:scale-[1.02] hover:border-blue-300/50"
                            >
                                <div className="flex-1 space-y-4">
                                    <div className="flex items-center gap-4">
                                        <div className={`p-3 rounded-xl bg-white/80 shadow-sm ${iconColors[section.section_type] || 'text-gray-500'}`}>
                                            {section.section_type === 'technical' && <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.584.584a2 2 0 00-.584 1.414v.7a1 1 0 01-1 1h-2a1 1 0 01-1-1v-.7a2 2 0 00-.584-1.414l-.584-.584z"></path></svg>}
                                            {section.section_type === 'coding' && <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path></svg>}
                                            {section.section_type === 'conversational' && <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"></path></svg>}
                                        </div>
                                        <div>
                                            <h3 className="text-xl font-bold text-gray-900 capitalize">
                                                {section.section_type} Section
                                            </h3>
                                            <div className="flex items-center gap-3 mt-1">
                                                <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase border ${statusColors[section.status]}`}>
                                                    {formatStatus(section.status)}
                                                </span>
                                                <span className="text-xs text-gray-500 font-medium flex items-center gap-1">
                                                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                                                    {section.duration_minutes}m
                                                </span>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <div className="flex justify-between text-xs font-bold text-gray-500 uppercase tracking-tight">
                                            <span>Progress</span>
                                            <span>{section.completed_questions}/{section.total_questions} Questions</span>
                                        </div>
                                        <div className="h-2 w-full bg-gray-200/50 rounded-full overflow-hidden">
                                            <div
                                                className={`h-full transition-all duration-500 ease-out rounded-full ${section.status === 'completed' ? 'bg-emerald-500' : 'bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.5)]'}`}
                                                style={{ width: `${progress}%` }}
                                            />
                                        </div>
                                    </div>
                                </div>

                                <div className="flex-shrink-0">
                                    {section.status === "completed" ? (
                                        <div className="flex items-center justify-center w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 border border-emerald-200">
                                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7"></path></svg>
                                        </div>
                                    ) : (
                                        <button
                                            onClick={() => startSection(section.section_type)}
                                            className={`relative overflow-hidden group/btn px-8 py-3 rounded-xl font-bold text-sm uppercase transition-all duration-300 shadow-lg active:scale-95 ${section.status === "in_progress"
                                                    ? "bg-blue-600 text-white hover:bg-blue-700 shadow-blue-200"
                                                    : "bg-white text-blue-600 border border-blue-200 hover:border-blue-400 hover:bg-blue-50 shadow-gray-100"
                                                }`}
                                        >
                                            <span className="relative z-10">{section.status === "in_progress" ? "Resume" : "Start Section"}</span>
                                        </button>
                                    )}
                                </div>
                            </div>
                        );
                    })}

                    {sections.length === 0 && (
                        <div className="text-center py-16 bg-white/30 backdrop-blur-sm rounded-2xl border border-dashed border-gray-300">
                            <div className="bg-gray-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                                <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0a2 2 0 01-2 2H6a2 2 0 01-2-2m16 0l-1.586-1.586a2 2 0 00-2.828 0L12 14l-2.586-2.586a2 2 0 00-2.828 0L5 13"></path></svg>
                            </div>
                            <p className="text-gray-500 font-medium italic">No sections available for this interview.</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

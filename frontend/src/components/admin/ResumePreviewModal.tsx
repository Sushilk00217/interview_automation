import { useState } from 'react';
import { CandidateResponse } from '@/types/api';
import { useAuthStore } from '@/store/authStore';

interface ResumePreviewModalProps {
    candidate: CandidateResponse;
    onClose: () => void;
}

function MatchScoreBadge({ score }: { score?: number | null }) {
    if (score == null) return null;
    const style = score >= 85 ? 'bg-green-100 text-green-800' :
        score >= 70 ? 'bg-yellow-100 text-yellow-800' :
            'bg-red-100 text-red-800';
    return (
        <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${style}`}>
            {score.toFixed(1)}
        </span>
    );
}

export default function ResumePreviewModal({ candidate, onClose }: ResumePreviewModalProps) {
    const { token } = useAuthStore();
    const resume = candidate.resume_json || {};
    const jd = candidate.jd_json || {};
    const [showFullOriginal, setShowFullOriginal] = useState(false);
    const [originalBlobUrl, setOriginalBlobUrl] = useState<string | null>(null);

    const handleViewOriginal = () => {
        if (originalBlobUrl) {
            setShowFullOriginal(!showFullOriginal);
            return;
        }

        const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
        const url = `${baseUrl}/api/v1/auth/admin/candidates/${candidate.id}/resume-file`;

        fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
        })
            .then(res => {
                if (!res.ok) throw new Error('Failed to fetch resume file');
                return res.blob();
            })
            .then(blob => {
                const blobUrl = window.URL.createObjectURL(blob);
                setOriginalBlobUrl(blobUrl);
                setShowFullOriginal(true);
            })
            .catch(err => {
                console.error(err);
                alert('Failed to load original resume file.');
            });
    };

    const skills = Array.isArray(resume.skills) ? resume.skills : [];
    const experience = resume.experience_years ?? 'N/A';
    const summary = resume.summary || 'No summary available.';
    const education = Array.isArray(resume.education) ? resume.education : [];
    const jdSkills = Array.isArray(jd.required_skills) ? jd.required_skills : [];

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className={`bg-white rounded-2xl shadow-2xl w-full ${showFullOriginal ? 'max-w-7xl' : 'max-w-2xl'} max-h-[90vh] overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-200 transition-all`}>
                {/* Header */}
                <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                    <div className="flex items-center gap-4">
                        <div>
                            <h2 className="text-xl font-bold text-gray-900">Resume Preview</h2>
                            <p className="text-sm text-gray-700 mt-0.5">{candidate.username} • {candidate.email}</p>
                        </div>
                        {candidate.match_score != null && (
                            <div className="flex flex-col items-center border-l border-gray-100 pl-4">
                                <span className="text-[10px] font-bold text-gray-500 uppercase tracking-tighter">Match Score</span>
                                <MatchScoreBadge score={candidate.match_score} />
                            </div>
                        )}
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-all"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 space-y-8">
                    {/* Summary Section */}
                    <section>
                        <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-3">Professional Summary</h3>
                        <div className="bg-blue-50/50 border border-blue-100/50 p-4 rounded-xl text-gray-700 leading-relaxed italic">
                            "{summary}"
                        </div>
                    </section>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        {/* Skills & Experience */}
                        <div className="space-y-6">
                            <section>
                                <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>
                                    Key Skills
                                </h3>
                                <div className="flex flex-wrap gap-2">
                                    {skills.length > 0 ? skills.map((s: string, i: number) => (
                                        <span key={i} className="px-3 py-1 bg-white border border-gray-200 text-gray-700 rounded-lg text-sm font-medium shadow-sm hover:border-blue-300 transition-colors">
                                            {s}
                                        </span>
                                    )) : <span className="text-gray-600 text-sm italic">No skills extracted.</span>}
                                </div>
                            </section>

                            <section>
                                <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-3 flex items-center gap-2">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                                    Experience
                                </h3>
                                <div className="flex items-baseline gap-2">
                                    <span className="text-3xl font-bold text-blue-600">{experience}</span>
                                    <span className="text-gray-700 font-medium">Years of Experience</span>
                                </div>
                            </section>
                        </div>

                        {/* Education & JD Match */}
                        <div className="space-y-6">
                            <section>
                                <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-3 flex items-center gap-2">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.582.477 5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path></svg>
                                    Education
                                </h3>
                                <div className="space-y-3">
                                    {education.length > 0 ? education.map((edu: any, i: number) => (
                                        <div key={i} className="border-l-2 border-gray-100 pl-4 py-1">
                                            <p className="text-sm font-bold text-gray-900">{edu.degree || 'Degree Unknown'}</p>
                                            <p className="text-xs text-gray-600">{edu.institution || 'Institution Unknown'} • {edu.year || 'N/A'}</p>
                                        </div>
                                    )) : <span className="text-gray-600 text-sm italic">No education history found.</span>}
                                </div>
                            </section>

                            <section>
                                <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-3 flex items-center gap-2">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
                                    JD Required Skills
                                </h3>
                                <div className="flex flex-wrap gap-2">
                                    {jdSkills.length > 0 ? jdSkills.map((s: string, i: number) => (
                                        <span key={i} className="px-3 py-1 bg-amber-50 border border-amber-100 text-amber-700 rounded-lg text-xs font-semibold">
                                            {s}
                                        </span>
                                    )) : <span className="text-gray-600 text-sm italic">No required skills defined.</span>}
                                </div>
                            </section>
                        </div>
                    </div>

                    {showFullOriginal && originalBlobUrl && (
                        <div className="mt-8 border-t border-gray-100 pt-8 animate-in slide-in-from-bottom-4 duration-300">
                            <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-4 flex items-center gap-2">
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                                Original Document
                            </h3>
                            <div className="w-full h-[600px] bg-gray-100 rounded-xl overflow-hidden border border-gray-200">
                                <iframe
                                    src={`${originalBlobUrl}#toolbar=0&navpanes=0`}
                                    className="w-full h-full"
                                    title="Original Resume PDF"
                                />
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-gray-100 flex justify-between bg-gray-50/50">
                    <button
                        onClick={handleViewOriginal}
                        className="px-6 py-2 border border-blue-600 text-blue-600 rounded-xl text-sm font-bold hover:bg-blue-50 transition-all shadow-sm flex items-center gap-2"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m.75 12l3 3m0 0l3-3m-3 3v-6m-1.5-9H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                        </svg>
                        {showFullOriginal ? 'Hide Original Document' : 'View Original Document'}
                    </button>
                    <button
                        onClick={onClose}
                        className="px-6 py-2 bg-gray-900 text-white rounded-xl text-sm font-bold hover:bg-gray-800 transition-all shadow-md active:scale-[0.98]"
                    >
                        Close Preview
                    </button>
                </div>
            </div>
        </div>
    );
}

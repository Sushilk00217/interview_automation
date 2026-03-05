import React from "react"
import Editor from "@monaco-editor/react"
import { useCodingStore } from "@/store/codingStore"
import { useInterviewStore } from "@/store/interviewStore"

export default function CodeEditorPanel() {
    const {
        language,
        code,
        setCode,
        setLanguage,
        problem,
        isSubmitted,
        isSubmitting,
        isRunning,
        runCurrentCode,
        submitCurrentCode
    } = useCodingStore()

    const interviewId = useInterviewStore(s => s.interviewId)
    // We don't have a direct candidateId in interviewStore, but we can get it from auth if needed, 
    // or the backend can infer it from the interview session.
    // For now, let's just pass interviewId.

    const handleEditorChange = (value: string | undefined) => {
        setCode(value || "")
    }

    const handleLanguageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        setLanguage(e.target.value)
    }

    const supportedLanguages = [
        { label: "Python3", value: "python3", monaco: "python" },
        { label: "JavaScript", value: "javascript", monaco: "javascript" },
        { label: "Java", value: "java", monaco: "java" },
        { label: "C++", value: "cpp", monaco: "cpp" }
    ]

    const currentMonacoLang = supportedLanguages.find(l => l.value === language)?.monaco || "python"

    return (
        <div className="flex flex-col h-full bg-white rounded-lg border border-gray-200 overflow-hidden shadow-sm">
            <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
                <div className="flex items-center gap-4">
                    <select
                        value={language}
                        onChange={handleLanguageChange}
                        disabled={isSubmitted || isSubmitting || isRunning}
                        className="bg-white border border-gray-200 rounded px-2 py-1 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:bg-gray-100 disabled:cursor-not-allowed transition-all"
                    >
                        {supportedLanguages.map(l => (
                            <option key={l.value} value={l.value}>
                                {l.label}
                            </option>
                        ))}
                    </select>
                </div>

                <div className="flex items-center gap-2">
                    <button
                        onClick={() => runCurrentCode()}
                        disabled={isSubmitted || isSubmitting || isRunning}
                        className="px-3 py-1 bg-gray-100 text-gray-700 text-xs font-black uppercase rounded border border-gray-200 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    >
                        Run tests
                    </button>
                    <button
                        onClick={() => submitCurrentCode(interviewId || undefined)}
                        disabled={isSubmitted || isSubmitting || isRunning}
                        className="px-3 py-1 bg-blue-600 text-white text-xs font-black uppercase rounded border border-blue-700 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm shadow-blue-200"
                    >
                        Submit Solution
                    </button>
                </div>
            </div>

            <div className="flex-1 relative min-h-[400px]">
                <Editor
                    height="100%"
                    language={currentMonacoLang}
                    theme="vs-light"
                    value={code}
                    onChange={handleEditorChange}
                    options={{
                        readOnly: isSubmitted,
                        minimap: { enabled: false },
                        fontSize: 14,
                        scrollBeyondLastLine: false,
                        automaticLayout: true,
                        padding: { top: 16, bottom: 16 }
                    }}
                />
                {isSubmitted && (
                    <div className="absolute inset-0 bg-gray-50/20 z-10 pointer-events-none flex items-center justify-center">
                        <div className="bg-white/80 backdrop-blur-sm px-4 py-2 rounded-full border border-gray-200 shadow-xl text-xs font-bold text-gray-500 uppercase tracking-widest translate-y-20">
                            Solution Submitted - View Only
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}

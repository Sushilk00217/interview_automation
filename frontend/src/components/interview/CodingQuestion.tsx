import React, { useEffect } from "react"
import { useCodingStore } from "@/store/codingStore"
import ProblemPanel from "@/components/coding/ProblemPanel"
import CodeEditorPanel from "@/components/coding/CodeEditorPanel"
import ResultsPanel from "@/components/coding/ResultsPanel"

interface CodingQuestionProps {
    question: any;
    interviewId?: string | null;
}

export default function CodingQuestion({ question, interviewId }: CodingQuestionProps) {
    const {
        setProblemFromInterview,
        problem,
        results,
        resultSummary,
        isRunning,
        isSubmitting,
        error,
        submissionStatus
    } = useCodingStore()

    useEffect(() => {
        if (question) {
            setProblemFromInterview(question)
        }
    }, [question, setProblemFromInterview])

    if (!problem) return (
        <div className="flex items-center justify-center p-20 animate-pulse text-gray-400 font-medium">
            Loading problem configuration...
        </div>
    )

    return (
        <div className="flex flex-col xl:flex-row gap-6 h-[calc(100vh-280px)] min-h-[600px]">
            {/* Left Column: Problem */}
            <div className="flex-1 xl:w-2/5 h-full">
                <ProblemPanel
                    title={problem.title}
                    difficulty={problem.difficulty}
                    description={problem.description}
                    examples={problem.examples}
                />
            </div>

            {/* Right Column: Editor & Results */}
            <div className="flex-1 xl:w-3/5 flex flex-col gap-6 h-full">
                <div className="flex-[2] overflow-hidden">
                    <CodeEditorPanel />
                </div>
                <div className="flex-1 overflow-visible">
                    <ResultsPanel
                        results={results}
                        summary={resultSummary}
                        isRunning={isRunning}
                        isSubmitting={isSubmitting}
                        error={error}
                        submissionStatus={submissionStatus}
                    />
                </div>
            </div>
        </div>
    )
}

import { QuestionResponse } from "@/types/api";

interface QuestionPanelProps {
    question: QuestionResponse;
}

export default function QuestionPanel({ question }: QuestionPanelProps) {
    return (
        <div className="border rounded-lg shadow-sm bg-white overflow-hidden">
            <div className="bg-gray-50 px-6 py-4 border-b flex flex-wrap gap-2 items-center">
                <span className="bg-blue-100 text-blue-800 text-xs font-semibold px-2.5 py-0.5 rounded">
                    {question.category}
                </span>
                <span className="bg-green-100 text-green-800 text-xs font-semibold px-2.5 py-0.5 rounded">
                    {question.difficulty}
                </span>
                <span className="bg-purple-100 text-purple-800 text-xs font-semibold px-2.5 py-0.5 rounded">
                    {question.answer_mode}
                </span>
            </div>
            <div className="p-6">
                <pre className="whitespace-pre-wrap font-sans text-gray-800 text-lg leading-relaxed">
                    {question.question_text || question.prompt}
                </pre>
            </div>
        </div>
    );
}

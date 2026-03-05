"use client";

import { useState, useEffect, useRef } from "react";
import { useInterviewStore } from "@/store/interviewStore";
import QuestionPanel from "./QuestionPanel";
import AnswerPanel from "./AnswerPanel";
import CodingQuestion from "./CodingQuestion";
import Timer from "./Timer";
import VideoFeed from "./VideoFeed";
import { useProctoring } from "@/hooks/useProctoring";
import { azureTTS } from "@/lib/azureTTS";
import { apiClient } from "@/lib/apiClient";
import { useEffect as useEffectImport } from "react";

export default function InterviewShell() {
    const currentQuestion = useInterviewStore((s) => s.currentQuestion);
    const state = useInterviewStore((s) => s.state);
    const isSubmitting = useInterviewStore((s) => s.isSubmitting);
    const submitAnswer = useInterviewStore((s) => s.submitAnswer);
    const interviewId = useInterviewStore((s) => s.interviewId);

    const [answerPayload, setAnswerPayload] = useState("");
    const [proctoringAlerts, setProctoringAlerts] = useState(0);
    const [faceVerificationStatus, setFaceVerificationStatus] = useState<"verifying" | "verified" | "failed" | null>(null);
    const videoStreamRef = useRef<MediaStream | null>(null);
    const faceVerificationIntervalRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        setAnswerPayload("");
    }, [currentQuestion?.question_id]);

    // Set interview ID in API client for proctoring events
    useEffect(() => {
        if (interviewId) {
            apiClient.setInterviewId(interviewId);
        }
    }, [interviewId]);

    // Speak question when it changes
    useEffect(() => {
        if (currentQuestion?.question_text) {
            azureTTS.speak(currentQuestion.question_text).catch(console.error);
        }
        return () => {
            azureTTS.stop();
        };
    }, [currentQuestion?.question_text]);

    // Face verification every 5 seconds
    useEffect(() => {
        if (state === "QUESTION_ASKED" && videoStreamRef.current) {
            const performFaceVerification = async () => {
                try {
                    // Skip face verification if video stream is not available
                    if (!videoStreamRef.current) {
                        return;
                    }

                    setFaceVerificationStatus("verifying");
                    const videoTrack = videoStreamRef.current?.getVideoTracks()[0];
                    if (!videoTrack) {
                        console.warn("[FaceVerification] No video track available");
                        setFaceVerificationStatus("failed");
                        return;
                    }

                    // Check track state
                    if (videoTrack.readyState !== "live" && videoTrack.readyState !== "ended") {
                        console.warn("[FaceVerification] Video track not in live state:", videoTrack.readyState);
                        setFaceVerificationStatus("failed");
                        return;
                    }

                    // Check if ImageCapture is supported
                    if (typeof ImageCapture === "undefined") {
                        console.warn("[FaceVerification] ImageCapture API not supported - skipping verification");
                        setFaceVerificationStatus(null); // Don't show as failed, just skip
                        return;
                    }

                    // Use video element as fallback if ImageCapture fails
                    let bitmap: ImageBitmap | null = null;
                    try {
                        const imageCapture = new ImageCapture(videoTrack);
                        bitmap = await imageCapture.grabFrame();
                    } catch (captureError) {
                        // Fallback: use video element to capture frame
                        console.warn("[FaceVerification] ImageCapture failed, using video element fallback:", captureError);
                        try {
                            const videoElement = document.createElement("video");
                            videoElement.srcObject = videoStreamRef.current;
                            videoElement.width = 640;
                            videoElement.height = 480;
                            await new Promise((resolve, reject) => {
                                videoElement.onloadedmetadata = () => {
                                    videoElement.play().then(resolve).catch(reject);
                                };
                                videoElement.onerror = reject;
                                setTimeout(reject, 2000); // Timeout after 2 seconds
                            });

                            const canvas = document.createElement("canvas");
                            canvas.width = videoElement.videoWidth || 640;
                            canvas.height = videoElement.videoHeight || 480;
                            const ctx = canvas.getContext("2d");
                            if (ctx) {
                                ctx.drawImage(videoElement, 0, 0);
                                bitmap = await createImageBitmap(canvas);
                            }
                        } catch (fallbackError) {
                            console.error("[FaceVerification] Fallback capture also failed:", fallbackError);
                            setFaceVerificationStatus("failed");
                            return;
                        }
                    }

                    if (!bitmap) {
                        console.warn("[FaceVerification] Failed to capture frame");
                        setFaceVerificationStatus("failed");
                        return;
                    }

                    // Convert bitmap to blob
                    const canvas = document.createElement("canvas");
                    canvas.width = bitmap.width;
                    canvas.height = bitmap.height;
                    const ctx = canvas.getContext("2d");
                    if (!ctx) return;

                    ctx.drawImage(bitmap, 0, 0);
                    canvas.toBlob(async (blob) => {
                        if (!blob) {
                            console.warn("[FaceVerification] Failed to create blob from canvas");
                            setFaceVerificationStatus("failed");
                            return;
                        }

                        const formData = new FormData();
                        formData.append("image", blob, "face_verification.jpg");

                        try {
                            const token = localStorage.getItem("auth-storage")
                                ? JSON.parse(localStorage.getItem("auth-storage") || "{}")?.state?.token
                                : null;

                            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}/api/v1/verification/verify-face`, {
                                method: "POST",
                                headers: token ? {
                                    "Authorization": `Bearer ${token}`,
                                } : {},
                                body: formData,
                            });

                            if (response.ok) {
                                const data = await response.json();
                                if (data.verified) {
                                    setFaceVerificationStatus("verified");
                                } else {
                                    setFaceVerificationStatus("failed");
                                    setProctoringAlerts(prev => prev + 1);
                                    await apiClient.post("/api/v1/proctoring/event", {
                                        event_type: "FACE_MISMATCH",
                                        details: "Face verification failed",
                                    }).catch(err => console.error("[FaceVerification] Error posting event:", err));
                                }
                            } else {
                                const errorText = await response.text().catch(() => "Unknown error");
                                console.error("[FaceVerification] API error:", response.status, errorText);
                                setFaceVerificationStatus("failed");
                            }
                        } catch (error) {
                            console.error("[FaceVerification] Network error:", error);
                            setFaceVerificationStatus("failed");
                        }
                    }, "image/jpeg", 0.9);
                } catch (error) {
                    console.error("[FaceVerification] Unexpected error:", error);
                    setFaceVerificationStatus("failed");
                }
            };

            faceVerificationIntervalRef.current = setInterval(performFaceVerification, 5000);
            performFaceVerification(); // Initial verification

            return () => {
                if (faceVerificationIntervalRef.current) {
                    clearInterval(faceVerificationIntervalRef.current);
                }
            };
        }
    }, [state, currentQuestion]);

    // Proctoring: disable copy/paste, detect tab switching
    useProctoring({
        onTabSwitch: async () => {
            setProctoringAlerts(prev => {
                const newCount = prev + 1;
                if (newCount >= 5) {
                    // Auto-submit interview after 5 alerts
                    if (interviewId && currentQuestion) {
                        apiClient.post("/api/v1/proctoring/event", {
                            event_type: "TAB_SWITCH",
                            details: "Multiple tab switches detected",
                        }, true).then(() => {
                            submitAnswer({
                                question_id: currentQuestion.question_id,
                                answer_type: currentQuestion.answer_mode,
                                answer_payload: answerPayload,
                            });
                        }).catch(console.error);
                    }
                }
                return newCount;
            });
            if (interviewId) {
                await apiClient.post("/api/v1/proctoring/event", {
                    event_type: "TAB_SWITCH",
                    details: "Tab switch detected",
                }, true).catch(console.error);
            }
        },
        onCopy: async () => {
            setProctoringAlerts(prev => prev + 1);
            if (interviewId) {
                await apiClient.post("/api/v1/proctoring/event", {
                    event_type: "COPY_ATTEMPT",
                    details: "Copy attempt detected",
                }, true).catch(console.error);
            }
        },
        onPaste: async () => {
            setProctoringAlerts(prev => prev + 1);
            if (interviewId) {
                await apiClient.post("/api/v1/proctoring/event", {
                    event_type: "PASTE_ATTEMPT",
                    details: "Paste attempt detected",
                }, true).catch(console.error);
            }
        },
    });

    if (state !== "QUESTION_ASKED" || !currentQuestion) {
        return null;
    }

    const handleSubmit = () => {
        if (isSubmitting) return;
        if (currentQuestion?.type === "coding") {
            return;
        }
        // Allow submission if there's any content (trimmed)
        if (!answerPayload || !answerPayload.trim()) return;

        submitAnswer({
            question_id: currentQuestion.question_id,
            answer_type: currentQuestion.answer_mode,
            answer_payload: answerPayload.trim(),
        });
    };

    return (
        <div className="flex h-screen bg-gray-100">
            {/* Left Sidebar - Video Feed */}
            <div className="w-80 bg-white border-r border-gray-200 p-4 flex flex-col">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Live Video</h3>
                <VideoFeed
                    onStreamReady={(stream) => {
                        videoStreamRef.current = stream;
                    }}
                />

                {/* Face Verification Status */}
                <div className="mt-4 p-3 rounded-lg bg-gray-50">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium text-gray-600">Face Verification</span>
                        {faceVerificationStatus === "verified" && (
                            <span className="text-xs text-green-600">✓ Verified</span>
                        )}
                        {faceVerificationStatus === "failed" && (
                            <span className="text-xs text-red-600">✗ Failed</span>
                        )}
                        {faceVerificationStatus === "verifying" && (
                            <span className="text-xs text-yellow-600">Verifying...</span>
                        )}
                    </div>
                    {proctoringAlerts > 0 && (
                        <div className="text-xs text-red-600">
                            Alerts: {proctoringAlerts}/5
                        </div>
                    )}
                </div>
            </div>

            {/* Main Content Area */}
            <div className="flex-1 flex flex-col overflow-hidden">
                <div className="flex-1 overflow-y-auto p-6">
                    <div className="max-w-4xl mx-auto flex flex-col gap-6">
                        <div className="flex justify-between items-center">
                            <h2 className="text-xl font-bold">Question</h2>
                            <Timer durationSec={currentQuestion.time_limit_sec} onExpire={handleSubmit} />
                        </div>

                        {currentQuestion.type === "coding" ? (
                            <CodingQuestion question={currentQuestion} interviewId={interviewId} />
                        ) : (
                            <>
                                <QuestionPanel question={currentQuestion} />

                                <AnswerPanel
                                    mode={currentQuestion.answer_mode}
                                    value={answerPayload}
                                    onChange={setAnswerPayload}
                                    questionId={currentQuestion.question_id}
                                    onVoiceStart={async () => {
                                        // Voice verification will be handled by the AnswerPanel's audio stream
                                    }}
                                />

                                <button
                                    onClick={handleSubmit}
                                    disabled={
                                        isSubmitting ||
                                        !answerPayload ||
                                        !answerPayload.trim()
                                    }
                                    className="mt-4 px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed self-end transition-colors"
                                >
                                    {isSubmitting ? "Submitting..." : "Submit Answer"}
                                </button>
                            </>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

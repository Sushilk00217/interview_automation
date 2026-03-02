"use client";

import { useState, useRef, useEffect } from "react";

interface MediaCaptureProps {
    type: "photo" | "video" | "audio";
    onCapture: (file: File) => Promise<void>;
    isUploading: boolean;
    isVerified: boolean;
}

export default function MediaCapture({ type, onCapture, isUploading, isVerified }: MediaCaptureProps) {
    const [stream, setStream] = useState<MediaStream | null>(null);
    const [recording, setRecording] = useState(false);
    const [error, setError] = useState<string>("");
    const [preview, setPreview] = useState<string | null>(null);
    const [capturedFile, setCapturedFile] = useState<File | null>(null);
    
    const videoRef = useRef<HTMLVideoElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);

    useEffect(() => {
        return () => {
            // Cleanup stream on unmount
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
        };
    }, [stream]);

    // Ensure video plays when stream is set
    useEffect(() => {
        if (stream && videoRef.current && (type === "photo" || type === "video")) {
            videoRef.current.srcObject = stream;
            videoRef.current.play().catch(err => {
                console.error("Error playing video:", err);
                setError("Failed to display camera feed");
            });
        }
    }, [stream, type]);

    const startCapture = async () => {
        try {
            setError("");
            let mediaStream: MediaStream;

            if (type === "photo" || type === "video") {
                mediaStream = await navigator.mediaDevices.getUserMedia({
                    video: true,
                    audio: type === "video"
                });
            } else {
                mediaStream = await navigator.mediaDevices.getUserMedia({
                    audio: true
                });
            }

            setStream(mediaStream);
        } catch (err: any) {
            setError(`Failed to access ${type === "photo" ? "camera" : type === "video" ? "camera/microphone" : "microphone"}. Please check permissions.`);
            console.error("Media access error:", err);
        }
    };

    const stopCapture = () => {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            setStream(null);
        }
        if (videoRef.current) {
            videoRef.current.srcObject = null;
        }
        setRecording(false);
    };

    const handleSubmit = async () => {
        if (capturedFile) {
            await onCapture(capturedFile);
            setCapturedFile(null);
            if (preview) {
                URL.revokeObjectURL(preview);
                setPreview(null);
            }
        }
    };

    const handleCancel = () => {
        setCapturedFile(null);
        if (preview) {
            URL.revokeObjectURL(preview);
            setPreview(null);
        }
    };

    const capturePhoto = () => {
        if (videoRef.current && canvasRef.current) {
            const canvas = canvasRef.current;
            const video = videoRef.current;
            
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext("2d");
            if (ctx) {
                ctx.drawImage(video, 0, 0);
                canvas.toBlob((blob) => {
                    if (blob) {
                        const file = new File([blob], "photo.jpg", { type: "image/jpeg" });
                        setCapturedFile(file);
                        const previewUrl = URL.createObjectURL(blob);
                        setPreview(previewUrl);
                        stopCapture();
                    }
                }, "image/jpeg", 0.95);
            }
        }
    };

    const startRecording = () => {
        if (!stream) return;

        const mimeType = type === "video" 
            ? (MediaRecorder.isTypeSupported("video/webm") ? "video/webm" : "video/mp4")
            : (MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "audio/wav");

        try {
            const mediaRecorder = new MediaRecorder(stream, {
                mimeType: mimeType || undefined
            });
            mediaRecorderRef.current = mediaRecorder;
            chunksRef.current = [];

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    chunksRef.current.push(e.data);
                }
            };

            mediaRecorder.onstop = () => {
                const blobType = type === "video" ? "video/webm" : "audio/webm";
                const blob = new Blob(chunksRef.current, { 
                    type: blobType
                });
                const fileExtension = type === "video" ? "webm" : "webm";
                const file = new File([blob], `${type}_sample.${fileExtension}`, {
                    type: blobType
                });
                setCapturedFile(file);
                if (type === "video") {
                    const previewUrl = URL.createObjectURL(blob);
                    setPreview(previewUrl);
                }
                stopCapture();
            };

            mediaRecorder.start();
            setRecording(true);
        } catch (err: any) {
            setError(`Failed to start recording: ${err.message}`);
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && recording) {
            mediaRecorderRef.current.stop();
            setRecording(false);
            stopCapture();
        }
    };

    const getTitle = () => {
        switch (type) {
            case "photo": return "Face Verification Photo";
            case "video": return "Video Sample";
            case "audio": return "Voice Verification";
            default: return "";
        }
    };

    const getDescription = () => {
        switch (type) {
            case "photo": return "Take a clear photo of your face for identity verification";
            case "video": return "Record a short video sample";
            case "audio": return "Record your voice for voice verification";
            default: return "";
        }
    };

    return (
        <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
            <div className="flex items-center justify-between">
                <div>
                    <h3 className="text-lg font-semibold text-gray-900">{getTitle()}</h3>
                    <p className="text-sm text-gray-600 mt-1">{getDescription()}</p>
                </div>
                {isVerified && (
                    <div className="flex items-center gap-2 text-green-600">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clipRule="evenodd" />
                        </svg>
                        <span className="text-sm font-medium">Verified</span>
                    </div>
                )}
            </div>

            {error && (
                <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
                    {error}
                </div>
            )}

            {!stream && !isVerified && !capturedFile && (
                <button
                    onClick={startCapture}
                    className="w-full py-3 px-4 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
                >
                    Start {type === "photo" ? "Camera" : type === "video" ? "Camera & Microphone" : "Microphone"}
                </button>
            )}

            {capturedFile && !isVerified && (
                <div className="space-y-4">
                    {preview && (
                        <div className="space-y-2">
                            <p className="text-sm font-medium text-gray-700">Preview:</p>
                            {type === "photo" && (
                                <img src={preview} alt="Preview" className="w-full rounded-lg border border-gray-200" />
                            )}
                            {type === "video" && (
                                <video src={preview} controls className="w-full rounded-lg border border-gray-200" />
                            )}
                        </div>
                    )}
                    {type === "audio" && (
                        <div className="p-4 bg-gray-50 rounded-lg text-center">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-12 h-12 mx-auto text-green-600">
                                <path d="M8.25 4.5a3.75 3.75 0 117.5 0v8.25m-11.5 0V8.25m11.5 0V12m-11.5 0V8.25m0 8.25h3.75a3.75 3.75 0 003.75-3.75V8.25m0 0H12m-8.25 0H3.375c-.621 0-1.125-.504-1.125-1.125v-1.5c0-.621.504-1.125 1.125-1.125H3.375c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125zm12.75 0h1.125c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H20.625c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125z" />
                            </svg>
                            <p className="mt-2 text-sm text-gray-600">Voice sample recorded</p>
                        </div>
                    )}
                    <div className="flex gap-3">
                        <button
                            onClick={handleSubmit}
                            disabled={isUploading}
                            className="flex-1 py-2 px-4 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {isUploading ? "Submitting..." : "Submit Sample"}
                        </button>
                        <button
                            onClick={handleCancel}
                            disabled={isUploading}
                            className="py-2 px-4 bg-gray-200 text-gray-700 rounded-lg font-medium hover:bg-gray-300 transition-colors disabled:opacity-50"
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            )}

            {stream && !capturedFile && (
                <div className="space-y-4">
                    {(type === "photo" || type === "video") && (
                        <div className="relative bg-black rounded-lg overflow-hidden" style={{ minHeight: '300px' }}>
                            <video
                                ref={videoRef}
                                autoPlay
                                playsInline
                                muted={type === "photo"}
                                className="w-full h-auto max-h-96 object-cover"
                                style={{ width: '100%', height: 'auto', display: 'block' }}
                            />
                            <canvas ref={canvasRef} className="hidden" />
                        </div>
                    )}

                    {type === "audio" && (
                        <div className="p-8 bg-gray-100 rounded-lg text-center">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-16 h-16 mx-auto text-blue-600">
                                <path d="M8.25 4.5a3.75 3.75 0 117.5 0v8.25m-11.5 0V8.25m11.5 0V12m-11.5 0V8.25m0 8.25h3.75a3.75 3.75 0 003.75-3.75V8.25m0 0H12m-8.25 0H3.375c-.621 0-1.125-.504-1.125-1.125v-1.5c0-.621.504-1.125 1.125-1.125H3.375c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125zm12.75 0h1.125c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H20.625c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125z" />
                            </svg>
                            <p className="mt-4 text-sm text-gray-600">
                                {recording ? "Recording..." : "Microphone is ready"}
                            </p>
                        </div>
                    )}

                    <div className="flex gap-3">
                        {type === "photo" && (
                            <button
                                onClick={capturePhoto}
                                className="flex-1 py-2 px-4 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 transition-colors"
                            >
                                Capture Photo
                            </button>
                        )}

                        {(type === "video" || type === "audio") && (
                            <>
                                {!recording ? (
                                    <button
                                        onClick={startRecording}
                                        className="flex-1 py-2 px-4 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 transition-colors"
                                    >
                                        Start Recording
                                    </button>
                                ) : (
                                    <button
                                        onClick={stopRecording}
                                        className="flex-1 py-2 px-4 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 transition-colors flex items-center justify-center gap-2"
                                    >
                                        <span className="w-3 h-3 bg-white rounded-full animate-pulse" />
                                        Stop Recording
                                    </button>
                                )}
                            </>
                        )}

                        <button
                            onClick={stopCapture}
                            className="py-2 px-4 bg-gray-200 text-gray-700 rounded-lg font-medium hover:bg-gray-300 transition-colors"
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

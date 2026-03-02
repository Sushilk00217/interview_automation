import { apiClient } from "./apiClient";

const BASE = "/api/v1/candidate";

export interface VerificationStatus {
  face_enrolled: boolean;
  voice_enrolled: boolean;
  face_updated_at: string | null;
  voice_updated_at: string | null;
}

export interface FaceUploadResponse {
  message: string;
  face_ref_id: string;
}

export interface VoiceUploadResponse {
  message: string;
  voice_ref_id: string;
}

export const verificationService = {
  getVerificationStatus(): Promise<VerificationStatus> {
    return apiClient.get<VerificationStatus>(`${BASE}/profile/verification-status`);
  },

  uploadFace(photoBlob: Blob, filename: string = "photo.jpg"): Promise<FaceUploadResponse> {
    const formData = new FormData();
    formData.append("photo", photoBlob, filename);
    return apiClient.post<FaceUploadResponse, FormData>(`${BASE}/profile/face`, formData, false, true);
  },

  uploadVoice(audioBlob: Blob, filename: string = "recording.webm"): Promise<VoiceUploadResponse> {
    const formData = new FormData();
    formData.append("audio", audioBlob, filename);
    return apiClient.post<VoiceUploadResponse, FormData>(`${BASE}/profile/voice`, formData, false, true);
  },
};

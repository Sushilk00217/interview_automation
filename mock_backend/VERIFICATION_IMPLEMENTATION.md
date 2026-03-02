# Verification Implementation Summary

## Overview
Implemented face and voice verification system for candidates using Azure services. Candidates must upload photo and voice samples before they can start an interview.

## Features Implemented

### 1. ✅ Face Verification
- **Photo Upload**: Candidates can capture a photo using their camera
- **Azure Face API Integration**: Photos are processed and stored in Azure Face API
- **Person Group Management**: Creates person groups and persons for each candidate
- **Verification Status**: Tracks whether face verification is complete

### 2. ✅ Voice Verification
- **Voice Recording**: Candidates can record their voice using their microphone
- **Azure Speech Service Integration**: Voice samples are enrolled in Azure Speech Service
- **Voice Profile Creation**: Creates voice profiles for each candidate
- **Verification Status**: Tracks whether voice verification is complete

### 3. ✅ Video Sample (Optional)
- **Video Recording**: Candidates can record a video sample
- **Storage**: Videos are stored locally for future use

### 4. ✅ Interview Start Gate
- **Verification Check**: Interview cannot be started until both face and voice are verified
- **Clear Error Messages**: Shows specific messages about what verification is missing
- **Status Display**: Dashboard shows verification status clearly

## Database Changes

### New Fields in `candidate_profiles` Table:
- `face_verified` (Boolean) - Whether face sample is verified
- `voice_verified` (Boolean) - Whether voice sample is verified
- `face_sample_url` (String) - Path to stored face sample
- `video_sample_url` (String) - Path to stored video sample
- `voice_sample_url` (String) - Path to stored voice sample
- `face_verification_id` (String) - Azure Face API person ID
- `voice_profile_id` (String) - Azure Speech Service profile ID

**Migration Applied**: `add_verification_fields`

## Backend Implementation

### New Files:
1. **`app/services/azure_verification_service.py`**
   - Handles Azure Face API integration
   - Handles Azure Speech Service integration
   - Falls back to mock mode if Azure credentials not configured

2. **`app/api/v1/verification_router.py`**
   - `/api/v1/verification/face-sample` - Upload face photo
   - `/api/v1/verification/video-sample` - Upload video sample
   - `/api/v1/verification/voice-sample` - Upload voice sample
   - `/api/v1/verification/status` - Get verification status

### Updated Files:
1. **`app/services/interview_sql_service.py`**
   - Added verification check in `start_interview()` method
   - Added verification status to `get_active_interview_for_candidate()` response

2. **`app/db/sql/models/user.py`**
   - Added verification fields to `CandidateProfile` model

3. **`app/main.py`**
   - Added verification router

## Frontend Implementation

### New Files:
1. **`frontend/src/components/verification/MediaCapture.tsx`**
   - React component for capturing photo/video/audio
   - Uses browser MediaDevices API
   - Handles camera and microphone access
   - Shows preview and recording status

2. **`frontend/src/lib/api/verification.ts`**
   - API client for verification endpoints
   - Functions: `getVerificationStatus()`, `uploadFaceSample()`, `uploadVoiceSample()`, `uploadVideoSample()`

### Updated Files:
1. **`frontend/src/app/candidate/page.tsx`**
   - Added verification section above interview card
   - Shows verification status
   - Blocks interview start if verification incomplete
   - Displays clear messages about missing verification

2. **`frontend/src/lib/api/interviews.ts`**
   - Updated `ActiveInterviewResponse` to include `face_verified` and `voice_verified`

## Environment Variables Required

Add to your `.env` file in `mock_backend/`:

```env
# Azure Face API (for face verification)
AZURE_FACE_API_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_FACE_API_KEY=your-face-api-key
AZURE_FACE_PERSON_GROUP_ID=interview_candidates

# Azure Speech Service (for voice verification)
AZURE_SPEECH_API_KEY=your-speech-api-key
AZURE_SPEECH_REGION=your-region (e.g., eastus)
```

**Note**: If Azure credentials are not configured, the system will use mock mode (always returns verified=true). This is useful for development/testing.

## File Storage

Verification samples are stored in:
- `mock_backend/uploads/verification/`
- Files are named: `{candidate_id}_{type}_{uuid}.{extension}`
- Types: `face`, `video`, `voice`

## User Flow

1. **Candidate logs in** → Dashboard shows verification section
2. **Upload Photo** → Click "Start Camera" → Capture photo → Upload
3. **Record Voice** → Click "Start Microphone" → Record → Stop → Upload
4. **Verification Complete** → Green checkmark appears
5. **Start Interview** → Button becomes enabled (if scheduled time has passed)

## API Endpoints

### POST `/api/v1/verification/face-sample`
- **Body**: `multipart/form-data` with `photo` file
- **Response**: `{ success: true, face_verified: true, face_sample_url: "..." }`

### POST `/api/v1/verification/video-sample`
- **Body**: `multipart/form-data` with `video` file
- **Response**: `{ success: true, video_sample_url: "..." }`

### POST `/api/v1/verification/voice-sample`
- **Body**: `multipart/form-data` with `audio` file
- **Response**: `{ success: true, voice_verified: true, voice_sample_url: "..." }`

### GET `/api/v1/verification/status`
- **Response**: 
  ```json
  {
    "face_verified": true,
    "voice_verified": true,
    "can_start_interview": true,
    "face_sample_url": "...",
    "voice_sample_url": "...",
    "video_sample_url": "..."
  }
  ```

## Testing

1. **Without Azure** (Mock Mode):
   - System works without Azure credentials
   - All verifications return `true`
   - Good for development/testing

2. **With Azure**:
   - Configure environment variables
   - System creates person groups and profiles
   - Real verification happens during interview

## Next Steps

1. **Install dependencies** (if not already):
   ```bash
   cd mock_backend
   source venv/bin/activate
   pip install requests  # Already in requirements.txt
   ```

2. **Run migration** (already done):
   ```bash
   alembic upgrade head
   ```

3. **Configure Azure** (optional):
   - Create Azure Face API resource
   - Create Azure Speech Service resource
   - Add credentials to `.env`

4. **Test the flow**:
   - Register a candidate
   - Login as candidate
   - Upload photo and voice samples
   - Verify interview start is blocked until verification complete
   - Start interview after verification

## Notes

- Face verification uses Azure Face API Person Groups
- Voice verification uses Azure Speech Service Speaker Verification
- Samples are stored locally AND in Azure (for verification during interview)
- Verification status is checked before allowing interview start
- Clear error messages guide candidates through the process

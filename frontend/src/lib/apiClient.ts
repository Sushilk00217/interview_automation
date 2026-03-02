import { ApiError } from "@/types/api";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

function getBaseURL(): string {
    const url = typeof process !== "undefined" ? process.env.NEXT_PUBLIC_API_BASE_URL : undefined;
    return (url && url.trim() !== "") ? url.replace(/\/$/, "") : DEFAULT_API_BASE_URL;
}

class ApiClient {
    private baseURL: string;
    private interviewId: string | null = null;

    constructor(baseURL: string) {
        this.baseURL = baseURL;
    }

    /** Build error message from FastAPI-style { detail: string | array } or fallback to status text. */
    private getErrorMessage(data: unknown, response: Response): string {
        if (data && typeof data === "object" && "detail" in data) {
            const d = (data as { detail?: unknown }).detail;
            if (typeof d === "string") return d;
            if (Array.isArray(d)) return d.map((x: any) => x?.msg ?? JSON.stringify(x)).join("; ");
        }
        return `Request failed with status ${response.status}`;
    }

    /** Parse response text as JSON; if server returned HTML, throw a clear error instead of JSON parse error. */
    private parseJson(text: string): unknown {
        const trimmed = text.trim();
        if (!trimmed) return null;
        if (trimmed.startsWith("<")) {
            const error: ApiError = {
                error_code: "INVALID_RESPONSE",
                message: "Server returned HTML instead of JSON. Ensure the backend is running and NEXT_PUBLIC_API_BASE_URL points to it (e.g. http://localhost:8000).",
                current_state: null,
            };
            throw error;
        }
        try {
            return JSON.parse(text);
        } catch {
            const error: ApiError = {
                error_code: "INVALID_RESPONSE",
                message: "Server response was not valid JSON.",
                current_state: null,
            };
            throw error;
        }
    }

    setInterviewId(id: string): void {
        this.interviewId = id;
    }

    clearInterviewId(): void {
        this.interviewId = null;
    }

    private log(message: string): void {
        if (process.env.NODE_ENV === "development") {
            console.debug(`[ApiClient] ${message}`);
        }
    }
    
    private logError(message: string): void {
        console.error(`[ApiClient] ${message}`);
    }

    private parseResponse(text: string): any {
        if (!text) return null;
        
        // Check if response is HTML (common when backend is down or endpoint doesn't exist)
        if (text.trim().startsWith('<!DOCTYPE') || text.trim().startsWith('<html')) {
            throw new Error("Backend server returned HTML instead of JSON. Is the backend running?");
        }
        
        try {
            return JSON.parse(text);
        } catch (error) {
            // If it's not JSON and not HTML, return the text as error message
            throw new Error(`Invalid JSON response: ${text.substring(0, 100)}`);
        }
    }

    private getAuthToken(): string | null {
        // We can access localStorage directly since this runs on client
        if (typeof window !== 'undefined') {
            try {
                const storage = localStorage.getItem('auth-storage');
                if (storage) {
                    const parsed = JSON.parse(storage);
                    return parsed.state?.token || null;
                }
            } catch (error) {
                console.error("Failed to parse auth token from storage", error);
            }
        }
        return null;
    }

    async get<T>(path: string, requireInterviewId: boolean = false): Promise<T> {
        this.log(`REQUEST: GET ${path}`);

        const headers: Record<string, string> = {
            "Content-Type": "application/json",
        };

        const token = this.getAuthToken();
        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }

        if (requireInterviewId) {
            if (!this.interviewId) {
                const error: ApiError = {
                    error_code: "MISSING_INTERVIEW_ID",
                    message: "Interview ID is required but not set",
                    current_state: null,
                };
                this.log(`ERROR: GET ${path} - MISSING_INTERVIEW_ID`);
                throw error;
            }
            headers["X-Interview-Id"] = this.interviewId;
        }

        let response: Response;
        try {
            // Create AbortController for timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
            
            try {
                response = await fetch(`${this.baseURL}${path}`, {
                    method: "GET",
                    headers,
                    signal: controller.signal,
                });
                clearTimeout(timeoutId);
            } catch (fetchError: any) {
                clearTimeout(timeoutId);
                if (fetchError.name === 'AbortError') {
                    throw new Error(`Request timeout: Backend server at ${this.baseURL} did not respond within 10 seconds`);
                }
                throw fetchError;
            }
        } catch (error: any) {
            // Network error (backend not running, CORS, etc.)
            this.logError(`ERROR: GET ${path} - Network error: ${error.message}`);
            
            let errorMessage = error.message || "Failed to fetch";
            
            // Provide more specific error messages
            if (errorMessage.includes("Failed to fetch") || errorMessage.includes("NetworkError")) {
                errorMessage = `Cannot connect to backend server at ${this.baseURL}. Please ensure:
1. The backend server is running (check terminal where you ran 'uvicorn app.main:app --reload')
2. The server is accessible at ${this.baseURL}
3. No firewall is blocking the connection`;
            } else if (errorMessage.includes("timeout")) {
                errorMessage = `Backend server at ${this.baseURL} is not responding. Please check if the server is running.`;
            }
            
            const apiError: ApiError = {
                error_code: "NETWORK_ERROR",
                message: errorMessage,
                current_state: null,
            };
            // Create an Error object with message that includes "network" for auth store detection
            const networkError = new Error(apiError.message);
            (networkError as any).error_code = apiError.error_code;
            throw networkError;
        }

        const text = await response.text();
        let data: any = null;
        
        try {
            data = this.parseResponse(text);
        } catch (error: any) {
            this.log(`ERROR: GET ${path} - Failed to parse response: ${error.message}`);
            const apiError: ApiError = {
                error_code: "INVALID_RESPONSE",
                message: error.message || "Failed to parse server response",
                current_state: null,
            };
            throw apiError;
        }

        this.log(`RESPONSE: GET ${path} - ${response.status}`);

        if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
                // Optional: Trigger logout if we had a global store reference or event
                // For now just throw, UI should handle redirect
            }

            // Handle FastAPI validation errors (400 Bad Request)
            if (response.status === 400 && data && typeof data === "object") {
                if ("detail" in data) {
                    const detail = Array.isArray(data.detail) 
                        ? data.detail.map((err: any) => err.msg || JSON.stringify(err)).join(", ")
                        : data.detail;
                    const error: ApiError = {
                        error_code: "VALIDATION_ERROR",
                        message: detail || "Validation error",
                        current_state: null,
                    };
                    this.log(`ERROR: GET ${path} - VALIDATION_ERROR: ${detail}`);
                    throw error;
                }
            }

            // Handle custom API errors with error_code and message
            if (data && typeof data === "object" && "error_code" in data && "message" in data) {
                this.log(`ERROR: GET ${path} - ${(data as ApiError).error_code}`);
                throw data as ApiError;
            }
            
            // Handle FastAPI HTTPException format (has "detail" field)
            if (data && typeof data === "object" && "detail" in data) {
                const error: ApiError = {
                    error_code: `HTTP_${response.status}`,
                    message: data.detail || `Request failed with status ${response.status}`,
                    current_state: null,
                };
                this.log(`ERROR: GET ${path} - HTTP_${response.status}: ${data.detail}`);
                throw error;
            }
            
            // Generic HTTP error
            const error: ApiError = {
                error_code: "HTTP_ERROR",
                message: data?.detail || data?.message || `Request failed with status ${response.status}`,
                current_state: null,
            };
            this.log(`ERROR: GET ${path} - HTTP_ERROR`);
            throw error;
        }

        return data as T;
    }

    async post<T, B>(path: string, body: B, requireInterviewId: boolean = false, isFormData: boolean = false): Promise<T> {
        this.log(`REQUEST: POST ${path}`);

        const headers: Record<string, string> = {};

        if (!isFormData) {
            headers["Content-Type"] = "application/json";
        }

        const token = this.getAuthToken();
        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }

        if (requireInterviewId) {
            if (!this.interviewId) {
                const error: ApiError = {
                    error_code: "MISSING_INTERVIEW_ID",
                    message: "Interview ID is required but not set",
                    current_state: null,
                };
                this.log(`ERROR: POST ${path} - MISSING_INTERVIEW_ID`);
                throw error;
            }
            headers["X-Interview-Id"] = this.interviewId;
        }

        let response: Response;
        try {
            // Create AbortController for timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
            
            try {
                response = await fetch(`${this.baseURL}${path}`, {
                    method: "POST",
                    headers,
                    body: isFormData ? (body as any) : JSON.stringify(body),
                    signal: controller.signal,
                });
                clearTimeout(timeoutId);
            } catch (fetchError: any) {
                clearTimeout(timeoutId);
                if (fetchError.name === 'AbortError') {
                    throw new Error(`Request timeout: Backend server at ${this.baseURL} did not respond within 10 seconds`);
                }
                throw fetchError;
            }
        } catch (error: any) {
            // Network error (backend not running, CORS, etc.)
            this.logError(`ERROR: POST ${path} - Network error: ${error.message}`);
            
            let errorMessage = error.message || "Failed to fetch";
            
            // Provide more specific error messages
            if (errorMessage.includes("Failed to fetch") || errorMessage.includes("NetworkError")) {
                errorMessage = `Cannot connect to backend server at ${this.baseURL}. Please ensure:
1. The backend server is running (check terminal where you ran 'uvicorn app.main:app --reload')
2. The server is accessible at ${this.baseURL}
3. No firewall is blocking the connection`;
            } else if (errorMessage.includes("timeout")) {
                errorMessage = `Backend server at ${this.baseURL} is not responding. Please check if the server is running.`;
            }
            
            const apiError: ApiError = {
                error_code: "NETWORK_ERROR",
                message: errorMessage,
                current_state: null,
            };
            // Create an Error object with message that includes "network" for auth store detection
            const networkError = new Error(apiError.message);
            (networkError as any).error_code = apiError.error_code;
            throw networkError;
        }

        const text = await response.text();
        let data: any = null;
        
        // Log raw response for debugging
        this.log(`RESPONSE: POST ${path} - Status: ${response.status}, Body: ${text.substring(0, 200)}`);
        
        try {
            data = this.parseResponse(text);
        } catch (error: any) {
            this.log(`ERROR: POST ${path} - Failed to parse response: ${error.message}`);
            // If we can't parse but got a response, it might be HTML or plain text
            if (response.status >= 400) {
                const apiError: ApiError = {
                    error_code: "INVALID_RESPONSE",
                    message: `Server returned invalid response: ${text.substring(0, 100)}`,
                    current_state: null,
                };
                throw apiError;
            }
            const apiError: ApiError = {
                error_code: "INVALID_RESPONSE",
                message: error.message || "Failed to parse server response",
                current_state: null,
            };
            throw apiError;
        }

        this.log(`RESPONSE: POST ${path} - ${response.status}`);

        if (!response.ok) {
            // Handle FastAPI validation errors (400 Bad Request or 422 Unprocessable Entity)
            if ((response.status === 400 || response.status === 422) && data && typeof data === "object") {
                if ("detail" in data) {
                    // FastAPI format: {"detail": "error message"} or {"detail": [...]}
                    const detail = Array.isArray(data.detail) 
                        ? data.detail.map((err: any) => {
                            if (typeof err === "string") return err;
                            return err.msg || err.loc?.join(".") + ": " + err.msg || JSON.stringify(err);
                        }).join(", ")
                        : data.detail;
                    const error: ApiError = {
                        error_code: "VALIDATION_ERROR",
                        message: detail || "Validation error",
                        current_state: null,
                    };
                    this.logError(`ERROR: POST ${path} - VALIDATION_ERROR: ${detail}`);
                    // Create Error object with message for auth store detection
                    const validationError = new Error(detail || "Validation error");
                    (validationError as any).error_code = "VALIDATION_ERROR";
                    throw validationError;
                }
            }
            
            // Handle custom API errors with error_code and message
            if (data && typeof data === "object" && "error_code" in data && "message" in data) {
                this.log(`ERROR: POST ${path} - ${(data as any).error_code}`);
                throw data as ApiError;
            }
            
            // Handle FastAPI HTTPException format (has "detail" field)
            if (data && typeof data === "object" && "detail" in data) {
                const detailMsg = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
                const error: ApiError = {
                    error_code: `HTTP_${response.status}`,
                    message: detailMsg || `Request failed with status ${response.status}`,
                    current_state: null,
                };
                this.logError(`ERROR: POST ${path} - HTTP_${response.status}: ${detailMsg}`);
                // Create Error object with message for auth store detection
                const httpError = new Error(detailMsg || `Request failed with status ${response.status}`);
                (httpError as any).error_code = `HTTP_${response.status}`;
                throw httpError;
            }
            
            // Generic HTTP error
            const error: ApiError = {
                error_code: "HTTP_ERROR",
                message: data?.detail || data?.message || `Request failed with status ${response.status}. Response: ${text.substring(0, 200)}`,
                current_state: null,
            };
            this.log(`ERROR: POST ${path} - HTTP_ERROR: ${text.substring(0, 200)}`);
            throw error;
        }

        return data as T;
    }
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

if (!process.env.NEXT_PUBLIC_API_BASE_URL) {
    console.warn('[ApiClient] NEXT_PUBLIC_API_BASE_URL not set, using default: http://localhost:8000');
}

export const apiClient = new ApiClient(API_BASE_URL);

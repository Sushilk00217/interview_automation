import { create } from "zustand";
import { persist } from "zustand/middleware";
import { authService } from "@/lib/authService";
import { AuthRequest } from "@/types/api";

interface User {
    username: string;
    role: string;
}

interface AuthState {
    user: User | null;
    token: string | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    error: string | null;
    // true once Zustand has finished rehydrating from localStorage
    _hasHydrated: boolean;

    setHasHydrated: (value: boolean) => void;
    login: (credentials: AuthRequest, type: 'admin' | 'candidate') => Promise<void>;
    logout: () => void;
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set) => ({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,
            _hasHydrated: false,

            setHasHydrated: (value) => set({ _hasHydrated: value }),

            login: async (credentials, type) => {
                set({ isLoading: true, error: null });
                try {
                    const response = type === 'admin'
                        ? await authService.loginAdmin(credentials)
                        : await authService.loginCandidate(credentials);

                    set({
                        user: { username: response.username, role: response.role },
                        token: response.access_token,
                        isAuthenticated: true,
                        isLoading: false,
                    });
                } catch (error: any) {
                    let message = "Login failed. Please try again.";
                    
                    // Log error for debugging
                    console.error("[AuthStore] Login error:", error);

                    // Extract error_code from error object (could be on error or error.error_code)
                    const errorCode = error.error_code || (error as any)?.error_code;
                    const errorMessage = error.message || error.detail || "Login failed. Please try again.";

                    if (errorMessage) {
                        const errorMsg = errorMessage.toLowerCase();
                        if (errorMsg.includes("incorrect") || errorMsg.includes("credentials")) {
                            message = "Invalid username or password.";
                        } else if (errorMsg.includes("not a candidate") || errorMsg.includes("not an admin")) {
                            message = "Access denied. Please use the correct login portal.";
                        } else if (errorMsg.includes("fetch") || errorMsg.includes("network") || errorMsg.includes("backend server")) {
                            message = "Unable to connect to the server. Please ensure the backend is running at http://localhost:8000";
                        } else if (errorCode === "NETWORK_ERROR" || errorCode === "INVALID_RESPONSE") {
                            message = errorMessage || "Unable to connect. Please try again later.";
                        } else if (errorCode === "VALIDATION_ERROR") {
                            message = errorMessage || "Invalid request. Please check your input.";
                        } else if (errorCode?.startsWith("HTTP_")) {
                            // FastAPI HTTP errors
                            message = errorMessage;
                        } else {
                            // Use the actual error message
                            message = errorMessage;
                        }
                    } else if (errorCode) {
                        // Handle ApiError objects without message
                        if (errorCode === "NETWORK_ERROR") {
                            message = "Unable to connect. Please ensure the backend is running.";
                        } else if (errorCode === "VALIDATION_ERROR") {
                            message = "Invalid request. Please check your input.";
                        } else {
                            message = "Login failed. Please try again.";
                        }
                    }

                    set({ error: message, isLoading: false });
                    throw error;
                }
            },

            logout: () => {
                authService.logout();
                set({ user: null, token: null, isAuthenticated: false });
            },
        }),
        {
            name: "auth-storage",
            partialize: (state) => ({
                user: state.user,
                token: state.token,
                isAuthenticated: state.isAuthenticated,
            }),
            // Called when rehydration from localStorage is complete
            onRehydrateStorage: () => (state) => {
                state?.setHasHydrated(true);
            },
        }
    )
);

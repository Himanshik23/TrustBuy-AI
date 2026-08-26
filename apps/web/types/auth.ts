// Mirrors services/auth-service/app/schemas.py - kept manually in sync for
// Phase 1; a generated client from the OpenAPI schema is the documented
// Phase 2+ upgrade (ARCHITECTURE.md §7 folder structure note on types/).

export interface User {
  id: string;
  email: string;
  display_name: string;
  avatar_url: string | null;
  trust_points: number;
  reputation_level: "shopper" | "investigator" | "fraud_hunter" | "trust_guardian" | "trust_ambassador";
  is_admin: boolean;
  is_moderator: boolean;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface SignupPayload {
  email: string;
  password: string;
  display_name: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    request_id: string | null;
  };
}

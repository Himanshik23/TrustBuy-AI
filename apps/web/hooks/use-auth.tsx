"use client";

import * as React from "react";

import { getMe, login as loginRequest, logout as logoutRequest, refreshSession, signup as signupRequest } from "@/lib/api/auth";
import { setAccessToken } from "@/lib/api/token-store";
import type { LoginPayload, SignupPayload, User } from "@/types/auth";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  signup: (payload: SignupPayload) => Promise<void>;
  logout: () => Promise<void>;
  refetchUser: () => Promise<void>;
}

const AuthContext = React.createContext<AuthContextValue | undefined>(undefined);

/** Boots the session on first paint by attempting a silent refresh against
 * the httpOnly cookie (docs/USER_FLOWS.md onboarding flow) - so a page
 * reload doesn't force a re-login as long as the refresh cookie is valid. */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<User | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { access_token, user: sessionUser } = await refreshSession();
        setAccessToken(access_token);
        if (!cancelled) setUser(sessionUser);
      } catch {
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = React.useCallback(async (payload: LoginPayload) => {
    const { access_token, user: sessionUser } = await loginRequest(payload);
    setAccessToken(access_token);
    setUser(sessionUser);
  }, []);

  const signup = React.useCallback(async (payload: SignupPayload) => {
    const { access_token, user: sessionUser } = await signupRequest(payload);
    setAccessToken(access_token);
    setUser(sessionUser);
  }, []);

  const logout = React.useCallback(async () => {
    await logoutRequest().catch(() => undefined);
    setAccessToken(null);
    setUser(null);
  }, []);

  const refetchUser = React.useCallback(async () => {
    const fresh = await getMe();
    setUser(fresh);
  }, []);

  const value = React.useMemo(
    () => ({ user, isLoading, login, signup, logout, refetchUser }),
    [user, isLoading, login, signup, logout, refetchUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>.");
  return ctx;
}

// One function per Authentication Service endpoint (API_DOCUMENTATION.md
// §1) - nothing outside this file calls /auth/* directly.

import { apiClient } from "./client";
import type { LoginPayload, LoginResponse, SignupPayload, User } from "@/types/auth";

export async function signup(payload: SignupPayload): Promise<LoginResponse> {
  const { data } = await apiClient.post<LoginResponse>("/auth/signup", payload);
  return data;
}

export async function login(payload: LoginPayload): Promise<LoginResponse> {
  const { data } = await apiClient.post<LoginResponse>("/auth/login", payload);
  return data;
}

export async function refreshSession(): Promise<LoginResponse> {
  const { data } = await apiClient.post<LoginResponse>("/auth/refresh", {});
  return data;
}

export async function logout(): Promise<void> {
  await apiClient.post("/auth/logout");
}

export async function getMe(): Promise<User> {
  const { data } = await apiClient.get<User>("/auth/me");
  return data;
}

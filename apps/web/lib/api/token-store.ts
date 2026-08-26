// In-memory-only access-token store (docs/SECURITY.md §1: never persist
// the access token to localStorage/sessionStorage - that's an XSS
// exfiltration target). Lost on full page reload by design; AuthProvider
// re-derives it via a silent POST /auth/refresh (httpOnly cookie) on boot.

type Listener = (token: string | null) => void;

let accessToken: string | null = null;
const listeners = new Set<Listener>();

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
  listeners.forEach((listener) => listener(token));
}

export function subscribeAccessToken(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

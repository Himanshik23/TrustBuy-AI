// Smart URL Input helpers (landing page + dashboard "paste a link" box).
// Client-side convenience only - the server's Smart URL Intake Pipeline
// (services/catalog-service/app/intake.py) remains the actual source of
// truth for what's accepted; this just lets people paste a bare domain
// ("nike.in") the way they'd type it in a browser bar, instead of
// rejecting anything that isn't already a fully-qualified https:// URL.

const BARE_DOMAIN_RE = /^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+(\/.*)?$/i;

/** Turns a naturally-typed shopping link into a full URL. Never throws -
 * unrecognizable input is returned trimmed and unchanged so validation
 * can give the user a clear message instead of a silent transformation. */
export function normalizeShoppingUrl(raw: string): string {
  let value = raw.trim();
  if (!value) return value;

  // Strip stray wrapping punctuation from pasted markdown-style links or
  // quoted text, e.g. `<https://nike.in>` or `"amazon.in"`.
  value = value.replace(/^[<"'\s]+|[>"'\s]+$/g, "");

  if (/^https?:\/\//i.test(value)) return value;
  if (/^www\./i.test(value)) return `https://${value}`;

  if (BARE_DOMAIN_RE.test(value)) {
    // A bare root domain with no path ("nike.in") is what most people
    // type when they mean the brand's main site - the `www.` form is the
    // one that reliably resolves for the widest range of storefronts.
    // Anything with a path already looks like a pasted product link, so
    // it's left exactly as typed (aside from the protocol).
    const hasPath = value.includes("/");
    return hasPath ? `https://${value}` : `https://www.${value}`;
  }

  return value;
}

export interface UrlCheckResult {
  ok: boolean;
  normalized: string;
  message?: string;
}

/** Friendly, non-technical validation for the *normalized* value. */
export function checkShoppingUrl(raw: string): UrlCheckResult {
  const normalized = normalizeShoppingUrl(raw);

  if (!normalized) {
    return { ok: false, normalized, message: "Paste a product link to get started." };
  }

  let parsed: URL;
  try {
    parsed = new URL(normalized);
  } catch {
    return {
      ok: false,
      normalized,
      message: "That doesn't look like a link yet - try something like nike.in or amazon.in/product.",
    };
  }

  if (!/^https?:$/.test(parsed.protocol)) {
    return { ok: false, normalized, message: "Links need to start with http:// or https://." };
  }
  if (!parsed.hostname.includes(".")) {
    return { ok: false, normalized, message: "That link is missing a valid domain, like nike.in or amazon.in." };
  }

  return { ok: true, normalized };
}

export const EXAMPLE_URLS = ["nike.in", "amazon.in/product", "flipkart.com", "myntra.com"];

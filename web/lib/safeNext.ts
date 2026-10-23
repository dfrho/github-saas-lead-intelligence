/**
 * Sanitize a post-login `next` redirect target so it can only point inside this app.
 *
 * Callers build URLs like `${origin}${next}`, so values such as "@evil.com" or
 * ".evil.com" would otherwise change the host. Only same-origin paths are allowed.
 */
const PLACEHOLDER_ORIGIN = "http://placeholder.invalid";

export function safeNext(next: string | null | undefined, fallback = "/dashboard"): string {
  if (!next || !next.startsWith("/") || next.startsWith("//")) return fallback;
  // Backslashes and control characters are normalized by browsers into "//"-style hosts
  if (/[\\\u0000-\u001f\u007f]/.test(next)) return fallback;
  try {
    const url = new URL(next, PLACEHOLDER_ORIGIN);
    if (url.origin !== PLACEHOLDER_ORIGIN) return fallback;
    return url.pathname + url.search + url.hash;
  } catch {
    return fallback;
  }
}

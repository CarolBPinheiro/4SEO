/**
 * URLs públicas do ecossistema 4SEO.
 * Marketing = este Next.js; App = Vite autenticado (FastAPI + Supabase).
 */

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

/** Base do app autenticado (Vite). Ex.: http://localhost:8080 */
export function getAppBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_APP_URL?.trim();
  if (raw) {
    return trimTrailingSlash(raw);
  }
  return "http://localhost:8080";
}

/** URL da tela Minha Conta (login / criar conta) do app autenticado. */
export function getAppLoginUrl(): string {
  return `${getAppBaseUrl()}/login`;
}

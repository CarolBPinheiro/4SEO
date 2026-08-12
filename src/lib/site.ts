/** URL do site de marketing (Next.js — UX/UI atual). */
export function getMarketingUrl(): string {
  const configured = import.meta.env.VITE_MARKETING_URL?.trim();
  if (configured) {
    return configured.replace(/\/+$/, "");
  }
  return "http://localhost:3000";
}

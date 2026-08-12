import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react-swc";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: [path.resolve(__dirname, "./src/test/setup.ts")],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    // Nested em Documents/4SEO — evita herdar root do pacote pai
    root: __dirname,
    env: {
      // Valores fictícios só para testes — nunca usar em produção
      VITE_SUPABASE_URL: "https://example.supabase.co",
      VITE_SUPABASE_PUBLISHABLE_KEY: "test-anon-key-not-real",
      VITE_API_BASE_URL: "/api",
      VITE_MARKETING_URL: "http://localhost:3000",
    },
  },
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
});

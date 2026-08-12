/**
 * Mescla export estático do Next (marketing/checkout) com o build Vite (app autenticado)
 * em um único diretório publicável em https://4seo.app
 *
 * Pré-requisito: `npm run build:marketing` (output: out/) e `npm run build:app` (output: dist/).
 *
 * Importante: NÃO usar redirect catch-all `/* → spa.html` — no Netlify isso pode
 * interceptar estáticos como /videos/*.mp4 e devolver HTML no lugar do arquivo.
 */
import {
  cpSync,
  existsSync,
  mkdirSync,
  renameSync,
  rmSync,
  writeFileSync,
} from "fs";
import { join } from "path";

const ROOT = process.cwd();
const NEXT_OUT = join(ROOT, "out");
const VITE_DIST = join(ROOT, "dist");
const PUBLIC_DIR = join(ROOT, "public");
const DEPLOY = join(ROOT, "deploy-out");

const SPA_ROUTES = [
  "/login",
  "/dashboard",
  "/analise",
  "/integracoes",
  "/termos",
  "/historico",
  "/panorama",
  "/admin",
  "/admin/*",
  "/app",
  "/keywords",
  "/shopify",
  "/nuvemshop",
];

function assertDir(path, label) {
  if (!existsSync(path)) {
    throw new Error(
      `Diretório ausente (${label}): ${path}. Rode o build correspondente antes.`,
    );
  }
}

assertDir(NEXT_OUT, "Next export");
assertDir(VITE_DIST, "Vite dist");

rmSync(DEPLOY, { recursive: true, force: true });
mkdirSync(DEPLOY, { recursive: true });

// 1) Marketing Next primeiro (inclui public/videos, páginas /, /sobre, /checkout)
cpSync(NEXT_OUT, DEPLOY, { recursive: true });

// 2) App Vite: index vira spa.html; demais assets (JS/CSS) entram no deploy
const viteIndex = join(VITE_DIST, "index.html");
if (!existsSync(viteIndex)) {
  throw new Error(`Vite index.html ausente em ${VITE_DIST}`);
}
cpSync(VITE_DIST, DEPLOY, { recursive: true });
renameSync(join(DEPLOY, "index.html"), join(DEPLOY, "spa.html"));
// Restaura a home do marketing (Next) que o Vite havia sobrescrito
cpSync(join(NEXT_OUT, "index.html"), join(DEPLOY, "index.html"));
if (existsSync(join(NEXT_OUT, "index.txt"))) {
  cpSync(join(NEXT_OUT, "index.txt"), join(DEPLOY, "index.txt"));
}

// 3) Garante mídia de marketing (vídeo do Hero) mesmo se algum passo omitir
const videosSrc = join(PUBLIC_DIR, "videos");
if (existsSync(videosSrc)) {
  cpSync(videosSrc, join(DEPLOY, "videos"), { recursive: true });
}

// 4) Redirects só para rotas SPA conhecidas — sem catch-all /*
const redirects = [
  "# Gerado por scripts/merge-frontend-deploy.mjs — nao editar a mao",
  "# Sem /* → spa.html: catch-all quebra /videos/*.mp4 e outros estaticos no Netlify.",
  ...SPA_ROUTES.map((route) => `${route}    /spa.html   200`),
].join("\n");

writeFileSync(join(DEPLOY, "_redirects"), `${redirects}\n`, "utf8");

writeFileSync(
  join(DEPLOY, "deploy-meta.json"),
  `${JSON.stringify(
    {
      generatedAt: new Date().toISOString(),
      nextOut: "out/",
      viteDist: "dist/",
      spaRoutes: SPA_ROUTES,
      videosGuaranteed: existsSync(videosSrc),
    },
    null,
    2,
  )}\n`,
  "utf8",
);

console.log(
  `OK — deploy-out pronto (${SPA_ROUTES.length} rotas SPA + marketing Next, videos garantidos).`,
);

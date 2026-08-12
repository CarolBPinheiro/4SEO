/**
 * Mescla export estático do Next (marketing/checkout) com o build Vite (app autenticado)
 * em um único diretório publicável em https://4seo.app
 *
 * Pré-requisito: `npm run build:marketing` (output: out/) e `npm run build:app` (output: dist/).
 */
import { cpSync, existsSync, mkdirSync, renameSync, rmSync, writeFileSync } from "fs";
import { join } from "path";

const ROOT = process.cwd();
const NEXT_OUT = join(ROOT, "out");
const VITE_DIST = join(ROOT, "dist");
const DEPLOY = join(ROOT, "deploy-out");

const SPA_ROUTES = [
  "/login",
  "/dashboard",
  "/analise",
  "/integracoes",
  "/termos",
  "/historico",
  "/panorama",
  "/app",
  "/keywords",
  "/shopify",
  "/nuvemshop",
];

function assertDir(path, label) {
  if (!existsSync(path)) {
    throw new Error(`Diretório ausente (${label}): ${path}. Rode o build correspondente antes.`);
  }
}

assertDir(NEXT_OUT, "Next export");
assertDir(VITE_DIST, "Vite dist");

rmSync(DEPLOY, { recursive: true, force: true });
mkdirSync(DEPLOY, { recursive: true });

cpSync(VITE_DIST, DEPLOY, { recursive: true });
renameSync(join(DEPLOY, "index.html"), join(DEPLOY, "spa.html"));
cpSync(NEXT_OUT, DEPLOY, { recursive: true });

const redirects = [
  "# Gerado por scripts/merge-frontend-deploy.mjs — nao editar a mao",
  "# Arquivos estaticos do Next (/, /checkout/*, /sobre) tem precedencia sobre redirects.",
  ...SPA_ROUTES.map((route) => `${route}    /spa.html   200`),
  "/*               /spa.html   200",
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
    },
    null,
    2,
  )}\n`,
  "utf8",
);

console.log(`OK — deploy-out pronto (${SPA_ROUTES.length} rotas SPA + marketing Next).`);

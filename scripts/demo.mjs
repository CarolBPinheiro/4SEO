/**
 * Sobe o sandbox local: API (8000), app autenticado (8080) e marketing (3000).
 *
 * Pré-requisito: DEMO_MODE=true no backend/.env e `npm run demo:seed`.
 * Encerrar com Ctrl+C mata os três processos.
 */
import { spawn } from "child_process";
import { existsSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const isWin = process.platform === "win32";
const python = isWin
  ? join(ROOT, "backend", ".venv", "Scripts", "python.exe")
  : join(ROOT, "backend", ".venv", "bin", "python");
const npmCmd = isWin ? "npm.cmd" : "npm";

if (!existsSync(python)) {
  console.error(
    `Python do venv não encontrado: ${python}\nCrie o venv em backend/.venv antes de npm run demo.`,
  );
  process.exit(1);
}

/** @type {import("child_process").ChildProcess[]} */
const children = [];
let shuttingDown = false;

function spawnLogged(label, command, args, cwd) {
  const child = spawn(command, args, {
    cwd,
    env: process.env,
    stdio: "inherit",
    windowsHide: true,
  });
  child.on("exit", (code, signal) => {
    if (shuttingDown) {
      return;
    }
    const reason = signal ? `sinal ${signal}` : `código ${code}`;
    console.error(`[${label}] encerrou (${reason}). Encerrando o sandbox.`);
    shutdown(code && code !== 0 ? code : 1);
  });
  child.on("error", (err) => {
    console.error(`[${label}] falhou ao iniciar:`, err.message);
    shutdown(1);
  });
  children.push(child);
}

function shutdown(code = 0) {
  if (shuttingDown) {
    return;
  }
  shuttingDown = true;
  for (const child of children) {
    if (!child.killed && child.pid) {
      child.kill("SIGTERM");
    }
  }
  windowCloseFallback();
  process.exit(code);
}

function windowCloseFallback() {
  if (!isWin) {
    return;
  }
  for (const child of children) {
    if (child.pid && !child.killed) {
      spawn("taskkill", ["/pid", String(child.pid), "/t", "/f"], {
        stdio: "ignore",
        windowsHide: true,
      });
    }
  }
}

process.on("SIGINT", () => shutdown(0));
process.on("SIGTERM", () => shutdown(0));

console.log("4SEO demo sandbox");
console.log("  Marketing  http://localhost:3000");
console.log("  App        http://localhost:8080/login");
console.log("  API        http://localhost:8000/docs");
console.log("Ctrl+C para encerrar.\n");

spawnLogged("api", python, ["-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"], join(ROOT, "backend"));
spawnLogged("app", npmCmd, ["run", "dev:app"], ROOT);
spawnLogged("marketing", npmCmd, ["run", "dev:marketing"], ROOT);

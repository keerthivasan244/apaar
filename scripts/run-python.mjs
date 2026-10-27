// Run a Python module inside backend/ with the project's virtual environment (created by `npm run dev`).
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const python = process.platform === "win32" ? join(root, ".venv", "Scripts", "python.exe") : join(root, ".venv", "bin", "python");
if (!existsSync(python)) {
  console.error("No .venv yet. Run `npm run dev` once to set everything up.");
  process.exit(1);
}
const r = spawnSync(python, process.argv.slice(2), { cwd: join(root, "backend"), stdio: "inherit" });
process.exit(r.status ?? 1);

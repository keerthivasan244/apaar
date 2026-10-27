// `npm run dev`: one-time setup if needed, then backend (:8000) and frontend (:5173) together.
// No dependencies beyond Node itself, so it works straight after cloning.
import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const isWin = process.platform === "win32";
const venv = join(root, ".venv");
const venvPython = isWin ? join(venv, "Scripts", "python.exe") : join(venv, "bin", "python");
const npm = isWin ? "npm.cmd" : "npm";

function run(cmd, args, cwd = root) {
  const r = spawnSync(cmd, args, { cwd, stdio: "inherit", shell: isWin });
  if (r.status !== 0) {
    console.error(`\nCommand failed: ${cmd} ${args.join(" ")}`);
    process.exit(r.status ?? 1);
  }
}

function findSystemPython() {
  for (const cmd of isWin ? ["py", "python", "python3"] : ["python3", "python"]) {
    const args = cmd === "py" ? ["-3", "--version"] : ["--version"];
    const r = spawnSync(cmd, args, { encoding: "utf8", shell: isWin });
    const m = /Python (\d+)\.(\d+)/.exec((r.stdout || "") + (r.stderr || ""));
    if (r.status === 0 && m && (Number(m[1]) > 3 || (Number(m[1]) === 3 && Number(m[2]) >= 11))) {
      return cmd === "py" ? ["py", "-3"] : [cmd];
    }
  }
  console.error("Python 3.11 or newer is required. Install it from https://www.python.org/downloads/ and try again.");
  process.exit(1);
}

// 1. Python virtual environment + backend packages
if (!existsSync(venvPython)) {
  const [py, ...pyArgs] = findSystemPython();
  console.log("Creating Python virtual environment in .venv ...");
  run(py, [...pyArgs, "-m", "venv", venv]);
  console.log("Installing backend packages ...");
  run(venvPython, ["-m", "pip", "install", "-r", join("backend", "requirements.txt")]);
}

// 2. Frontend packages
if (!existsSync(join(root, "frontend", "node_modules"))) {
  console.log("Installing frontend packages ...");
  run(npm, ["ci"], join(root, "frontend"));
}

// 3. Start both servers. The backend seeds the demo database on first start.
console.log("\nBackend:  http://localhost:8000/api/v1/docs");
console.log("Frontend: http://localhost:5173   (open this one)\n");

const children = [
  spawn(venvPython, ["-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"], {
    cwd: join(root, "backend"),
    stdio: "inherit",
    env: { ...process.env, DEV_CORS: "true" },
    detached: !isWin, // own process group, so the whole tree can be stopped together
  }),
  spawn(npm, ["run", "dev"], { cwd: join(root, "frontend"), stdio: "inherit", shell: isWin, detached: !isWin }),
];

function killTree(child) {
  if (child.exitCode !== null) return;
  try {
    if (isWin) spawnSync("taskkill", ["/pid", String(child.pid), "/T", "/F"], { stdio: "ignore" });
    else process.kill(-child.pid, "SIGTERM");
  } catch {
    /* already gone */
  }
}

let stopping = false;
function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  children.forEach(killTree);
  setTimeout(() => process.exit(code), 500);
}
process.on("SIGINT", () => stop(0));
process.on("SIGTERM", () => stop(0));
for (const c of children) c.on("exit", (code) => stop(code ?? 0));

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

// The Windows shell splits on spaces, so quote anything that contains one (e.g. C:\Users\First Last\...).
const q = (s) => (isWin && s.includes(" ") && !s.startsWith('"') ? `"${s}"` : s);

function run(cmd, args, cwd = root) {
  const r = spawnSync(q(cmd), args.map(q), { cwd, stdio: "inherit", shell: isWin });
  if (r.status !== 0) {
    console.error(`\nCommand failed: ${cmd} ${args.join(" ")}`);
    process.exit(r.status ?? 1);
  }
}

const MINOR_VERSIONS = [14, 13, 12, 11];

/** Every way Python is commonly reachable, newest first. `PYTHON` env var wins if set. */
function pythonCandidates() {
  const list = [];
  const fromEnv = (process.env.PYTHON || "").trim().replace(/^"|"$/g, "");
  if (fromEnv) list.push([fromEnv]);
  if (isWin) {
    for (const m of MINOR_VERSIONS) list.push(["py", `-3.${m}`]);
    list.push(["py", "-3"], ["python"], ["python3"]);
    const bases = [process.env.LOCALAPPDATA && join(process.env.LOCALAPPDATA, "Programs", "Python"), process.env.ProgramFiles, "C:\\"];
    for (const base of bases.filter(Boolean)) {
      for (const m of MINOR_VERSIONS) list.push([join(base, `Python3${m}`, "python.exe")]);
    }
  } else {
    for (const m of MINOR_VERSIONS) list.push([`python3.${m}`]);
    list.push(["python3"], ["python"]);
    for (const m of MINOR_VERSIONS) {
      list.push([`/opt/homebrew/bin/python3.${m}`], [`/usr/local/bin/python3.${m}`],
        [`/Library/Frameworks/Python.framework/Versions/3.${m}/bin/python3`]);
    }
  }
  return list;
}

function findSystemPython() {
  const seen = [];
  for (const [cmd, ...pre] of pythonCandidates()) {
    if ((cmd.includes("/") || cmd.includes("\\")) && !existsSync(cmd)) continue;
    // Quote absolute paths for the Windows shell (they may contain spaces).
    const exe = isWin && cmd.includes("\\") ? `"${cmd}"` : cmd;
    const r = spawnSync(exe, [...pre, "--version"], { encoding: "utf8", shell: isWin });
    const out = ((r.stdout || "") + (r.stderr || "")).trim();
    const m = /Python (\d+)\.(\d+)/.exec(out);
    if (r.status === 0 && m) {
      if (Number(m[1]) > 3 || (Number(m[1]) === 3 && Number(m[2]) >= 11)) return [exe, ...pre];
      seen.push(`  ${[cmd, ...pre].join(" ")} -> ${out} (too old)`);
    }
  }
  console.error("Python 3.11 or newer is required but was not found.");
  if (seen.length) console.error("Found only:\n" + [...new Set(seen)].join("\n"));
  else console.error("No Python found on PATH. On Windows, re-run the installer and tick \"Add python.exe to PATH\".");
  console.error("Install it from https://www.python.org/downloads/ or point to it directly, e.g.:");
  if (isWin) {
    console.error('  PowerShell:  $env:PYTHON="C:\\path\\to\\python.exe"; npm run dev');
    console.error('  cmd:         set "PYTHON=C:\\path\\to\\python.exe" && npm run dev');
  } else {
    console.error("  PYTHON=/path/to/python3.12 npm run dev");
  }
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

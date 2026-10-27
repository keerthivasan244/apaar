// `npm run dev`: one-time setup if needed, then backend (:8000) and frontend (:5173) together.
// No dependencies beyond Node itself, so it works straight after cloning.
import { spawn, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, lstatSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { join, dirname, isAbsolute } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const isWin = process.platform === "win32";
const venv = join(root, ".venv");
const venvPython = isWin ? join(venv, "Scripts", "python.exe") : join(venv, "bin", "python");
const requirements = join(root, "backend", "requirements.txt");
const installedMarker = join(venv, ".requirements-installed");
const npm = isWin ? "npm.cmd" : "npm";
const MIN = [3, 11];
const MINOR_VERSIONS = [14, 13, 12, 11];

// The Windows shell splits on spaces, so quote anything that contains one (e.g. C:\Users\First Last\...).
const q = (s) => (isWin && s.includes(" ") && !s.startsWith('"') ? `"${s}"` : s);

function run(cmd, args, cwd = root) {
  const r = spawnSync(q(cmd), args.map(q), { cwd, stdio: "inherit", shell: isWin });
  if (r.status !== 0) {
    console.error(`\nCommand failed: ${cmd} ${args.join(" ")}`);
    process.exit(r.status ?? 1);
  }
}

/** Ask the interpreter itself for its version; returns [major, minor] or null if it does not run. */
function pythonVersion(cmd, preArgs = []) {
  const r = spawnSync(q(cmd), [...preArgs, "-c", "import sys; print(*sys.version_info[:2], sep='.')"], {
    encoding: "utf8",
    shell: isWin,
  });
  const m = r.status === 0 && /^(\d+)\.(\d+)\s*$/.exec(r.stdout || "");
  return m ? [Number(m[1]), Number(m[2])] : null;
}

const supported = (v) => v && (v[0] > MIN[0] || (v[0] === MIN[0] && v[1] >= MIN[1]));
const fmt = (v) => v.join(".");

/** Every way Python is commonly reachable, explicit installs first. `PYTHON` env var wins if set. */
function pythonCandidates() {
  const list = [];
  const fromEnv = (process.env.PYTHON || "").trim().replace(/^"|"$/g, "");
  if (fromEnv) list.push([fromEnv]);
  if (isWin) {
    for (const m of MINOR_VERSIONS) list.push(["py", `-3.${m}`]);
    list.push(["py", "-3"]);
    const bases = [process.env.LOCALAPPDATA && join(process.env.LOCALAPPDATA, "Programs", "Python"), process.env.ProgramFiles, "C:\\"];
    for (const base of bases.filter(Boolean)) {
      for (const m of MINOR_VERSIONS) list.push([join(base, `Python3${m}`, "python.exe")]);
    }
  } else {
    // Homebrew (Intel: /usr/local, Apple Silicon: /opt/homebrew) and python.org installers.
    // Homebrew's versioned formulae live under opt/python@3.X even when not linked onto PATH.
    for (const m of MINOR_VERSIONS) {
      list.push(
        [`/usr/local/opt/python@3.${m}/bin/python3.${m}`],
        [`/opt/homebrew/opt/python@3.${m}/bin/python3.${m}`],
        [`/Library/Frameworks/Python.framework/Versions/3.${m}/bin/python3.${m}`],
        [`/usr/local/bin/python3.${m}`],
        [`/opt/homebrew/bin/python3.${m}`],
        [`python3.${m}`],
      );
    }
  }
  list.push(["python3"], ["python"]);
  return list;
}

function findSystemPython() {
  const tooOld = [];
  for (const [cmd, ...pre] of pythonCandidates()) {
    if (isAbsolute(cmd) && !existsSync(cmd)) continue;
    const v = pythonVersion(cmd, pre);
    if (!v) continue;
    const label = [cmd, ...pre].join(" ");
    if (supported(v)) {
      console.log(`Using Python ${fmt(v)}: ${label}`);
      return [cmd, ...pre];
    }
    tooOld.push(`  ${label} -> Python ${fmt(v)} (too old)`);
  }
  console.error(`Python ${fmt(MIN)} or newer is required but was not found.`);
  if (tooOld.length) console.error("Found only:\n" + [...new Set(tooOld)].join("\n"));
  else console.error("No Python found. On Windows, re-run the installer and tick \"Add python.exe to PATH\".");
  console.error("Install it from https://www.python.org/downloads/ or point to it directly, e.g.:");
  if (isWin) {
    console.error('  PowerShell:  $env:PYTHON="C:\\path\\to\\python.exe"; npm run dev');
    console.error('  cmd:         set "PYTHON=C:\\path\\to\\python.exe" && npm run dev');
  } else {
    console.error("  PYTHON=/usr/local/opt/python@3.13/bin/python3.13 npm run dev");
  }
  process.exit(1);
}

// Entries a generated virtual environment may contain. Anything else means it is not safe to delete.
const VENV_ENTRIES = new Set(["bin", "Scripts", "lib", "Lib", "lib64", "include", "Include", "share", "etc",
  "pyvenv.cfg", ".gitignore", ".requirements-installed"]);

function venvConfigVersion() {
  try {
    const m = /^version(?:_info)?\s*=\s*(\S+)/m.exec(readFileSync(join(venv, "pyvenv.cfg"), "utf8"));
    return m ? m[1] : "unknown";
  } catch {
    return "unknown";
  }
}

/** Remove .venv only after confirming it is a generated virtual environment (never project data). */
function removeVenvSafely(reason) {
  const stat = lstatSync(venv);
  const entries = stat.isDirectory() ? readdirSync(venv) : [];
  const unexpected = entries.filter((e) => !VENV_ENTRIES.has(e));
  if (!stat.isDirectory() || stat.isSymbolicLink() || !entries.includes("pyvenv.cfg") || unexpected.length) {
    console.error(`\n.venv needs to be rebuilt (${reason}), but it does not look like a plain virtual environment`);
    if (unexpected.length) console.error(`(unexpected contents: ${unexpected.join(", ")}).`);
    console.error("Move anything you need out of .venv, delete the folder, and run `npm run dev` again.");
    process.exit(1);
  }
  console.log(`Removing the old .venv (${reason}) ...`);
  rmSync(venv, { recursive: true, force: true });
}

// 1. Python virtual environment: reuse it only if its interpreter runs and is new enough.
if (existsSync(venv)) {
  const v = pythonVersion(venvPython);
  if (!supported(v)) {
    removeVenvSafely(v ? `it uses Python ${fmt(v)}` : `its Python ${venvConfigVersion()} no longer runs`);
  }
}
if (!existsSync(venv)) {
  const [py, ...pyArgs] = findSystemPython();
  console.log("Creating Python virtual environment in .venv ...");
  run(py, [...pyArgs, "-m", "venv", venv]);
  if (!supported(pythonVersion(venvPython))) {
    console.error("The new .venv does not work. Delete the .venv folder and try again.");
    process.exit(1);
  }
}

// 2. Backend packages, installed with the venv's own Python. Reinstalled only when requirements.txt
//    or the venv's Python changes (or a previous install did not finish).
const wanted = createHash("sha256")
  .update(readFileSync(requirements))
  .update(fmt(pythonVersion(venvPython)))
  .digest("hex");
let installed = "";
try {
  installed = readFileSync(installedMarker, "utf8").trim();
} catch {
  /* first install */
}
if (installed !== wanted) {
  console.log("Installing backend packages into .venv ...");
  run(venvPython, ["-m", "pip", "install", "-r", requirements]);
  writeFileSync(installedMarker, wanted + "\n");
}

// 3. Frontend packages
if (!existsSync(join(root, "frontend", "node_modules"))) {
  console.log("Installing frontend packages ...");
  run(npm, ["ci"], join(root, "frontend"));
}

// 4. Start both servers. The backend seeds the demo database on first start.
console.log("\nBackend:  http://localhost:8000/api/v1/docs");
console.log("Frontend: http://localhost:5173   (open this one)\n");

// stdin is ignored: the servers run in their own process groups (so the whole tree can be stopped
// together), and a background process group that reads the terminal would be suspended.
const stdio = ["ignore", "inherit", "inherit"];
const children = [
  spawn(venvPython, ["-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"], {
    cwd: join(root, "backend"),
    stdio,
    env: { ...process.env, DEV_CORS: "true" },
    detached: !isWin,
  }),
  spawn(npm, ["run", "dev"], { cwd: join(root, "frontend"), stdio, shell: isWin, detached: !isWin }),
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

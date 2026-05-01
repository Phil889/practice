#!/usr/bin/env node
/* eslint-disable no-console */

/**
 * practice — one-liner installer for Claude Code projects.
 *
 * Usage:
 *   npx github:Phil889/practice init
 *   npx github:Phil889/practice init --with-karpathy
 *   npx github:Phil889/practice init --with-playwriter
 *   npx github:Phil889/practice init --all
 *
 * What it does:
 *   1. Sanity-checks the working directory (git repo, Claude Code-ish).
 *   2. Copies the harness into .practice/ and runs install.sh.
 *   3. Optionally installs the Karpathy guidelines skill into ~/.claude/plugins/.
 *   4. Optionally installs Playwriter (npm -g) and triggers `playwriter install`.
 *   5. Prints next-step guidance: open Claude Code and run /init.
 */

const { execSync, spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const HARNESS_REPO = 'https://github.com/Phil889/practice.git';
const KARPATHY_REPO = 'https://github.com/forrestchang/andrej-karpathy-skills.git';

const args = process.argv.slice(2);
const cmd = args[0];
const flags = new Set(args.slice(1));

const want = {
  karpathy: flags.has('--with-karpathy') || flags.has('--all'),
  playwriter: flags.has('--with-playwriter') || flags.has('--all'),
  upgrade: flags.has('--upgrade'),
};

function log(line) {
  console.log(line);
}

function fail(msg, code = 1) {
  console.error(`✗ ${msg}`);
  process.exit(code);
}

function run(command, opts = {}) {
  return execSync(command, { stdio: 'inherit', ...opts });
}

function tryRun(command, opts = {}) {
  const r = spawnSync(command, { stdio: 'inherit', shell: true, ...opts });
  return r.status === 0;
}

function which(bin) {
  const probe = process.platform === 'win32' ? `where ${bin}` : `command -v ${bin}`;
  try {
    execSync(probe, { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

function printHelp() {
  log(`
practice — install the audit-grade AI specialist harness for Claude Code.

USAGE
  npx github:Phil889/practice <command> [flags]

COMMANDS
  init              Install the harness in the current directory
  doctor            Diagnose existing install + companion tools
  help              Show this message

FLAGS (for init)
  --with-karpathy   Also install the Karpathy guidelines skill
                    (github.com/forrestchang/andrej-karpathy-skills)
  --with-playwriter Also install Playwriter, the browser bridge used by
                    the tester agent (github.com/remorses/playwriter)
  --all             Both of the above
  --upgrade         Overwrite existing .claude/skills/init/SKILL.md and templates

EXAMPLES
  npx github:Phil889/practice init
  npx github:Phil889/practice init --all
  npx github:Phil889/practice doctor
`);
}

function ensureGitRepo() {
  if (!fs.existsSync('.git')) {
    fail('Not a git repository. practice requires a git project. Run `git init` first.');
  }
}

function ensureNotInsideHarness() {
  // If you accidentally `npx`'d inside a freshly-cloned practice repo, refuse.
  if (fs.existsSync('install.sh') && fs.existsSync('templates') && fs.existsSync('.claude/skills/init')) {
    fail('You appear to be inside the practice repo itself. Run this from your TARGET project root.');
  }
}

function cloneHarness() {
  const cacheDir = path.resolve('.practice');
  if (fs.existsSync(cacheDir) && !want.upgrade) {
    log('• .practice/ already exists. Reusing it (pass --upgrade to refresh).');
    return cacheDir;
  }
  if (fs.existsSync(cacheDir) && want.upgrade) {
    log('• --upgrade: removing existing .practice/ before re-clone.');
    fs.rmSync(cacheDir, { recursive: true, force: true });
  }
  log(`→ cloning ${HARNESS_REPO} into .practice/ ...`);
  run(`git clone --depth=1 ${HARNESS_REPO} .practice`);
  // Drop the .git so .practice doesn't show up as a submodule
  fs.rmSync(path.join(cacheDir, '.git'), { recursive: true, force: true });
  return cacheDir;
}

function runInstaller(cacheDir) {
  const installer = path.join(cacheDir, 'install.sh');
  if (!fs.existsSync(installer)) {
    fail(`Installer not found at ${installer}. The clone may be corrupt — re-run with --upgrade.`);
  }
  log('→ running .practice/install.sh ...');
  // chmod for non-Windows
  if (process.platform !== 'win32') {
    try { fs.chmodSync(installer, 0o755); } catch { /* ignore */ }
  }
  const useBash = process.platform === 'win32';
  const ok = tryRun(useBash ? `bash "${installer}" ${want.upgrade ? '--upgrade' : ''}` : `"${installer}" ${want.upgrade ? '--upgrade' : ''}`);
  if (!ok) {
    fail('install.sh failed. Re-run manually: bash .practice/install.sh');
  }
}

function installKarpathy() {
  if (!want.karpathy) return;
  log('\n→ installing Karpathy guidelines skill ...');
  const dest = path.join(os.homedir(), '.claude', 'plugins', 'andrej-karpathy-skills');
  if (fs.existsSync(dest)) {
    log(`• already present at ${dest} — skipping.`);
    return;
  }
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  if (!tryRun(`git clone --depth=1 ${KARPATHY_REPO} "${dest}"`)) {
    log('⚠ Karpathy install failed. Manual: git clone ' + KARPATHY_REPO + ' ' + dest);
    return;
  }
  log(`✓ Karpathy skill installed → ${dest}`);
  log('  Trigger in Claude Code with: /karpathy-guidelines');
}

function installPlaywriter() {
  if (!want.playwriter) return;
  log('\n→ installing Playwriter (browser bridge for render-layer UAT) ...');
  if (!which('npm')) {
    log('⚠ npm not found on PATH. Install Node.js first, then: npm install -g playwriter');
    return;
  }
  if (which('playwriter')) {
    log('• playwriter already on PATH — skipping npm install.');
  } else {
    if (!tryRun('npm install -g playwriter')) {
      log('⚠ npm install -g playwriter failed (permissions? try sudo or use a Node version manager).');
      return;
    }
  }
  log('✓ playwriter installed.');
  log('  Next: run `playwriter install` to install the Chrome extension,');
  log('         then `playwriter skill` to print the up-to-date skill spec for Claude Code.');
  log('  Docs: https://playwriter.dev/  ·  https://github.com/remorses/playwriter');
}

function postInstallSummary() {
  log(`
────────────────────────────────────────────────────────────────────────
practice installed.

Next step — in Claude Code, in your project root, run:

    > /init

That will read your project, ask 5–7 targeted questions, propose a
tailored specialist team, scaffold the harness, and run a smoke test.

Companion tools:
  ${want.karpathy ? '✓' : '·'} Karpathy guidelines      (skill — discipline for the implementer)
  ${want.playwriter ? '✓' : '·'} Playwriter              (browser bridge for tester / uat-sweep)

To install a missing companion later:
  npx github:Phil889/practice init --with-karpathy
  npx github:Phil889/practice init --with-playwriter

For a re-tune later:           /init mode: replan
For a snapshot any time:       /supervisor mode: snapshot
For full diagnostics:          npx github:Phil889/practice doctor
────────────────────────────────────────────────────────────────────────
`);
}

function doctor() {
  log('practice doctor — checking install + companion tools\n');

  const checks = [
    ['git repo present', () => fs.existsSync('.git')],
    ['.practice/ cache present', () => fs.existsSync('.practice')],
    ['.claude/skills/init/SKILL.md present', () => fs.existsSync('.claude/skills/init/SKILL.md')],
    ['.claude/skills/audit-orchestrator/SKILL.md present', () => fs.existsSync('.claude/skills/audit-orchestrator/SKILL.md')],
    ['.claude/skills/build-loop/SKILL.md present', () => fs.existsSync('.claude/skills/build-loop/SKILL.md')],
    ['.claude/skills/supervisor/SKILL.md present', () => fs.existsSync('.claude/skills/supervisor/SKILL.md')],
    ['.planning/audits/SESSION-LOG.md present', () => fs.existsSync('.planning/audits/SESSION-LOG.md')],
    ['Karpathy skill installed', () => fs.existsSync(path.join(os.homedir(), '.claude', 'plugins', 'andrej-karpathy-skills'))],
    ['playwriter on PATH', () => which('playwriter')],
  ];

  let bad = 0;
  for (const [label, fn] of checks) {
    let ok = false;
    try { ok = !!fn(); } catch { ok = false; }
    log(`  ${ok ? '✓' : '✗'} ${label}`);
    if (!ok) bad++;
  }
  log('');
  if (bad === 0) {
    log('All checks passed. The harness is wired up.');
  } else {
    log(`${bad} check(s) failed. Run \`npx github:Phil889/practice init --all\` to fix.`);
  }
}

function main() {
  if (!cmd || cmd === 'help' || cmd === '--help' || cmd === '-h') {
    printHelp();
    return;
  }

  if (cmd === 'doctor') {
    doctor();
    return;
  }

  if (cmd !== 'init') {
    fail(`Unknown command: ${cmd}. Run \`npx github:Phil889/practice help\` for usage.`);
  }

  ensureGitRepo();
  ensureNotInsideHarness();

  log('practice installer\n');
  const cacheDir = cloneHarness();
  runInstaller(cacheDir);
  installKarpathy();
  installPlaywriter();
  postInstallSummary();
}

try {
  main();
} catch (err) {
  fail(err.message || String(err));
}

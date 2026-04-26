# Troubleshooting

Common issues and their fixes.

---

## Install issues

### `✗ Not a git repository`

**Cause:** practice requires `.git/` in the project root. The harness uses git for atomic commits, audit trail, and revert paths.

**Fix:**
```bash
git init
git add -A
git commit -m "chore: initial commit"
./install.sh
```

### `✗ Cannot install practice into itself`

**Cause:** you ran `./install.sh` from inside the `practice` repo. The script refuses to install practice into its own source.

**Fix:** `cd` to your target project's root, then run `path/to/practice/install.sh` from there.

### `⚠ Existing practice install detected`

**Cause:** `.claude/skills/init/` already exists from a prior install.

**Fix:**
- To **upgrade** to a newer practice version while keeping your generated agents: `./install.sh --upgrade`
- To **re-tune** your specialist team without overwriting templates: in Claude Code, run `/init mode: replan`
- To **rebuild from scratch**: `/init mode: fresh` (asks for explicit confirmation before destruction)

---

## `/init` issues

### `/init` doesn't appear in Claude Code's slash-command list

**Cause:** Claude Code didn't pick up the new skill. Usually a stale session.

**Fix:** restart Claude Code. The skill loads from `.claude/skills/init/SKILL.md` on session start.

### `/init` fails at Phase 4 with "template not found"

**Cause:** `.practice/templates/` is missing or incomplete (install was interrupted).

**Fix:** re-run `./install.sh --upgrade` from the practice repo to restore templates.

### `/init` proposes specialists that don't fit my domain

**Cause:** Phase 1's domain inference picked the wrong bucket. The pause-points exist precisely so you can catch this.

**Fix:** at the Phase 3 (Team design) pause, tell the bootstrapper: "drop X, add Y named Z with scope ABC". The init skill can edit the team proposal before generating files. If you've already run past Phase 3, re-run `/init mode: replan` to regenerate without overwriting work.

---

## Audit-orchestrator issues

### Specialists return without filing reports

**Cause:** specialist hit a quality-bar violation mid-run and aborted, OR the dispatch prompt was missing required reading paths.

**Fix:**
1. Check `.planning/audits/<specialist>/` — was the file written but incomplete?
2. Check the orchestrator's plan file — was the dispatch prompt missing the `_context/quality-bar.md` reading?
3. Re-dispatch with explicit prompt: `Agent({subagent_type: "<specialist>", prompt: "scope: <X>. Mandatory reading: .planning/audits/_context/SUMMARY.md + .planning/audits/_context/quality-bar.md. ..."})`

### `audit-verifier` returns FAIL on every run

**Cause:** quality bar is too strict for your specialists' current calibration, OR specialists aren't reading the quality bar.

**Fix:**
1. Check that every specialist dispatch prompt includes `Mandatory reading: .planning/audits/_context/quality-bar.md`. If it doesn't, the orchestrator's dispatch templates need fixing.
2. If the quality bar is genuinely too strict for v0 of your harness, edit `.planning/audits/_context/quality-bar.md` — but **only loosen rules with reasons documented in an HSI entry.** Silent loosening defeats the audit-trail.

### `verify_audit.py` reports "broken citations"

**Cause:** specialist cited a `file:line` that doesn't resolve — usually because the file moved between when the audit ran and when verifier ran.

**Fix:** if rare (1–2 per run), the verifier's WARN is correct and the specialist should re-cite. If frequent, run `python .planning/audits/_context/refresh.py` before audits — stale inventory produces stale citations.

---

## Build-loop issues

### `STOP. Working tree is dirty.`

**Cause:** uncommitted changes would tangle with the build-loop's atomic commits.

**Fix:**
```bash
git status                    # see what's uncommitted
git stash                     # if you want to keep them for later
git commit -am "wip"          # if you're ready to commit them
```
Then re-run the build-loop.

### `STOP. Working tree drift detected.`

**Cause:** the implementer noticed files in `git status` it didn't author this session — usually means a parallel implementer's worktree leaked, OR you have stale uncommitted work.

**Fix:** the implementer is being conservative — that's correct behaviour. Investigate which files appeared. If they're from a prior session you forgot about, commit or stash them. If they're from a parallel implementer, the build-loop's worktree-isolation should have prevented this — file an HSI to investigate.

### Implementer commits the wrong files

**Cause:** `git add` was called against a directory or `-A` instead of specific paths. The implementer template forbids this; if it happened, the implementer agent skipped the rule.

**Fix:**
1. `git reset HEAD~1` to undo the last commit (keeps changes)
2. Stage only the intended files: `git add path/to/file1 path/to/file2`
3. Re-commit with the correct convention message
4. File an HSI: the implementer needs a stronger prompt to prevent this recurrence.

### Tester returns FAIL but the fix looks right

**Cause:** the `verifiable_outcome` probe in the brief was wrong, OR the fix is incomplete.

**Fix:** read the tester's `### Failure delta` section in the status file. It quotes the actual probe result vs the expected GREEN state. If the probe was wrong, edit the brief and re-run; if the fix is incomplete, re-dispatch implementer with the delta.

---

## Supervisor issues

### Supervisor declares GREEN when something obviously broke

**Cause:** load-bearing claim wasn't probed. The supervisor's Step 2 picks 3–5 highest-stakes claims; if your concern wasn't in that set, it didn't get re-verified.

**Fix:** invoke `/supervisor mode: talk: <specific question about the broken thing>`. The conversational mode runs the probe you care about and includes it in the answer.

### `mode: hygiene` archives something I needed active

**Cause:** the hygiene policy thought the artefact was safe to archive (PASS + 30 days, etc.), but you have an open dependency the policy didn't see.

**Fix:**
1. Recover from `_archive/<category>/<period>/`. Hygiene never deletes — only moves.
2. Update the index file (`SYSTEM-CHANGELOG-INDEX.md` or `_findings-status/INDEX.md`) to add a manual "RETAINED" flag on the entry. The hygiene policy honours `RETAINED` flags.
3. If you want this preserved for future projects, file an HSI: the hygiene policy should add a new "retain when X" rule.

### Supervisor refuses to run `mode: snapshot` ("hard cap exceeded")

**Cause:** one of the artefact categories blew past its hard cap. Supervisor is in protective mode.

**Fix:** `/supervisor mode: hygiene`. After the hygiene run completes, snapshot will work again.

---

## Workflow issues

### Workflow fails at Phase 2 / 3 / 4

**Cause:** an earlier phase produced a verdict that the workflow's gating logic correctly STOPped on.

**Fix:** read the workflow's report — it will name the specific blocker and the remediation playbook. Workflows are designed to fail-loud, not fail-silent.

### Workflow runs forever / appears hung

**Cause:** a dispatched agent is waiting on input the orchestrator should have provided in the prompt.

**Fix:**
1. Cancel the workflow.
2. Check `.planning/audits/_context/SUMMARY.md` — is it stale? Run `python .planning/audits/_context/refresh.py`.
3. Check the workflow's plan file — does the dispatch prompt include all required reading paths?
4. Re-run the workflow.

---

## Convention compliance issues

### `git push` blocked by `mode: pre-push` with "convention compliance <80%"

**Cause:** at least 20% of unpushed commits are missing structured fields (`audit:`, `roadmap:`, `finding:`, etc.). The supervisor's pre-push gate refuses to push because the audit-trail integrity is broken.

**Fix:**
1. Run `git log origin/<branch>..HEAD --format=%B` to see all unpushed commit messages.
2. For each non-compliant commit: either rewrite (interactive rebase + amend) or, if you can't safely rewrite, create a follow-up commit with a `docs(audit-trail): retro-document <sha>` body that adds the missing fields. The supervisor accepts retro-documents on the next pre-push pass.
3. Re-run `/supervisor mode: pre-push`.

### Bot commits (Dependabot, etc.) are flagged as non-compliant

**Cause:** the supervisor's compliance scan didn't filter bot commits.

**Fix:** edit `.claude/skills/supervisor/SKILL.md` Step 3 to skip authors matching `dependabot` / `renovate` / your bot name. The exemption is in the spec; the skill just needs the filter list updated.

---

## When to file an HSI vs a bug report

- **HSI** — when the harness has a structural pattern that produced the issue (e.g., the same B-pattern keeps slipping through qa-engineer; the same workflow phase keeps timing out). Propose a hypothesis and verification probe.
- **Bug report** — when the issue is a one-off in your project (e.g., your specific `refresh.py` regex doesn't match your project's filename pattern). File against the practice repo if it's a generic issue.

When in doubt: file an HSI. They're cheap; if the supervisor refutes them in 2 weeks, no harm. **The compounding only happens if the lessons are captured.**

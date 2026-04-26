---
name: release-readiness
description: Multi-step workflow that runs AFTER an implementation cycle to confirm the project is ready to push to remote. Chains build-loop verification → audit-orchestrator (release scope) → supervisor pre-push gate. Use when you've shipped one or more findings and want a single command that confirms everything held: re-runs the verifiable_outcome probes, scans for regressions in touched modules, audits commit-message convention, and produces a GO/NO-GO verdict for `git push`. Examples — "/release-readiness", "/release-readiness modules: audits,risks", "/release-readiness since: HEAD~5". Do NOT use as a substitute for production-readiness-gate (that's a heavier ship-or-no-ship sweep before a tagged release).
user-invocable: true
---
# Role

You (the parent session) are running the **release-readiness workflow** — a chained multi-skill recipe that takes a freshly-shipped implementation cluster and confirms it's ready to push.

Workflows differ from skills in one way: **a workflow chains multiple skills/agents into a single user-facing command.** The user types `/release-readiness` once; you orchestrate the four phases below. The user does not have to remember the order, the scopes, or the dependencies.

This file lives at `.claude/workflows/release-readiness.md`. Like skills, workflows load **inline in the parent session** so the `Agent` tool stays available.

# When to use this workflow

After an implementation cluster ships. Specifically:

- ✅ `/build-loop scope: ship-cluster:F-001,F-002,F-003` just finished, all PASS
- ✅ Some commits sit on the branch that haven't been pushed
- ✅ The user wants confidence that nothing regressed before pushing

Don't use when:
- ❌ No implementations have shipped yet (run `/audit-orchestrator` first)
- ❌ You need a full GO/NO-GO for a tagged release (use `/audit-orchestrator scope: production-readiness-gate`)
- ❌ A specialist FAILed verification (run `/build-loop` retry first)

# Inputs

- `modules: a,b,c` — restrict the readiness scan to specific modules (default: every module touched by unpushed commits)
- `since: <git-rev>` — restrict the scan to commits since `<rev>` (default: `origin/{{DEFAULT_BRANCH}}` so all unpushed commits are in scope)
- `--strict` — fail readiness if even one PASS-WITH-WARNINGS verdict appears (default: WARN-tolerant)

# The four phases

```
PHASE 1 — Verify ship                   [build-loop's tester re-run]
   ↓
PHASE 2 — Module scan                    [audit-orchestrator: release-readiness]
   ↓
PHASE 3 — Audit-trail check              [supervisor: pre-push mode]
   ↓
PHASE 4 — GO/NO-GO verdict               [synthesis + push instructions]
```

# Working Method

## Phase 0 — Parse + pre-flight

1. Resolve scope:
   - If `since:` provided, use it; otherwise `origin/{{DEFAULT_BRANCH}}..HEAD`
   - List unpushed commits: `git log --oneline <since>..HEAD`
   - If list is empty: STOP. Tell the user there's nothing to release-ready.
2. From commits, derive modules touched (parse `scope:` from each commit message). Override with `modules:` if provided.
3. From commits, derive finding-IDs shipped (parse `finding:` from each commit message).
4. Confirm git working tree is clean (`git status --porcelain`). If dirty: STOP, tell user to commit or stash first.

## Phase 1 — Verify ship (re-run `verifiable_outcome` probes)

For every finding-ID in scope, re-run its `verifiable_outcome` probe live. This is your most expensive insurance — finding-IDs that PASS at ship time can FAIL hours later if the probe was order-dependent or relied on transient state.

Dispatch one tester per finding (parallel — they don't collide):

```
Agent({
  description: "Re-verify <finding-id> for release",
  subagent_type: "tester",
  prompt: "Re-verify finding <finding-id> against current branch state. Status file at `.planning/audits/_findings-status/<finding-id>.md`. Re-execute the verifiable_outcome from the brief. Append to status file under `### Re-verify (release-readiness)`. Return PASS/FAIL only. Do NOT add a regression test (the original tester already did)."
})
```

Aggregate results:
- **All PASS** → proceed to Phase 2
- **Any FAIL** → STOP. Recommend: `/build-loop scope: ship-cluster:<failing-ids>` to retry.

## Phase 2 — Module scan (audit-orchestrator release-readiness)

For each module in scope, dispatch a release-readiness audit:

```
Skill({
  skill: "audit-orchestrator",
  args: "scope: release-readiness modules: <module-list>"
})
```

The audit-orchestrator runs:
- `qa-engineer scope: release` (production-blocker subset)
- Domain specialists scoped to the module(s)
- Synthesis with go/no-go recommendation per module
- Auto-dispatched audit-verifier

Read the orchestrator's strategic report. Extract:
- Module-by-module verdict (PASS / PASS-WITH-WARNINGS / FAIL)
- Any new P0 findings introduced by the unpushed commits (regression class)
- Any open P1 findings the audit team flags as "should fix before push"

Decision matrix:

| audit-verifier verdict | --strict mode | Phase 3 action |
|------------------------|---------------|----------------|
| PASS | any | proceed |
| PASS-WITH-WARNINGS | off (default) | proceed (warnings noted in final verdict) |
| PASS-WITH-WARNINGS | on | STOP — recommend addressing warnings first |
| FAIL | any | STOP — re-dispatch failing specialist or recommend `/build-loop` to fix |
| HARD-FAIL | any | STOP — orchestrator bug, escalate |

## Phase 3 — Audit-trail check (supervisor pre-push)

```
Skill({
  skill: "supervisor",
  args: "mode: pre-push"
})
```

The supervisor runs:
- Convention compliance on every unpushed commit
- Audit-trail integrity (`git log --grep "<finding-id>"` returns the commit for every finding shipped)
- Live state vs commit claims (3–5 sample probes)
- HSI verification updates if relevant evidence exists

Read the supervisor's snapshot. Posture must be GREEN or AMBER-with-justification to proceed.

## Phase 4 — GO/NO-GO verdict

Synthesise. Write to `.planning/audits/orchestrator/<YYYY-MM-DD>-release-readiness-<branch-short-sha>.md`:

```markdown
# Release Readiness — <branch> @ <short-sha> — <YYYY-MM-DD>

**Workflow:** release-readiness
**Scope:** <since-rev>..HEAD (<commit-count> unpushed commits)
**Modules touched:** <comma-list>
**Findings re-verified:** <count> · all PASS
**Audit-orchestrator verdict:** <PASS / PASS-WITH-WARNINGS / FAIL>
**Supervisor pre-push:** <GREEN / AMBER / RED>

## VERDICT

**<GO | NO-GO>**

<one-paragraph why>

## Phase results

### Phase 1 — Verify ship
- <finding-id>: PASS (probe: <one-line>)
- ...

### Phase 2 — Module scan
- <module>: <verdict> — <one-line summary, link to audit report>

### Phase 3 — Audit-trail check
- Convention compliance: <N>/<N> commits clean
- Audit-trail integrity: <pass / drift>
- Live-state probes: <N>/<N> matched

## What's pushable

If GO:
\`\`\`bash
git push origin <branch>
\`\`\`

If NO-GO: <specific blocker + remediation playbook>

## Self-Check

- [ ] Phase 1 ran every shipped finding's `verifiable_outcome` probe live
- [ ] Phase 2's audit-verifier verdict on disk
- [ ] Phase 3's supervisor snapshot on disk
- [ ] Verdict cites all three phase outcomes
- [ ] If GO: push command shown. If NO-GO: specific remediation playbook named.
```

Append to `.planning/audits/SESSION-LOG.md`:

```markdown
## <YYYY-MM-DD HH:MM UTC> — workflow:release-readiness — <verdict>

**Branch:** <branch>
**Unpushed range:** <since-rev>..HEAD (<count> commits)
**Findings re-verified:** <count>
**Modules scanned:** <comma-list>
**Verdict:** GO | NO-GO
**Reports written:**
- `.planning/audits/orchestrator/<date>-release-readiness-<sha>.md`
- (audit-orchestrator's release-readiness reports)
- (supervisor's pre-push snapshot)

**Recommended next:** <push command> | <remediation playbook>

---
```

## Phase 5 — Hand off

Return concise summary to user:
- Verdict (GO / NO-GO)
- One-sentence why
- Push command (if GO) or remediation playbook (if NO-GO)
- Path to the full report

# Anti-patterns

- Do not skip Phase 1. Re-running `verifiable_outcome` probes is the expensive insurance the workflow exists to provide.
- Do not skip Phase 3. A clean Phase 1 + Phase 2 with broken audit-trail integrity is still NO-GO.
- Do not soften FAIL to GO. The user invoked this workflow because they want the gate.
- Do not push for the user. Hand them the command. Push is the user's act.
- Do not run this when no implementations have shipped — there's nothing to release-ready.
- Do not bypass the workflow because "the build-loop already passed." Build-loop verifies at ship time; release-readiness verifies at push time. Order-dependent / transient bugs surface in the gap.

# Peer skills

You orchestrate (you call them):
- `audit-orchestrator` skill (Phase 2)
- `supervisor` skill (Phase 3)
- `tester` agent (Phase 1, parallel)

You write to:
- `.planning/audits/orchestrator/` (the workflow's own report)
- `.planning/audits/SESSION-LOG.md` (workflow entry)

# Final note

Release-readiness is the workflow that protects the user from "the implementation passed but production still broke." Every probe re-run, every audit-trail check, every convention scan is the difference between a clean release and a 2-AM hotfix. **Run it religiously after every ship, even when "everything obviously works."**

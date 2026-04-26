---
name: audit-and-ship
description: Per-module weekly cycle that audits a module, ships its Top-N findings, and confirms release-readiness — all in one command. Chains audit-orchestrator (module-deep-dive) → audit-verifier → build-loop (ship-findings) → release-readiness workflow. Use as the natural weekly cadence per module: pick a module on Monday, run audit-and-ship, ship verified work by end of day. Examples — "/audit-and-ship module: audits", "/audit-and-ship module: risks top: 3", "/audit-and-ship module: datenschutz severity: P0". Do NOT use for new modules (call /feature-launch); do NOT use for cross-module sweeps (call /audit-orchestrator scope: foundation-audit directly).
user-invocable: true
---
# Role

You (the parent session) are running the **audit-and-ship workflow** — the per-module weekly cycle. One module, four phases, one shipped + verified cluster.

This workflow exists because the most-effective ship cadence is **one module per week**, audited end-to-end and shipped under the audit-grade rigour. Larger scopes burn token budget; smaller scopes don't compound.

This file lives at `.claude/workflows/audit-and-ship.md`. Loads inline in the parent session.

# When to use this workflow

- ✅ Monday morning, picking a module to focus on for the week
- ✅ After a foundation-audit identified a P0 module-level concern
- ✅ Per-module follow-up after a `/incident-response` workflow surfaced a deeper module issue

Don't use when:
- ❌ Multiple modules need attention — run `/audit-orchestrator scope: foundation-audit` first to sequence
- ❌ The module doesn't exist yet — use `/feature-launch`
- ❌ Production is on fire — use `/incident-response` (faster path, narrower scope)

# Inputs

- `module: <name>` — required. The module to audit + ship.
- `top: <n>` — number of findings to ship (default: 5)
- `severity: <P0|P0,P1>` — severity filter (default: `P0,P1`)
- `--skip-release-readiness` — skip Phase 4 (use only when chaining into another workflow)

# The four phases

```
PHASE 1 — Audit                          [audit-orchestrator: module-deep-dive]
   ↓
PHASE 2 — Verify audit                   [audit-verifier auto-dispatch]
   ↓
PHASE 3 — Ship Top-N                     [build-loop: ship-findings]
   ↓
PHASE 4 — Release-readiness              [/release-readiness workflow]
```

# Working Method

## Phase 0 — Pre-flight

1. Confirm `<module>` is a real module in `.planning/audits/_context/SUMMARY.md`. If not: STOP, show the user the available modules.
2. Confirm git working tree is clean. If dirty: STOP, ask user to commit/stash.
3. Confirm current branch is the dev branch. If protected: STOP.
4. Read SESSION-LOG.md tail. If a heavy playbook ran today already: warn the user, recommend break.

## Phase 1 — Module-deep-dive audit

```
Skill({
  skill: "audit-orchestrator",
  args: "scope: module-deep-dive:<module>"
})
```

The audit-orchestrator runs:
- Every relevant specialist scoped to the module (parallel)
- qa-engineer scope: module:<module> (sequential, reads Phase-1 reports)
- Synthesis with module strategy + Top-N action table
- Auto-dispatched audit-verifier

Read the synthesis path from the orchestrator's return value. **Don't proceed if audit-verifier verdict is FAIL or HARD-FAIL** — the orchestrator handles re-dispatch internally; this workflow only proceeds on PASS or PASS-WITH-WARNINGS.

## Phase 2 — Verify audit (gating decision)

The audit-orchestrator already auto-dispatched audit-verifier. Read its verdict from `.planning/audits/audit-verifier/<date>-*.md`.

| Verdict | Workflow action |
|---------|------------------|
| PASS | proceed to Phase 3 |
| PASS-WITH-WARNINGS | proceed to Phase 3, log warnings in final summary |
| FAIL | STOP — recommend re-running `/audit-orchestrator scope: module-deep-dive:<module>` after addressing the verifier's complaints |
| HARD-FAIL | STOP — escalate to user, this is an orchestrator bug |

## Phase 3 — Ship Top-N

Filter the synthesis Top-N by `severity:` parameter, take first `top:` rows.

```
Skill({
  skill: "build-loop",
  args: "scope: ship-top-n:<synthesis-path>:<n> --severity <severity-filter>"
})
```

The build-loop runs:
- Per-finding brief generation
- Effort-cap validation (STOPs if any L-effort finding selected — recommend `/feature-launch` instead)
- Parallel dispatch of independent findings (worktree-isolated)
- Sequential dispatch of file-colliding findings
- Per-finding implementer + tester + retry-on-FAIL (cap 2)
- Build summary

Read the build summary. Note: shipped count, failed count, escalated count.

## Phase 4 — Release-readiness (skip with `--skip-release-readiness`)

```
Skill({
  skill: "release-readiness",
  args: "modules: <module>"
})
```

Reads the unpushed commits, re-verifies every shipped `verifiable_outcome`, runs supervisor pre-push, produces GO/NO-GO.

## Phase 5 — Synthesise + final verdict

Write `.planning/audits/orchestrator/<YYYY-MM-DD>-audit-and-ship-<module>.md`:

```markdown
# Audit-and-Ship — <module> — <YYYY-MM-DD>

**Workflow:** audit-and-ship
**Module:** <module>
**Phases:** audit · verify · ship · release-readiness
**Synthesis:** <link to Phase 1 strategic report>
**Verifier verdict:** <link to Phase 2 verifier verdict>
**Build summary:** <link to Phase 3 build summary>
**Release verdict:** <link to Phase 4 release-readiness report>

## VERDICT

**<GREEN | AMBER | RED>**

<one paragraph why>

## Phase results

### Phase 1 — Audit
- Synthesis verdict: <PASS / PASS-WITH-WARNINGS / FAIL>
- Top-N actions: <count> · <severity breakdown>

### Phase 2 — Verify
- audit-verifier: <verdict>
- Re-dispatches: <count or "none">

### Phase 3 — Ship
- Findings shipped: <P>/<N>
- Failed: <count>
- Escalated: <count>
- Pattern regressions caught: <count>

### Phase 4 — Release-readiness
- GO/NO-GO: <verdict>
- Probes re-run: <count>
- Convention compliance: <N>/<N>

## What's pushable

If GREEN:
\`\`\`bash
git push origin <branch>
\`\`\`

If AMBER/RED: <specific blocker + remediation>

## Open threads
- <escalated findings + their reasons>
- <warnings from audit-verifier still standing>

## Recommended next
- <next-week module pick> | <follow-up workflow>
```

Append a single entry to `.planning/audits/SESSION-LOG.md`:

```markdown
## <YYYY-MM-DD HH:MM UTC> — workflow:audit-and-ship · module=<module> — <verdict>

**Module:** <module>
**Top-N requested:** <n> · severity-filter: <filter>
**Shipped:** <P>/<N> · <F> failed · <E> escalated
**Release:** <GO / NO-GO>
**Reports written:** <links>
**Recommended next:** <next module or workflow>

---
```

## Phase 6 — Hand off

Return concise summary to user:
- Verdict (GREEN/AMBER/RED)
- Shipped/failed/escalated count
- Push instructions or remediation playbook
- Next-week module pick (if GREEN)

# Anti-patterns

- Do not skip Phase 2 (audit-verifier). Phase 3 against unverified findings poisons the audit trail.
- Do not skip Phase 4 unless explicitly chaining into another workflow. The user pushes after this workflow; release-readiness is the gate.
- Do not run multiple `audit-and-ship` workflows in one session. Each is ~60–90 min wall-clock + ~150K tokens. Two = quality collapse.
- Do not select an L-effort finding into Phase 3. Build-loop will STOP — kick to `/feature-launch` instead.
- Do not bypass the module check in Phase 0. Auditing a module that doesn't exist produces empty syntheses.

# Peer skills

You orchestrate (you call them):
- `audit-orchestrator` skill (Phase 1)
- `build-loop` skill (Phase 3)
- `release-readiness` workflow (Phase 4)
- `audit-verifier` agent (auto-dispatched by Phase 1, read by Phase 2)

# Final note

This is the canonical weekly cycle. Run it Monday morning, push by Friday afternoon, repeat next week with the next module. **Compounding only happens when the cycle is religious.**

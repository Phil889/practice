---
name: incident-response
description: Production-incident workflow that diagnoses, fixes, and verifies — fast. Chains qa-engineer (pattern scan) → optional domain specialist → build-loop (ship-cluster) → release-readiness → post-incident review with HSI proposal. Use when production breaks, when a customer reports a bug, or when monitoring fires. Examples — "/incident-response symptom: 500-on-checkout", "/incident-response module: payments severity: P0", "/incident-response pattern: B2 multi-tenant-leak". Do NOT use for cosmetic bugs or non-blocking issues — use `/audit-and-ship` instead. Do NOT use as a substitute for actually rolling back if rollback is faster than fix-forward.
user-invocable: true
---
# Role

You (the parent session) are running the **incident-response workflow** — the path from "something broke" to "fix is verified and pushable" with audit-grade rigour at incident speed. Faster than `/audit-and-ship`; narrower scope; the same evidence-grounding non-negotiables.

This workflow exists because **the gap between "we noticed a bug" and "the fix is live" is where most incidents compound into bigger incidents.** Skip the audit, you ship a half-fix. Skip the verifier, you ship a regression. This workflow keeps both gates without slowing you down — by scoping aggressively.

This file lives at `.claude/workflows/incident-response.md`. Loads inline in the parent session.

# When to use this workflow

- ✅ Production is reporting an error to users right now
- ✅ A monitoring alert fired (latency, error rate, queue depth)
- ✅ A customer just reported a behaviour change
- ✅ You suspect a specific historical pattern (B2 leak, B5 role casing, etc.) re-introduced

Don't use when:
- ❌ Rollback is the faster path (revert the recent commits, deploy, *then* run this workflow against the reverted state)
- ❌ The bug is cosmetic / non-blocking — that's `/audit-and-ship`
- ❌ You don't have a rough hypothesis — open a `/supervisor mode: talk:` first to triage

# Inputs (one of these is required)

- `symptom: <one-line description>` — the user-visible behaviour, e.g. "500 on checkout" or "logo missing on Siempelkamp dashboard"
- `module: <name>` — the module suspected
- `pattern: <pattern-id>` — the historical pattern suspected (e.g. `B2`, `B5`)
- `customer: <org-id>` — the affected tenant (if known — orients RLS / multi-tenant probes)

Optional:
- `since: <git-rev>` — narrow the diagnostic to commits since a known-good revision (default: last 24h of unpushed + pushed commits)
- `--rollback-first` — workflow refuses to ship-fix and recommends rollback instead (use when fix-forward is risky)

# The five phases

```
PHASE 1 — Diagnose                       [qa-engineer pattern scan / module scan]
   ↓
PHASE 2 — Triage + scope                 [orchestrator decides: fix-forward or rollback]
   ↓
PHASE 3 — Ship fix                       [build-loop ship-cluster, P0 only]
   ↓
PHASE 4 — Verify + release               [release-readiness workflow]
   ↓
PHASE 5 — Post-incident review           [HSI proposal + supervisor entry]
```

# Working Method

## Phase 0 — Pre-flight (incident sanity)

1. Confirm git working tree is clean. If dirty: STOP. Mid-incident is the worst time to merge half-finished work — commit/stash first.
2. Confirm current branch is the dev branch (or a hotfix branch if conventions differ).
3. Read SESSION-LOG.md tail. If a heavy playbook is currently in-flight: STOP. Resume after that playbook finishes — incidents compound when concurrent runs collide.

## Phase 1 — Diagnose

Pick the diagnostic dispatch based on input:

| Input | Dispatch |
|-------|----------|
| `pattern: <id>` | `Agent({subagent_type: "qa-engineer", prompt: "scope: pattern:<id>. Production incident — find every file:line currently exhibiting this pattern. Cite verifiable_outcome probes that distinguish broken from fixed. Speed > completeness."})` |
| `module: <name>` | `Agent({subagent_type: "qa-engineer", prompt: "scope: module:<name>. Production incident — full pattern sweep across this module. Rank by likelihood of being the live cause."})` |
| `symptom: <text>` only | `Agent({subagent_type: "qa-engineer", prompt: "scope: free:<symptom>. Production incident — diagnose. Use Grep + Read + live tools to locate the root cause. Cite file:line + verifiable_outcome."})` |
| `customer: <org-id>` only | `Agent({subagent_type: "qa-engineer", prompt: "scope: pattern:B2,B3,B5. Tenant-isolation incident on org <org-id>. Cite RLS gaps + role-casing bugs + org-id leaks."})` |

If `symptom:` and `module:` are both supplied, do both dispatches in parallel.

Read qa-engineer's report. Identify the **most likely root cause** finding (highest severity + highest confidence + concrete reproduction).

## Phase 2 — Triage + scope

Decision: fix-forward or rollback?

| Signal | Recommendation |
|--------|----------------|
| Root cause is in a commit shipped <2h ago | **Rollback first.** Revert the commit, deploy, then run this workflow on the reverted state to actually fix. |
| Root cause is in a commit shipped >2h ago AND fix is S-effort | Fix-forward |
| Root cause is in old code (>1 day) | Fix-forward |
| Root cause is M or L effort | **Rollback first** — incident speed needs S-effort fixes; M/L is for /audit-and-ship |
| `--rollback-first` flag set | Always rollback; workflow stops at end of this phase with rollback instructions |
| User explicitly says fix-forward | Honour the choice |

**If rollback recommended:** STOP. Output:

```
ROLLBACK RECOMMENDED

Recent risky commits since <since>:
- <sha> · <message>
- ...

Rollback command:
git revert <sha> --no-edit && git push origin <branch>

After rollback deploys, re-run /incident-response with --rollback-first to do the proper fix.
```

**If fix-forward:** continue to Phase 3.

## Phase 3 — Ship fix

Build a one-finding cluster from the qa-engineer report (or 2–3 findings if the root cause is multi-file but tightly-coupled). Pass to build-loop:

```
Skill({
  skill: "build-loop",
  args: "scope: ship-cluster:<finding-id-list> --severity P0 --incident-mode"
})
```

`--incident-mode` is a flag the build-loop honours by:
- Compressing per-finding briefs (no peer-cross-cite section needed for incident fixes)
- Tightening retry-cap from 2 to 1 (incident speed; if 1 retry FAILs, escalate to user immediately)
- Forcing sequential dispatch even for non-colliding files (reduces complexity in stress)

Read the build summary. **If any finding ESCALATED:** Phase 4 still runs — the user must see release-readiness verdict against whatever shipped, plus the unshipped finding's status.

## Phase 4 — Release-readiness

```
Skill({
  skill: "release-readiness",
  args: "modules: <touched-modules> --strict"
})
```

`--strict` is mandatory for incident workflows: a PASS-WITH-WARNINGS verdict on a regular ship is fine; on an incident fix, warnings need to be addressed before push. The workflow honour this strictness.

If GO: proceed to Phase 5.
If NO-GO: STOP, surface the blocker. The user decides whether to push anyway (logged in incident report) or fix the blocker first.

## Phase 5 — Post-incident review

Write `.planning/audits/orchestrator/<YYYY-MM-DD-HHMM>-incident-<slug>.md`:

```markdown
# Incident Report — <slug> — <YYYY-MM-DD HH:MM UTC>

**Workflow:** incident-response
**Trigger:** <symptom / monitoring alert / customer report>
**Module:** <module>
**Pattern:** <pattern-id or "novel">
**Severity:** P0
**Decision:** fix-forward | rollback

## Timeline
- <HH:MM> incident detected (<source>)
- <HH:MM> qa-engineer dispatched
- <HH:MM> root cause identified: <one line + file:line>
- <HH:MM> fix committed: <sha>
- <HH:MM> tester PASS
- <HH:MM> release-readiness: GO
- <HH:MM> push to remote

## Root cause
<one paragraph: what was wrong, where, why it bit now>

## Fix
<one paragraph: what changed, why this is the right shape>

## Verifiable outcome
- Pre-fix probe: `<probe>` returned <RED state>
- Post-fix probe: same query returns <GREEN state>

## What we learned

### HSI proposal
<If this incident reveals a systemic gap — e.g. "the harness shipped a B2 leak past qa-engineer's pattern scan because the scan didn't cover this code path" — propose an HSI:>

```
HSI-<NNN> — <hypothesis>
Status: PROPOSED
Trigger evidence: this incident
Proposed fix: <one paragraph>
Verification probe: <how we'd know the HSI works>
```

Append to `.planning/audits/SYSTEM-CHANGELOG.md`.

### Convention compliance check
- Was the broken commit's verifiable_outcome correctly stated? <yes/no>
- Did regression tests exist for this pattern? <yes/no>
- Was the audit-trail (`git log --grep "<finding-id>"`) complete? <yes/no>

If any "no": that's a process gap worth a follow-up HSI.

## Recommendations
- [ ] <one-time fix shipped>
- [ ] <process change to prevent recurrence>
- [ ] <pattern to add to qa-engineer's taxonomy if novel>
```

Append entry to `.planning/audits/SESSION-LOG.md`:

```markdown
## <YYYY-MM-DD HH:MM UTC> — workflow:incident-response · <slug> — <verdict>

**Trigger:** <symptom / module / pattern>
**Decision:** fix-forward | rollback
**Wall-clock to fix:** <minutes>
**Commits:** <sha-list>
**Release verdict:** <GO / NO-GO>
**HSI proposed:** <HSI-NNN or "none">
**Reports written:**
- `.planning/audits/orchestrator/<incident-report-path>`

---
```

## Phase 6 — Hand off

Return to user:
- Verdict (FIXED / ROLLED-BACK / ESCALATED)
- Wall-clock time-to-fix
- Commit SHAs
- Push command (if GO)
- Path to incident report
- HSI proposal (if any)

# Anti-patterns

- Do not skip Phase 1 (qa-engineer diagnostic). Vibes-debugging an incident is how you ship a half-fix that incidents itself in 4 hours.
- Do not skip Phase 4. An "incident fix" that breaks something else is how a 5-minute incident becomes a 5-hour incident.
- Do not bypass triage in Phase 2. Fix-forward when rollback is the faster path is malpractice.
- Do not push without `--strict` release-readiness PASS. Incident fixes must clear a higher bar, not a lower one.
- Do not skip Phase 5 (post-incident review + HSI). The compounding from "this won't happen again" only happens if the lesson is captured.
- Do not run multiple incidents in parallel from one session. Sequential discipline; resume order from SESSION-LOG.

# Peer skills

You orchestrate (you call them):
- `qa-engineer` agent (Phase 1)
- `build-loop` skill (Phase 3)
- `release-readiness` workflow (Phase 4)

You write to:
- `.planning/audits/orchestrator/` (incident report)
- `.planning/audits/SESSION-LOG.md` (workflow entry)
- `.planning/audits/SYSTEM-CHANGELOG.md` (HSI proposal, if any)

# Final note

Incidents are the most-expensive learning opportunities the harness gives you. **Run this workflow, not just because the customer is angry, but because every incident is a refutation of a hypothesis you didn't realise you were holding.** The HSI you propose in Phase 5 is the compounding asset; the fix in Phase 3 is the cost of admission.

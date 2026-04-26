---
name: feature-launch
description: End-to-end workflow for shipping a new feature with audit-grade rigour. Chains audit-orchestrator (feature-design) → audit-verifier → build-loop (ship-findings from the design output) → release-readiness → supervisor pre-push. Use when adding a new module or substantially-new functionality. Examples — "/feature-launch name: incident-management", "/feature-launch name: ai-summary-cards module: dashboard", "/feature-launch name: tenant-impersonation severity-floor: P0,P1". Do NOT use for fixes within an existing module — use `/audit-and-ship` instead. Do NOT use for spec-only work without a build (the design playbook produces specs; this workflow goes further).
user-invocable: true
---
# Role

You (the parent session) are running the **feature-launch workflow** — the path from "we need feature X" to "feature X is shipped, verified, and pushable" with audit-grade rigour.

This workflow exists because **new features are where evidence-grounding fails most often.** Specialists don't have historical patterns to match against; bugs are novel; the design has to be invented before the build. This workflow forces design before build (gate Phase 1+2), then ships under the same rigour as `/audit-and-ship`.

This file lives at `.claude/workflows/feature-launch.md`. Loads inline in the parent session.

# When to use this workflow

- ✅ A new module is needed (no existing route, no existing service file)
- ✅ Substantial new functionality in an existing module (≥3 new database tables / ≥5 new endpoints)
- ✅ A finding from `/audit-and-ship` was deferred as L-effort and kicked here
- ✅ A roadmap-phase requires a feature you haven't built yet

Don't use when:
- ❌ Fixing within an existing module → `/audit-and-ship`
- ❌ Just want a design spec, not a build → `/audit-orchestrator scope: feature-design:<name>` directly
- ❌ Production incident → `/incident-response`

# Inputs

- `name: <feature-slug>` — required. Lower-kebab-case identifier for the feature.
- `module: <name>` — optional. The module the feature lives in (default: feature creates its own module if no fit)
- `severity-floor: <P0|P0,P1>` — minimum severity to ship from the design's findings (default: `P0,P1`)
- `--design-only` — stop after Phase 2; produce the spec, no build (use when ship-readiness depends on user review of the design)

# The five phases

```
PHASE 1 — Design                         [audit-orchestrator: feature-design]
   ↓
PHASE 2 — Verify design                  [audit-verifier on the design output]
   ↓
PHASE 3 — Ship the design's findings     [build-loop: ship-findings from design]
   ↓
PHASE 4 — Release-readiness              [/release-readiness workflow]
   ↓
PHASE 5 — Pre-push gate                  [supervisor: pre-push]
```

# Working Method

## Phase 0 — Pre-flight

1. Confirm `<name>` doesn't already exist in `.planning/audits/_context/SUMMARY.md`. If it does: STOP — the user wants `/audit-and-ship` for an existing feature, not `/feature-launch`. (Override with `--force-new` if the user genuinely wants a parallel implementation.)
2. Confirm git working tree is clean.
3. Confirm current branch is the dev branch.
4. Read SESSION-LOG.md tail. If a heavy playbook ran today: warn user, recommend break.

## Phase 1 — Design

```
Skill({
  skill: "audit-orchestrator",
  args: "scope: feature-design:<name>"
})
```

The audit-orchestrator's feature-design playbook runs:
- All relevant specialists scoped to the feature area, in parallel:
  - Domain specialists: which constraints does this feature satisfy?
  - workflow-architect (or equivalent): where does this feature plug into existing flows?
  - competitive-analyst (or equivalent): what's the parity bar?
  - ai-strategist (if applicable): what AI fits here?
- Then sequential: designer specialist consumes Phase-1 reports and produces an implementable spec
- Auto-dispatched audit-verifier on the design

The output is a **design synthesis** with a Top-N "atomic build IDs" table — each row is a shippable finding (file/migration/UI scope + verifiable_outcome).

Read the synthesis path. Confirm the Top-N table exists.

## Phase 2 — Verify design

The audit-orchestrator already auto-dispatched audit-verifier. Read the verdict.

| Verdict | Workflow action |
|---------|------------------|
| PASS | proceed to Phase 3 |
| PASS-WITH-WARNINGS | proceed to Phase 3, log warnings in final summary |
| FAIL | STOP — recommend re-running `/audit-orchestrator scope: feature-design:<name>` after addressing the verifier's complaints |
| HARD-FAIL | STOP — escalate to user, this is an orchestrator bug |

**If `--design-only` flag set:** STOP here. Output the synthesis path + verifier verdict. The user will run `/feature-launch` again without the flag (or `/audit-and-ship`) when ready.

## Phase 3 — Ship the design's findings

The synthesis Top-N table contains atomic build IDs. Filter by `severity-floor` and pass to build-loop:

```
Skill({
  skill: "build-loop",
  args: "scope: ship-findings:<synthesis-path> --severity <severity-floor>"
})
```

The build-loop runs the standard ship pipeline:
- Per-finding briefs
- Effort-cap validation (note: feature-launch may legitimately have M-effort findings; effort-cap allows ≤2 M)
- Parallel/sequential dispatch with worktree-isolation
- Per-finding implementer + tester + retry-on-FAIL (cap 2)
- Build summary

Read build summary. **If any finding ESCALATED:** Phase 4 still runs against what shipped, but the workflow's final verdict will be AMBER not GREEN.

## Phase 4 — Release-readiness

```
Skill({
  skill: "release-readiness",
  args: "modules: <feature-module>"
})
```

Live re-verification of every shipped `verifiable_outcome` + audit-trail integrity check + supervisor pre-push.

**Mandatory for feature-launch:** the `--strict` flag is implied — new features must clear PASS-not-PASS-WITH-WARNINGS, because new features are where regression tests don't yet exist to catch drift later.

If GO: proceed to Phase 5.
If NO-GO: STOP, surface the blocker. The user decides whether to address it before push or defer.

## Phase 5 — Pre-push gate

```
Skill({
  skill: "supervisor",
  args: "mode: pre-push"
})
```

The supervisor runs final convention compliance + audit-trail integrity + 3 live-state probes against the unpushed commits. **A new feature shouldn't push if even one HSI is INCONCLUSIVE for a load-bearing claim** — supervisor enforces this.

## Phase 6 — Final report

Write `.planning/audits/orchestrator/<YYYY-MM-DD>-feature-launch-<name>.md`:

```markdown
# Feature Launch — <name> — <YYYY-MM-DD>

**Workflow:** feature-launch
**Feature:** <name>
**Module:** <module> (new | extended)
**Phases:** design · verify · ship · release-readiness · pre-push
**Design synthesis:** <link>
**Verifier verdict:** <link>
**Build summary:** <link>
**Release verdict:** <link>
**Pre-push verdict:** <link>

## VERDICT

**<GREEN | AMBER | RED>**

<one paragraph why>

## Phase results

### Phase 1 — Design
- Design synthesis: <link>
- Atomic build IDs produced: <count>
- Specialists involved: <comma-list>

### Phase 2 — Verify design
- audit-verifier: <verdict>

### Phase 3 — Ship
- Findings shipped: <P>/<N>
- Failed: <count>
- Escalated: <count> (<list with names>)
- Pattern regressions caught: <count>

### Phase 4 — Release-readiness
- GO/NO-GO: <verdict>
- Probes re-run: <count>

### Phase 5 — Pre-push
- Posture: <GREEN/AMBER/RED>
- Convention compliance: <N>/<N>
- HSI verification: <pending count>

## What's pushable

If GREEN:
\`\`\`bash
git push origin <branch>
\`\`\`

Then verify deployment: <link to runbook or "deployment-target not specified">.

If AMBER/RED: <specific blocker + remediation>

## What's deferred to follow-up

- <findings deferred from severity-floor filter>
- <escalated findings still open>

## Open threads
- <warnings standing>
- <open HSIs related to this feature>

## Recommended next
- <if GREEN: monitor for 7 days, then `/audit-and-ship module: <name>` to harden>
- <if AMBER: retry escalated findings>
- <if RED: investigate + retry the failing phase>
```

Append entry to `.planning/audits/SESSION-LOG.md`:

```markdown
## <YYYY-MM-DD HH:MM UTC> — workflow:feature-launch · name=<name> — <verdict>

**Feature:** <name> · module=<module>
**Atomic build IDs:** <N> · shipped: <P>/<N> · escalated: <E>
**Release:** <GO / NO-GO>
**Pre-push:** <GREEN / AMBER / RED>
**Reports written:** <link>
**Recommended next:** <follow-up workflow>

---
```

## Phase 7 — Hand off

Return concise summary to user:
- Verdict (GREEN/AMBER/RED)
- Atomic build IDs shipped/failed/escalated
- Push command (if GREEN)
- 7-day monitoring reminder for new feature

# Anti-patterns

- Do not skip Phase 1 (design). Building a new feature without a verified design is how you ship 8 atomic build IDs that conflict in production.
- Do not skip Phase 2 (verify design). PASS-WITH-WARNINGS on a design is fine; FAIL means the design is incoherent and Phase 3 will compound the incoherence.
- Do not skip Phase 5 (pre-push). New features are the highest-risk push class — supervisor's gate exists for a reason.
- Do not parallelise feature-launches. One feature at a time per session — they share the dev branch and worktree-isolation can't fully decouple.
- Do not bypass `--strict` release-readiness for new features. Regression tests don't exist yet; the live re-verify is your only safety net.
- Do not declare GREEN if any P0 finding from the design ESCALATED. Even one ESCALATED P0 in a feature-launch = AMBER at best.

# Peer skills

You orchestrate (you call them):
- `audit-orchestrator` skill (Phase 1)
- `build-loop` skill (Phase 3)
- `release-readiness` workflow (Phase 4)
- `supervisor` skill (Phase 5)

You write to:
- `.planning/audits/orchestrator/` (workflow report)
- `.planning/audits/SESSION-LOG.md` (workflow entry)

# Final note

Feature launches are the heaviest workflow in `practice` — by design. **A workflow that runs five phases in sequence catches the failure modes that running one phase doesn't.** The hour you spend in feature-launch saves the day you'd spend in incident-response a week later. Run it religiously.

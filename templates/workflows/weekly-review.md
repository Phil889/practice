---
name: weekly-review
description: End-of-week reflection workflow that synthesises the past 7 days of project activity into a snapshot + next-week plan. Chains supervisor (hygiene check) → supervisor (weekly-review mode) → backlog burn analysis → roadmap drift check → next-week plan with concrete actions. Use Friday afternoon or Monday morning. Examples — "/weekly-review", "/weekly-review week-of: 2026-04-19". Do NOT use as a substitute for `/supervisor mode: snapshot` (that's intra-day; this is end-of-week reflection).
user-invocable: true
---
# Role

You (the parent session) are running the **weekly-review workflow** — the rhythm that turns daily tactics into weekly compounding. One command produces a complete week-in-review snapshot + next-week plan, so the user steps into Monday with momentum, not a cold start.

This workflow exists because **without a weekly review, the audit trail compounds but the user's mental model doesn't.** Every Friday-or-Monday, the user needs to see: what shipped, what didn't, what the harness learned, what's next. This workflow produces that briefing in one command.

This file lives at `.claude/workflows/weekly-review.md`. Loads inline in the parent session.

# When to use this workflow

- ✅ Friday afternoon (close out the week)
- ✅ Monday morning (cold-start the week with a Friday-snapshot)
- ✅ When the user asks "where are we?" but the answer requires looking back, not just at the latest run

Don't use when:
- ❌ Mid-day mid-week — `/supervisor mode: snapshot` is faster and better-fit
- ❌ Right after a heavy run — the supervisor's `mode: latest-run` is the right call
- ❌ For multi-week or multi-month rollups — that's `/supervisor mode: progress` against a roadmap span

# Inputs

- `week-of: <YYYY-MM-DD>` — the Monday of the week to review (default: this week, computed from today)
- `--include-archive` — also read `_archive/sessions/<YYYY-MM>.md` if the week spans an archive boundary

# The five phases

```
PHASE 1 — Hygiene check                  [supervisor: hygiene if soft cap tripped]
   ↓
PHASE 2 — Weekly snapshot                [supervisor: weekly-review mode]
   ↓
PHASE 3 — Backlog burn                   [analyse P0/P1/deferred over the week]
   ↓
PHASE 4 — Roadmap drift                  [compare planned vs actual]
   ↓
PHASE 5 — Next-week plan                 [concrete actions, not aspirations]
```

# Working Method

## Phase 0 — Pre-flight

1. Compute `week-of` if not supplied: most-recent Monday at-or-before today.
2. Confirm SESSION-LOG.md has entries spanning the week. If empty for the whole week: STOP, tell the user "no activity this week — nothing to review".

## Phase 1 — Hygiene check

```
Skill({
  skill: "supervisor",
  args: "mode: snapshot"
})
```

Read the snapshot's hygiene line. If any artefact category exceeds soft cap:

```
Skill({
  skill: "supervisor",
  args: "mode: hygiene"
})
```

Run hygiene FIRST so the rest of the workflow operates on a clean working set. Hygiene archives older entries and regenerates the SESSION-LOG.md monthly rollup, which Phase 2+ depend on.

## Phase 2 — Weekly snapshot

```
Skill({
  skill: "supervisor",
  args: "mode: weekly-review"
})
```

The supervisor produces:
- 7-day activity summary (audits, builds, workflows run)
- HSI status flips this week (verified / refuted / new)
- Posture trajectory (was Monday GREEN, now AMBER? RED?)
- Convention-compliance trend (improving / drifting)

Read the supervisor's report from disk. Don't paraphrase — quote.

## Phase 3 — Backlog burn

Compute over the week:

| Metric | Source | Compute |
|--------|--------|---------|
| **Findings shipped** | `_findings-status/` PASS entries this week | count |
| **Findings opened** | new entries in `_findings-status/` this week | count |
| **Net burn** | shipped − opened | sign matters |
| **Escalated** | ESCALATED entries gained this week | count + names |
| **Deferred** | DEFERRED entries gained this week | count |
| **P0 backlog** | active P0 findings start-of-week vs end-of-week | delta |
| **P1 backlog** | active P1 findings start-of-week vs end-of-week | delta |
| **Mean-time-to-fix (P0)** | for shipped P0s: time from finding-opened to tester-PASS | average |

If net burn is negative (more opened than shipped): **flag as backlog drift.**
If P0 delta is positive: **flag as compounding risk.**
If MTTF (P0) is climbing week-over-week: **flag as ship-friction.**

## Phase 4 — Roadmap drift

Read `{{ROADMAP_PATH}}` (if present). Compare planned-this-week against actual.

For each phase:
- ✅ checkboxes ticked this week → "on plan"
- ⏸ checkboxes still open that were planned for this week → "behind"
- ✨ checkboxes ticked that weren't planned → "above plan" or "scope creep" (worth distinguishing)

Aggregate:
- Phase progress: % complete vs % time elapsed
- Drift signal: phase falling behind by ≥2 weeks → flag
- Scope-creep signal: ≥3 above-plan checks → flag (compounds short-term but slows the planned phase)

If no roadmap exists, write a one-line note: "No roadmap detected at `{{ROADMAP_PATH}}`. Recommend creating one for future weekly-reviews."

## Phase 5 — Next-week plan

Synthesise. Produce a concrete, actionable plan — not aspirations. Three buckets:

### Must-do next week
- 1–3 items the harness should ship next week to stay on plan
- Each item: workflow + scope + effort-estimate + driver
- Example: `/audit-and-ship module: risks` (Tue, M-effort, drives Phase-2 §risks-module checkbox)

### Should-do if time
- 1–3 items that are valuable but not on critical-path

### Watch-list
- Open threads from this week that need monitoring (escalated findings, REGRESSED HSIs, AMBER posture trends)

## Phase 6 — Final report

Write `.planning/audits/orchestrator/<YYYY-MM-DD>-weekly-review.md`:

```markdown
# Weekly Review — week of <YYYY-MM-DD> — <YYYY-MM-DD>

**Workflow:** weekly-review
**Week:** <Monday> to <Sunday>
**Posture trajectory:** <Monday-posture> → <today-posture>

## TL;DR

{Three sentences: biggest win, biggest miss, biggest takeaway.}

## Activity summary
- Audits run: <N>
- Builds run: <N>
- Workflows run: <N> (`/release-readiness` × N · `/audit-and-ship` × N · ...)
- Commits: <N>

## Backlog burn

| Metric | Mon | Fri | Δ |
|--------|-----|-----|---|
| P0 active | <N> | <N> | <±N> |
| P1 active | <N> | <N> | <±N> |
| Deferred | <N> | <N> | <±N> |
| Escalated | <N> | <N> | <±N> |

- **Net burn:** <shipped − opened>
- **MTTF (P0):** <hours/days> · trend: <improving/stable/drifting>
- **Flags:** <list or "none">

## HSI iteration this week
- Verified: <list>
- Refuted: <list with replacement HSI links>
- New: <list>

## Roadmap status
- Phase: <current phase>
- On plan: <list of ticks>
- Behind: <list of misses>
- Above plan / scope creep: <list>

## Next-week plan

### Must-do
- [ ] {workflow + scope + effort + driver}

### Should-do
- [ ] {workflow + scope + effort}

### Watch-list
- {open thread + monitoring action}

## Self-Check
- [ ] Hygiene check ran (Phase 1)
- [ ] All four metrics computed (Phase 3)
- [ ] Roadmap compared (Phase 4)
- [ ] Next-week plan is actionable (workflow + scope + effort, not aspirations)
- [ ] Confidence: high | medium | low — {reason}
```

Append entry to `.planning/audits/SESSION-LOG.md`:

```markdown
## <YYYY-MM-DD HH:MM UTC> — workflow:weekly-review · week-of=<YYYY-MM-DD> — <verdict>

**Activity:** <audits>+<builds>+<workflows> runs · <commits> commits
**Burn:** <net> · MTTF P0: <metric>
**Posture trajectory:** <Mon> → <Fri>
**Next-week must-do:** <comma-list of workflows>
**Reports written:** <link>

---
```

## Phase 7 — Hand off

Return concise summary to user:
- Posture trajectory (one line)
- Net burn (one line)
- Next-week must-do (3 bullets)
- Path to the full report

# Anti-patterns

- Do not skip Phase 1 (hygiene). A weekly review against a bloated working set produces unreliable metrics.
- Do not produce aspirations as next-week plan. Every must-do has a workflow + scope + effort.
- Do not gloss over backlog drift. If shipped < opened this week, surface it loud — it's a compounding risk.
- Do not run weekly-review more than once per week. Twice = noise.
- Do not skip Phase 4 (roadmap drift). The compounding risk you can't see is the one that bites.
- Do not synthesise without reading SESSION-LOG end-to-end for the week. The supervisor in `mode: weekly-review` does this — trust its output.

# Peer skills

You orchestrate (you call them):
- `supervisor` skill (Phase 1 hygiene + Phase 2 weekly-review)

You read from:
- `.planning/audits/SESSION-LOG.md` (week's entries)
- `.planning/audits/SYSTEM-CHANGELOG.md` (HSI flips this week)
- `.planning/audits/_findings-status/` (backlog state Mon vs Fri)
- `{{ROADMAP_PATH}}` (planned vs actual)

# Final note

The weekly review is the rhythm that turns the harness's daily compounding into the user's strategic visibility. **Don't skip it. Don't pad it. Make it the most-trusted artefact of the week.**

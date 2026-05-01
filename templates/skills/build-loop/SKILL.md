---
name: build-loop
description: Build orchestrator skill for {{PROJECT_NAME}}. Reads an audit synthesis or specialist report, extracts finding-IDs with their cited file:line + verifiable_outcome probe, then dispatches implementer + tester per finding (parallel where files don't collide, sequenced when they do). Aggregates per-finding status, retries failed verifications (cap 2), writes a build summary, and appends to SESSION-LOG.md. Use when an audit has produced a Top-N action list and you want to ship all of them with audit-grade rigour. Examples — "ship-findings from foundation-audit {date} top-5", "ship-cluster F-002+F-003+F-004", "ship-top-n .planning/audits/orchestrator/{date}-foundation-audit.md 3". Do NOT use for new module design — call audit-orchestrator with feature-design playbook first.
user-invocable: true
---
# Role

You (the parent session) are now operating as the **{{PROJECT_NAME}} Build Orchestrator**. You convert an audit's findings into shipped commits with audit-grade rigour. You don't write code yourself — you decompose a finding-list into per-finding work-packages, dispatch `implementer` to ship each one, dispatch `tester` to verify each one, retry on FAIL (cap 2), and produce a single decision-ready build summary.

You are the build counterpart to the `audit-orchestrator` skill. **The audit team identifies; you ship.**

This skill lives at `.claude/skills/build-loop/SKILL.md`. It runs **inline in the parent session** — the `Agent` tool is always available because skills don't go through the subagent runtime that drops it. If this content ever surfaces in a subagent context, something is misconfigured; the skill is parent-only by design.

# Hard rules (non-negotiable)

1. **Read the source report first.** Extract every finding's: ID, severity, cited file:line, identifier citations, `verifiable_outcome` probe, dependencies, effort.
2. **Pass the FULL context block to implementer + tester.** Not "fix F-002" — the structured brief defined in §"Per-finding context block" below.
3. **Sequence findings that share files or migrations** — never dispatch two implementers that will collide. Detect collisions by overlapping file:line citations.
4. **Cap retries at 2 per finding.** After 2 FAILs, escalate to user with full diff between expected and actual.
5. **Never push.** Implementer doesn't push; you don't push. The user approves.
6. **Stop on new-module work.** If a finding requires a module that doesn't exist (no inventory entry, no service file), STOP and recommend the audit-orchestrator's `scope: feature-design:<module>` playbook instead. New modules need design before build.
7. **One commit per finding** (enforced by implementer). You do not aggregate.
8. **Write the build summary even on partial success.** SESSION-LOG.md gets one entry; the build summary file lives at `.planning/audits/orchestrator/<date>-build-<slug>.md`.

# Invocation Protocol

The user invokes you via `/build-loop <scope: ...>` or `Skill({skill: "build-loop", args: "scope: ..."})`. The `audit-orchestrator` skill also delegates to you for `scope: ship-findings`. Parse the scope parameter:

- `scope: ship-findings:<report-path>` — ship every finding in the report (filter by `--severity P0,P1` flag if user supplies)
- `scope: ship-cluster:F-001,F-007,F-009` — ship a specific finding cluster
- `scope: ship-top-n:<synthesis-path>:<n>` — ship top-N from an orchestrator synthesis (default 5)
- `scope: ship-by-module:<synthesis-path>:<module>` — ship every finding affecting a single module
- `scope: ship-by-pattern:<report-path>:<pattern>` — ship every finding tagged with a specific qa-engineer pattern
- `scope: free:<finding-id-list>` — free-form for one-off composition

# Working Method

## Step 0 — Parse input + verify pre-flight

1. Resolve the source report path. Read it.
2. Refresh inventory if older than the latest commit:
   ```bash
   {{REFRESH_COMMAND}}
   ```
3. Confirm git working tree is clean (`git status` — no uncommitted work that would tangle with implementer's atomic commits). If dirty, **STOP** and ask user to stash or commit.
4. Confirm current branch is `{{DEFAULT_BRANCH}}` — if a protected branch (e.g. `main`/`master`), STOP. Build runs go through the dev branch first.

5. **Effort-cap validation.** Compute the cluster's total effort from the source report's per-finding effort labels (S/M/L). Apply the per-session cap:

   | Effort | Per-session cap | Rationale |
   |--------|------------------|-----------|
   | S (<4h) | max 4 findings | Implementer overhead amortizes well; tester runs in <5 min each |
   | M (1–3 days) | max 2 findings | Each M finding consumes meaningful design work + multiple file edits |
   | L (>3 days) | **0 findings — refer to `feature-design` first** | L-effort findings need spec-level design before any ship-attempt; including them in a ship-cluster wastes dispatch overhead |

   **Validation logic:**
   ```
   if any finding has effort=L:
     STOP. Recommend: Skill({skill: "audit-orchestrator", args: "scope: feature-design:<finding-name>"}).
     Re-run build-loop after the feature-design playbook produces an implementable spec.
   if S_count > 4 or M_count > 2:
     STOP. Recommend splitting into two ship-runs.
   ```

   **Override:** the user can pass `--force-effort-cap` in scope to bypass. Override gets logged in the build summary so post-run analysis can surface whether overrides correlate with elevated defer-rates.

## Step 1 — Extract per-finding briefs

For each finding the scope selects, build a context block (the brief you'll hand to implementer):

### Per-finding context block

This block is the implementer's complete brief — it carries enough metadata to write a fully-traceable commit message (per the implementer's commit-message convention). Every field maps to one line in the eventual commit message.

```markdown
# <finding-id> brief

## Commit metadata (implementer copies these verbatim)

- **type:** <fix | feat | refactor | chore | migration | test | docs | {{DOMAIN_TYPES}}>
- **scope:** <module slug from inventory>
- **finding-id:** <e.g. F-002, synthesis:#3>
- **audit-slug:** <e.g. foundation-audit/{date}>
- **severity:** <P0 | P1 | P2>
- **specialist:** <which specialist filed this>
- **driver:** <comma-list of cross-cited specialists>
- **pattern:** <historical-pattern-id from qa-engineer.md, comma-list, or n/a>
- **report-path:** <repo-relative path to specialist or synthesis report>

## Source

**Citation:** `<report-path>` §<finding-id> — the full finding text + load-bearing claims live in the specialist report. Implementer follows the citation when context is needed; brief stays compact (saves ~500-1000 tokens per dispatch vs verbatim quotes).

**One-line summary:** <≤30 words capturing the load-bearing problem>

## Citations (verified by orchestrator to resolve)
- <file:line> (confirmed: file exists, line valid)
- <identifier> (confirmed via inventory)

## Pre-fix state (implementer live-verifies BEFORE edit)
```{lang}
<verbatim from finding>
```
Expected RED: <what the probe should return today, verbatim from finding>

## Verifiable outcome (implementer live-verifies AFTER commit; tester re-runs)
```{lang}
<verbatim from finding>
```
Expected GREEN: <what the probe should return after fix, verbatim from finding>

## Recommended fix

**Citation:** `<report-path>` §<finding-id>'s "Fix" / "Recommendation" block — specialist's proposal lives there. Implementer may improve, must justify deviation in commit body.

**Approach summary:** <≤2 lines describing the gist of the fix>

## Regression-check checklist (patterns implementer must spot-check NOT reintroduced)
<orchestrator deduces from touched file paths; defaults defined per-project>

## Dependencies
- **Blocks:** <other finding-IDs that need this first> (or "none")
- **Blocked by:** <other finding-IDs that must ship first> (or "none")
- **Sequencing note:** <e.g. "after F-009 ships">

## Render-layer UAT scope
<!--
  Fill this section for every finding that touches frontend / UI files.
  For non-render findings (backend / migration / spec / AI / harness-only edits), use:
    N/A-NON-RENDER — <one-line rationale, e.g. "spec-edit on markdown file, no frontend code touched">

  For render-layer findings, document the full click-path the tester should follow:
    **Route:** <locale-prefixed path if applicable>
    **Setup:** <any preconditions — login as <role>, open record <ID>, etc.>
    **Interaction:** <what to click/type/upload/scroll, step-by-step>
    **DOM assertion:** <what the tester should assert is visible or absent>
    **Screenshot target:** .planning/audits/_screenshots/<finding-id>-<YYYY-MM-DD>/<step>.png
    **Tester runner:** tester (auto) | session-implementer (pre-commit smoke)
-->
<RENDER-or-N/A-NON-RENDER value>
```

**Brief filename convention:** `.planning/audits/_findings-status/<finding-id>-brief.md` (implementer reads this).
**Status filename convention:** `.planning/audits/_findings-status/<finding-id>.md` (implementer + tester both append to this).
**Brief is immutable after orchestrator writes it.** Status file is append-only.

### Brief size ceiling (8 KB body)

The brief body (everything below `# <finding-id> brief`) must not exceed **8 KB**. If the specialist's finding text + recommendation would push the brief over 8 KB:

1. Keep commit metadata + citations + pre-fix state + verifiable outcome + dependencies verbatim (structurally required).
2. Replace `## Source` and `## Recommended fix` with citation-only format:
   - `## Source` → `**Citation:** <report-path> §<finding-id> — read full finding in-situ. One-line summary: <≤30 words>.`
   - `## Recommended fix` → `**Citation:** <report-path> §<finding-id> "Fix" section — read in-situ. Approach summary: <≤2 lines>.`
3. Never verbatim-quote more than 10 lines from the specialist report into the brief.

**Validation:** After writing each brief, check file size. If >8 KB, rewrite with citation-only format. If still >8 KB, split the finding into sub-findings per §"Sub-directory convention" below.

### Sub-directory convention for complex findings

When a finding decomposes into **>3 sub-findings**, create a sub-directory:

```
_findings-status/
  F-007/
    F-007a-brief.md
    F-007a.md
    F-007b-brief.md
    ...
    INDEX.md          # one-line per sub-finding: ID, status, commit SHA
```

The `INDEX.md` summarises the family:

```markdown
# F-007 — <Title>

| Sub-finding | Status | Commit | Summary |
|---|---|---|---|
| F-007a | VERIFIED | abc1234 | <description> |
| F-007b | VERIFIED | def5678 | <description> |
| ... |
```

**Simple findings (≤3 sub-tasks)** stay flat — no directory needed.

The orchestrator globs both `_findings-status/<id>*` and `_findings-status/<id>/<id>*` when resolving status.

Produce `.planning/audits/orchestrator/<YYYY-MM-DD>-build-<scope-slug>-PLAN.md`:

```markdown
# Build Plan — <scope> — <YYYY-MM-DD>

**Orchestrator:** build-loop (skill, parent-session)
**Source:** <report-path>
**Findings selected:** <count>
**Git rev (start):** <sha>

## Pre-flight (worktree base-ref refresh)

- `git fetch origin` — OK
- `git pull --ff-only origin {{DEFAULT_BRANCH}}` — at <BASE_REF> (captured pre-dispatch)
- **BASE_REF:** `<sha>` — every implementer prompt asserts `git merge-base HEAD BASE_REF` matches this value
- **Re-run between phases:** required if any earlier-phase implementer commit landed on `{{DEFAULT_BRANCH}}`

## Collision detection

Files touched by ≥2 findings (must sequence, not parallelize):
- <file>: <finding-id>, <finding-id>
- ...

## Phases

### Phase 1 — independent findings (parallel)
- <finding-id>: <one-line summary>

### Phase 2 — sequential findings (file/migration collisions)
- <finding-id> (after <other>): <reason>

### Phase 3 — dependent findings (logical ordering)
- <finding-id> (after <other>): <sequencing note>

## Per-finding briefs
See `.planning/audits/_findings-status/<finding-id>-brief.md`.

## Estimated wall-clock
- Phase 1: <N> findings × ~10–15min implementer + ~5min tester (parallel) = ~20min total
- Phase 2: <N> findings × ~15min sequential = ~<N×15>min
- Phase 3: <N> findings × ~15min sequential = ~<N×15>min
```

## Step 3 — Dispatch

Per finding, in this order:

### 3a-pre — Pre-dispatch base-ref refresh (worktree base-ref MUST equal `origin/{{DEFAULT_BRANCH}}` tip at dispatch-time)

The Agent runtime's `isolation: "worktree"` snapshots the worktree from the parent's current HEAD at dispatch-time. If the parent's HEAD is stale relative to `origin/{{DEFAULT_BRANCH}}`, every implementer inherits a stale base — causing migration-filename collisions, stale-content cherry-pick conflicts, and silent bugs where an implementer thinks an earlier-phase commit isn't on disk yet. This pattern manifested 3 consecutive times in real ship-clusters before being codified.

**Pre-flight invariant** (run BEFORE Phase 1, and again BEFORE each subsequent phase if any implementer commit landed on `{{DEFAULT_BRANCH}}` since the last phase):

```bash
git fetch origin
git checkout {{DEFAULT_BRANCH}}                       # confirm parent is on the dev branch
git pull --ff-only origin {{DEFAULT_BRANCH}}          # align parent with origin tip
BASE_REF=$(git rev-parse HEAD)                        # capture the ref worktrees will inherit
```

Record `BASE_REF` in the build PLAN's `## Pre-flight` section. The runtime does not expose a `from_ref` parameter, so this orchestrator-side pull is the sole reliable mechanism. Re-run the pre-flight between Phases if any earlier-phase implementer commit landed on `{{DEFAULT_BRANCH}}` mid-orchestration.

**Runtime-side staleness is non-deterministic** even after orchestrator-side pre-flight. The Agent runtime's worktree-snapshot caching may still hand the implementer a base older than `BASE_REF` on first dispatch in each parallel batch. The fix is to make canonical-rebase the implementer's first action (instead of an assertion-then-rebase-only-on-failure path). This costs ~0 wall-clock when the snapshot is fresh and saves ~2 min/dispatch when it's stale. The same operation always runs; the only thing that changes is whether it's a no-op.

### 3a — implementer dispatch

**Worktree-isolation is mandatory for parallel dispatch.** Every parallel implementer Agent call MUST include `isolation: "worktree"`. This eliminates the staging-race that can bundle multiple findings into one commit. Sequential dispatches (Phase 2 / Phase 3) should also pass `isolation: "worktree"` as defence-in-depth.

The dispatch carries the `BASE_REF` (captured in 3a-pre) into the implementer's prompt as the rebase target the implementer must apply before any edit. Detecting a stale base aborts cleanly with explicit manifestation evidence rather than discovering the staleness at cherry-pick / merge time.

```
Agent({
  description: "Ship <finding-id>",
  subagent_type: "implementer",
  isolation: "worktree",   // mandatory; prevents parallel-staging race
  prompt: "Ship finding <finding-id>. Brief at `.planning/audits/_findings-status/<finding-id>-brief.md`.\n\n**Pre-edit canonical rebase:** Inside your worktree, your FIRST action is `git fetch origin && git rebase <BASE_REF>`. This is canonical, not a fallback — runtime worktree-snapshot caching is non-deterministic, and the rebase aligns it before any edit. The worktree shares the parent's `.git`, so the rebase target is reachable even if `origin/{{DEFAULT_BRANCH}}` lags.\n\n**Falsifier-of-last-resort:** After the rebase, run `git merge-base HEAD <BASE_REF>` and verify the output equals <BASE_REF>. If the rebase claimed success but the assertion still diverges, abort BEFORE any edit, write a one-line falsifier note to your status file's `### Pre-flight` section (`base-ref-falsifier: rebase reported success but merge-base diverged: <actual> != BASE_REF <expected>`), and return ESCALATED. Do NOT attempt the fix on a stale base.\n\nIf both the rebase succeeds and the assertion holds: read the brief, read every cited file, ship the fix per your spec (atomic commit, live-verify, status file). Return when commit is on disk."
})
```

For Phase 1, dispatch all independent findings in a single message (parallel). For Phase 2 / 3, dispatch one at a time, waiting for each implementer to return before dispatching the next. Each implementer's worktree is automatically cleaned up if no changes are made; otherwise the path and branch are returned in the result. Merge implementer worktree-branches back to `{{DEFAULT_BRANCH}}` before dispatching the corresponding tester (the tester needs to see the implementer's commit on the branch to re-run the `verifiable_outcome`). After merge-back, re-run the 3a-pre pre-flight if any further parallel batches remain.

### 3b — tester dispatch

After implementer returns success:

```
Agent({
  description: "Verify <finding-id>",
  subagent_type: "tester",
  prompt: "Verify finding <finding-id>. Status file at `.planning/audits/_findings-status/<finding-id>.md`. Re-execute the verifiable_outcome from the brief, run pattern regression spot-check, add regression test if warranted, append your verdict to the status file. Return verdict."
})
```

### 3c — retry on FAIL

If tester returns FAIL:
- Read the status file's `### Failure delta` section
- Re-dispatch implementer: `"Retry <finding-id>. Tester returned FAIL with delta: <quote delta>. Status file at <path>. Address the delta, re-commit (amend the prior commit only if untouched by anyone else; otherwise new commit referencing the same finding-id)."`
- After retry, re-dispatch tester
- Cap at 2 retries per finding. After cap, mark finding `ESCALATED` in status file and continue.

### 3d — retry on collision detection failure

If implementer-A and implementer-B were dispatched in parallel but their commits conflict (rare — collision detection should catch it), the second implementer's commit will fail. Recover:
- Mark second finding `BLOCKED_BY_COLLISION`
- Move it to Phase 2 (sequential)
- Re-dispatch after Phase 1 settles

## Step 4 — Aggregate + write build summary

Write `.planning/audits/orchestrator/<YYYY-MM-DD>-build-<scope-slug>.md`:

```markdown
# Build Summary — <scope> — <YYYY-MM-DD>

**Orchestrator:** build-loop (skill, parent-session)
**Source:** <report-path>
**Git rev (start):** <sha>
**Git rev (end):** <sha>
**Wall-clock:** <minutes>

## TL;DR

<N> findings selected. <P> shipped + verified. <F> failed (<reason>). <E> escalated.

## Per-finding results

| ID | Severity | Verdict | Commit | Status file | Notes |
|----|----------|---------|--------|-------------|-------|
| F-001 | P0 | PASS | abc1234 | _findings-status/F-001.md | clean |
| F-002 | P0 | PASS-RETRY-1 | def5678 | _findings-status/F-002.md | tester FAILed once on RLS spot-check; retry caught a regression |
| F-003 | P0 | ESCALATED | — | _findings-status/F-003.md | implementer touched the wrong file twice; needs human |

## Pattern regressions caught
- <finding-id> introduced <pattern> at <file:line> on first attempt; retry fixed
- ...

## Migrations applied
- <migration-name> by <finding-id>
- ...

## Files changed
- <count> total

## Next actions
- [ ] User pushes commits to remote
- [ ] If P0 cluster shipped: `release-readiness` audit on affected modules
- [ ] If migration applied: confirm via {{MIGRATION_VERIFY_COMMAND}}
- [ ] Escalated findings need human review: <list>
```

## Step 5 — Append to SESSION-LOG.md

Append a build-run entry (mirrors audit-run entry format):

```markdown
## <YYYY-MM-DD HH:MM UTC> — build:<scope-slug> — <verdict>

**Source:** <report-path>
**Findings:** <P>/<N> shipped + verified. <F> failed. <E> escalated.
**Reports written:**
- `.planning/audits/orchestrator/<date>-build-<slug>.md`
- `.planning/audits/_findings-status/<id>.md` × <N>

**Commits:** <sha-list>
**Verdict:** GREEN | AMBER (some failed/escalated) | RED (all failed)
**Recommended next:** <push to remote → release-readiness scoped to module> | <re-dispatch escalated findings> | <break session>
**Why break (if applicable):** <e.g. "shipped P0 cluster — fresh eyes for next module">
**Open threads:** <escalated findings + their reasons>

---
```

## Step 6 — Hand off

Return concise summary to caller:
- Verdict (GREEN/AMBER/RED)
- Per-finding shipped/failed/escalated count
- Build summary path
- Suggested next playbook (typically `release-readiness:<module>` for the module(s) affected)

# Predefined playbooks

## `scope: ship-findings:<report>:<severity-filter>`

Ship every finding matching severity-filter (default `P0,P1`).

Phase 1: collision-detect → parallel dispatch independent findings.
Phase 2: sequential dispatch collision-and-dependency-bound findings.
Phase 3: aggregate + write build summary.

## `scope: ship-cluster:<id-list>`

Ship an explicit comma-separated list. User-curated; trust the user to have checked dependencies.

Default: sequential (small clusters benefit from sequencing — cleaner commit history).

## `scope: ship-top-n:<synthesis>:<n>`

Read the orchestrator synthesis's Top-N action table. Map each row to its driver findings (cross-citations). Ship the union of those findings. Order: synthesis Top-N order.

Use this after a Foundation Audit — natural follow-up.

## `scope: ship-by-pattern:<report>:<pattern>`

Ship every finding tagged with a specific historical-pattern ID.

Default: parallel where files don't collide.

## `scope: ship-by-module:<synthesis>:<module>`

Ship every finding affecting a single module.

Default: sequential (within-module collisions likely).

# Output: artefacts

1. **Build PLAN** — `.planning/audits/orchestrator/<date>-build-<slug>-PLAN.md`
2. **Per-finding briefs** — `.planning/audits/_findings-status/<id>-brief.md` (input to implementer)
3. **Build SUMMARY** — `.planning/audits/orchestrator/<date>-build-<slug>.md`
4. **Per-finding status** — `.planning/audits/_findings-status/<id>.md` (written by implementer + tester; you don't write these directly)
5. **SESSION-LOG.md** — appended entry

# Anti-patterns

- Do not write code yourself — dispatch implementer.
- Do not dispatch implementer without a brief — context starvation produces broken fixes.
- Do not parallelize findings that touch the same file or migration.
- Do not retry beyond 2 — escalate.
- Do not skip the build summary even on partial success — it's how the next session knows what's open.
- Do not push to remote — the user approves push.
- Do not run a build playbook in the same session as a heavy audit playbook (foundation-audit, production-readiness-gate). Break first.
- Do not ship findings tagged "new module needed" — kick to the audit-orchestrator's `feature-design` playbook.
- Do not aggregate multiple findings into one commit — atomicity is enforced by implementer for a reason.

# Peer agents and skills

Upstream (you read their output):
- `audit-orchestrator` skill (synthesis Top-N is your natural input)
- All specialist agents (specialist reports — direct ship sources)

Downstream (you dispatch them):
- `implementer` agent (per finding)
- `tester` agent (per finding, after implementer)

Adjacent (don't call, but coordinate):
- `audit-verifier` agent (verifies audits, not builds — but its quality-bar discipline is your reference for citation rigour)

# Final note

The audit harness sells when it ships. Every audit that ends without a `build-loop` follow-through is theatre. Your job is to make ship-quality the default, not the exception. **Atomic commits + live verification + pattern check + per-finding traceability = enterprise-grade — every time.**

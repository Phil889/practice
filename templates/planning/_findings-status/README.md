# Findings Status — Commit-Message Convention

**Every commit produced by the `implementer` agent follows this convention.** The audit harness depends on it: `git log --grep "audit:"` lists every audit-driven ship; `git log --grep "<finding-id>"` shows a finding's full life; `git log --grep "roadmap: phase-1"` lists all phase-1 build work. Skipping a field breaks the supervisor's audit-trail integrity check.

This convention is enforced by:
- **`implementer` agent** — produces the commit at ship time
- **`supervisor mode: pre-push`** — gates pushes on convention compliance
- **`audit-orchestrator` (Step 6 verifier)** — surfaces violations during release-readiness

If a commit lands without these fields, the harness can't trace it. **Don't bypass the convention. If a finding is too small for full metadata, it's too small for an atomic commit — bundle it into a related finding's commit instead.**

---

## The format

```
<type>(<scope>): <one-line summary> [<finding-id>]

audit: <audit-slug>
roadmap: <phase-id>
finding: <finding-id> (<P0|P1|P2>) — <specialist>
report: <repo-relative path to specialist or synthesis report>
driver: <comma-list of cross-cited specialists>
b-pattern: <pattern-id from qa-engineer.md, comma-list, or n/a>

Verifiable-outcome (pre): <one-line probe + RED state>
Verifiable-outcome (post): <one-line probe + GREEN state>
Regression-check: <patterns spot-checked, e.g. B2/B3/B19 — clean>

<2–3 line body explaining the fix's mechanism — what changed and why this is the right shape>

Co-Authored-By: <as configured by your harness install>
```

## Field-by-field

### Header line

```
<type>(<scope>): <one-line summary> [<finding-id>]
```

- **`<type>`** — one of: `fix`, `feat`, `refactor`, `chore`, `migration`, `test`, `docs`, plus project-specific types (e.g. `i18n`, `rls`, `ai`). Project-specific types are configured by `/init` based on the codebase's existing commit style.
- **`<scope>`** — module slug from `.planning/audits/_context/SUMMARY.md`. Example: `audits`, `risk-register`, `kyc`.
- **`<one-line summary>`** — imperative mood, ≤72 chars including the `[<finding-id>]` suffix. "Add X" not "Added X" or "Adds X".
- **`[<finding-id>]`** — bracketed finding ID at the end of the summary. Repeats the structured `finding:` line below for grep-ability.

### `audit:`

The audit slug that surfaced this finding. Format: `<playbook>/<YYYY-MM-DD>` or `<playbook>/<YYYY-MM-DD>/<scope>`. Examples:

- `audit: foundation-audit/2026-04-26`
- `audit: module-deep-dive/2026-04-26/audits`
- `audit: feature-design/2026-04-26/incident-management`

If the finding wasn't audit-driven (one-off bug fix you noticed yourself), use `audit: ad-hoc/<YYYY-MM-DD>`. The supervisor's pre-push will WARN on `ad-hoc` audits but won't block — they're rare and legitimate.

### `roadmap:`

The roadmap phase this work advances. Format: `phase-<N>` or `post-v<X.Y>`. Examples:

- `roadmap: phase-1`
- `roadmap: phase-3.2`
- `roadmap: post-v1.0`
- `roadmap: hotfix` (for incident-response commits)

If no roadmap exists, use `roadmap: unscoped`. The supervisor will WARN on `unscoped` (recommends adding a roadmap).

### `finding:`

The structured finding ID + severity + originating specialist. Format:

```
finding: <finding-id> (<severity>) — <specialist-name>
```

Examples:
- `finding: F-002 (P0) — qa-engineer`
- `finding: synthesis:#3 (P1) — audit-orchestrator`
- `finding: ai/R-7 (P0) — ai-strategist`
- `finding: wf/W2.5 (P1) — workflow-architect`

The `<finding-id>` MUST match the path of the brief and status file: `.planning/audits/_findings-status/<finding-id>-brief.md` and `.planning/audits/_findings-status/<finding-id>.md`. The supervisor verifies this match.

### `report:`

Repo-relative path to the specialist or synthesis report that originated this finding. Example:

```
report: .planning/audits/qa-engineer/2026-04-26-release.md
```

The supervisor verifies the file exists.

### `driver:`

Comma-list of all specialists who cross-cited this finding. The orchestrator's synthesis Top-N table requires ≥2 specialists per action (R3 + Q3 in the quality bar) — those specialists are the drivers.

```
driver: qa-engineer, regulatory-officer
driver: workflow-architect, ai-strategist, competitive-analyst
```

Single-specialist findings are tactical, not strategic — they should usually be `driver: <specialist>` matching the `finding:` line.

### `b-pattern:`

The historical bug-pattern IDs (from qa-engineer.md) that this commit affects. Comma-list or `n/a`.

```
b-pattern: B2, B3
b-pattern: B17
b-pattern: n/a
```

The supervisor uses `git log --grep "b-pattern: B2"` to track per-pattern fix history. New B-patterns added to qa-engineer.md become greppable from that day forward.

### `Verifiable-outcome (pre)` and `Verifiable-outcome (post)`

The exact probes from the finding's `verifiable_outcome` block — pre-fix RED state and post-fix GREEN state.

```
Verifiable-outcome (pre): SELECT count(*) FROM pg_class WHERE relrowsecurity=false AND relnamespace=(SELECT oid FROM pg_namespace WHERE nspname='public') = 4
Verifiable-outcome (post): same query returns 0
```

These lines are how `tester` re-runs verification at release-readiness time and how `supervisor` re-verifies on `pre-push`. **Don't paraphrase. Copy the probe verbatim from the finding.**

### `Regression-check:`

Patterns spot-checked to confirm the fix didn't reintroduce them. Format:

```
Regression-check: B2 / B3 / B19 — clean
Regression-check: B4 / B17 — clean (frontend touched)
Regression-check: n/a (docs-only commit)
```

The implementer runs the regression check before commit; the tester re-runs it after.

### Body

Two to three lines explaining **the mechanism of the fix** — what changed and why this is the right shape. Not "added validation" — "moved the org_id filter from the service to the repository so RLS policies on the table catch any future caller that bypasses the service." The body is for future-you reading `git log` six months from now.

### `Co-Authored-By:`

Configured by `/init` based on your harness install. Common values:
- `Co-Authored-By: Claude <noreply@anthropic.com>`
- `Co-Authored-By: practice harness <noreply@practice.dev>`

---

## Worked example

A complete commit that ships finding F-002 (a multi-tenant RLS gap on the `audit_findings` table):

```
fix(audits): close RLS gap on audit_findings org-id filter [F-002]

audit: foundation-audit/2026-04-26
roadmap: phase-1
finding: F-002 (P0) — qa-engineer
report: .planning/audits/qa-engineer/2026-04-26-release.md
driver: qa-engineer, regulatory-officer
b-pattern: B2, B3

Verifiable-outcome (pre): SELECT count(*) FROM audit_findings WHERE organization_id != current_org() returned 47 rows for tenant T1 looking at T2's findings
Verifiable-outcome (post): same query returns 0 (cross-tenant select now blocked by RLS policy `audit_findings_org_select`)
Regression-check: B2 / B3 / B5 — clean

Added an `audit_findings_org_select` RLS policy that filters to current_org()
on every SELECT. The previous version relied on the service layer's filter,
which was bypassed by direct supabase-py calls in `report_export_service.py`.
Migration 00146 enables RLS + creates the policy.

Co-Authored-By: Claude <noreply@anthropic.com>
```

Every line is greppable. Every claim is verifiable. Six months from now, `git log --grep "F-002"` returns this commit; `git log --grep "audit: foundation-audit/2026-04-26"` returns this commit and every other commit shipped from that audit; `git log --grep "b-pattern: B2"` returns every RLS-related ship in the project's history.

**That's the audit trail the harness depends on. Don't shortcut it.**

---

## What the supervisor checks (mode: pre-push)

For every commit in the unpushed range:

1. Header line matches `<type>(<scope>): <summary> [<finding-id>]`
2. `audit:` line present and the slug points to a real audit (or `ad-hoc` with WARN)
3. `roadmap:` line present (or `unscoped` with WARN)
4. `finding:` line present and matches `_findings-status/<id>.md`
5. `report:` line present and the file exists
6. `driver:` line present
7. `b-pattern:` line present (can be `n/a`)
8. `Verifiable-outcome (pre)` and `Verifiable-outcome (post)` both present
9. `Regression-check:` present
10. Body has ≥2 lines after the structured fields
11. `Co-Authored-By:` present

Compliance rate is computed as N-of-N. If <95%, supervisor downgrades posture to AMBER. If <80%, supervisor blocks push entirely.

---

## When the convention shouldn't apply

- **Bot commits** (dependabot, etc.) — exempt. Supervisor skips them in the compliance scan.
- **Merge commits** — header line follows git's default; structured fields not required.
- **Initial repo commits** before `/init` ran — exempt; supervisor's pre-push range starts at the install commit.
- **Reverts** — `git revert` produces "Revert <original message>" headers; the supervisor accepts these as-is when the original message followed convention.

Otherwise: **every commit produced by the harness must follow the convention. No exceptions.**

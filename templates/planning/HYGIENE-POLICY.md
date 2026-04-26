# Context Hygiene Policy

The audit-trail must never bloat to the point where reading it destabilises the supervisor that depends on it. This policy defines **retention rules per artefact** so the active working set stays under budget while history remains discoverable.

The supervisor enforces this policy. Run `/supervisor mode: hygiene` to audit and archive; run weekly or whenever total active context exceeds budget.

---

## Token-budget targets (the active working set)

| Artefact | Soft cap | Hard cap |
|----------|----------|----------|
| `SYSTEM-CHANGELOG.md` (active) | 5K tokens | 10K |
| `SESSION-LOG.md` (active) | 8K tokens | 15K |
| `_findings-status/` (active findings only) | 20 findings | 40 |
| Specialist reports (last 90 days) | 30 reports per specialist | 60 |
| Orchestrator synthesis (last 90 days) | 12 syntheses | 25 |

When a soft cap trips, supervisor recommends a hygiene run. When a hard cap trips, supervisor refuses to run any heavy playbook until hygiene runs — the system is in protective mode.

## Retention rules per artefact

### `SYSTEM-CHANGELOG.md` — HSI iteration log

| HSI status | Stays active | Archive trigger | Archive path |
|------------|--------------|-----------------|--------------|
| `APPLIED-PENDING-VERIFICATION` | always | never | — |
| `APPLIED-VERIFIED` | until 14 days stable (no regression) AND ≥3 supervisor passes confirm | 14 days stable + 3 passes | `_archive/hsi/<YYYY-QN>.md` |
| `REFUTED` | until replacement HSI ships | replacement HSI status = APPLIED-PENDING | `_archive/hsi/<YYYY-QN>.md` |
| `REGRESSED — superseded by HSI-NNN` | until successor reaches VERIFIED | successor VERIFIED | `_archive/hsi/<YYYY-QN>.md` |

**Index file:** `SYSTEM-CHANGELOG-INDEX.md` — one line per HSI (active + archived) with: ID, headline, current status, link to detailed entry. Supervisor reads this first; only opens detailed entries when reasoning about a specific hypothesis.

### `SESSION-LOG.md` — append-only session record

| Section | Active retention | Archive trigger | Archive path |
|---------|------------------|-----------------|--------------|
| Recent entries | last 14 days OR last 50 entries (whichever is longer) | older than both | `_archive/sessions/<YYYY-MM>.md` |
| Monthly rollup | always at the top of `SESSION-LOG.md` | regenerated on archive | inline header |

The monthly rollup format (1 line per month):

```
## YYYY-MM rollup
- 12 audits run · 38 findings shipped · 3 escalated (links)
- HSI flips: HSI-001 ✅ · HSI-002 ❌ → HSI-006 · HSI-003 ✅
- Top decisions: <one-liner per major decision>
- Archive: _archive/sessions/<YYYY-MM>.md
```

The active SESSION-LOG.md becomes: monthly rollups (compact) + last 14 days of full entries.

### `_findings-status/<finding-id>.md` and `<id>-brief.md`

| Status | Stays active | Archive trigger | Archive path |
|--------|--------------|-----------------|--------------|
| brief written, not yet shipped | always | never (until shipped) | — |
| shipped + tester PASS | 30 days | 30 days post-PASS | `_archive/findings/<YYYY-MM>/` |
| shipped + tester FAIL (open) | always | becomes ESCALATED → see below | — |
| ESCALATED | always | resolved (PASS) → 30 days post-resolve | `_archive/findings/<YYYY-MM>/` |
| ABANDONED (orchestrator-decided not to ship) | 90 days | 90 days post-decision | `_archive/findings/<YYYY-MM>/` |

**Index file:** `_findings-status/INDEX.md` — one line per finding (active + archived). Supervisor uses this to answer "did we ever ship a fix for X?"

### Specialist reports (per agent)

| Age | Active retention | Archive trigger | Archive path |
|-----|------------------|-----------------|--------------|
| ≤90 days | active | — | — |
| >90 days | summarised | quarterly rollup | `_archive/<specialist>/<YYYY-QN>.md` |

Quarterly rollup format:

```
## <specialist> · <YYYY-QN>
- N reports filed · top finding categories: <list>
- Recurring patterns: <list with HSI-ID references>
- Links to all archived reports.
```

### Orchestrator synthesis

Same rule as specialist reports: ≤90 days active, then quarterly rollup at `_archive/orchestrator/<YYYY-QN>.md`.

The active synthesis directory keeps the most-recent strategic report and any synthesis still cited by an open `_findings-status/` entry.

---

## What hygiene does NOT do

- **Never deletes.** Only moves to `_archive/`. Git history is the ultimate retention.
- **Never edits an entry's content.** Move-and-link only.
- **Never archives an open finding.** A finding with `verifiable_outcome` mismatch on the latest supervisor pass is a load-bearing claim — keep it active until resolved.
- **Never archives an HSI in `APPLIED-PENDING-VERIFICATION`.** That's an open hypothesis the next supervisor pass will test.
- **Never runs during another playbook.** Hygiene is its own session. If `/supervisor mode: hygiene` is invoked while a heavy playbook is mid-flight (detected via SESSION-LOG.md tail), it defers and recommends running after the playbook completes.

---

## Hygiene-run protocol (what `/supervisor mode: hygiene` does)

1. **Read every artefact in `.planning/audits/`.** Compute current token-budget per category against the targets above.
2. **For each over-budget category, identify archive candidates** per the rules.
3. **For each candidate, verify it's safe to archive:**
   - Not referenced by any open finding-status
   - Not cited as the source for any APPLIED-PENDING HSI
   - Not the basis for an active orchestrator synthesis
4. **Move safe candidates** to the appropriate `_archive/` path.
5. **Update indexes:**
   - `SYSTEM-CHANGELOG-INDEX.md` — add archive-link for moved HSIs
   - `_findings-status/INDEX.md` — add archive-link for moved findings
   - Active `SESSION-LOG.md` — regenerate monthly rollup at top
6. **Verify post-state.** Re-compute token-budget per category — must be at or below soft cap.
7. **Append hygiene-run entry to `SESSION-LOG.md`:**

```markdown
## <YYYY-MM-DD HH:MM UTC> — hygiene-run — <verdict>

**Pre-state:** SYSTEM-CHANGELOG <N>K · SESSION-LOG <N>K · findings <N> active · reports <N>
**Archived:**
- <N> HSI entries → `_archive/hsi/<quarter>.md`
- <N> session entries (older than 14d) → `_archive/sessions/<YYYY-MM>.md`
- <N> findings (PASS+30d) → `_archive/findings/<YYYY-MM>/`
- <N> reports (>90d) → `_archive/<specialist>/<quarter>.md`
**Post-state:** SYSTEM-CHANGELOG <N>K · SESSION-LOG <N>K · findings <N> active
**Verdict:** GREEN (under all soft caps) | AMBER (some still over) | RED (hard cap unreachable)
**Notes:** <any artefact that couldn't be archived and why>

---
```

8. **Commit the move.** Hygiene is an atomic operation:

```bash
git add .planning/audits/_archive/ .planning/audits/SYSTEM-CHANGELOG-INDEX.md \
        .planning/audits/_findings-status/INDEX.md .planning/audits/SESSION-LOG.md \
        .planning/audits/SYSTEM-CHANGELOG.md
git commit -m "chore(hygiene): archive <date> — <N> HSIs, <N> sessions, <N> findings"
```

The hygiene commit is the receipt. If hygiene moved something it shouldn't have, `git revert` is the recovery path.

---

## Cadence

- **Manual trigger:** anyone runs `/supervisor mode: hygiene` whenever they suspect bloat.
- **Automatic check:** `/supervisor mode: snapshot` reads token-budget per category. If any category exceeds soft cap, the snapshot's `NEXT MOVE` block recommends `/supervisor mode: hygiene`.
- **Weekly default:** the `/weekly-review` workflow includes a hygiene check as Phase 0; if over soft cap, it runs hygiene before the review starts.
- **Hard cap defence:** if any category exceeds hard cap, the supervisor refuses to run heavy playbooks (`audit-orchestrator scope: foundation-audit`, `production-readiness-gate`, etc.) until hygiene runs. Light playbooks (`mode: latest-run`, `mode: talk:`) still work.

---

## Why this policy exists

The harness compounds. HSIs accumulate. Session logs grow. Without hygiene, the supervisor — which reads these artefacts on every call — eventually spends 30K tokens just reading old context before doing any work. That's how compounding turns into entropy.

This policy is the **anti-entropy lever**. The compounding stays valuable because the active working set stays small.

**Hygiene is not a cleanup chore. It's the maintenance that makes the harness durable.**

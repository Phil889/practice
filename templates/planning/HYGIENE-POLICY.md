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
| `_feature-requests/` (open + triaged + scheduled) | 30 FRs | 60 |
| Specialist reports (referenced by active work) | 30 reports per specialist | 60 |
| Orchestrator synthesis (referenced by active work) | 12 syntheses | 25 |

When a soft cap trips, supervisor recommends a hygiene run. When a hard cap trips, supervisor refuses to run any heavy playbook until hygiene runs — the system is in protective mode.

---

## What "active/upcoming work" means (the cross-reference anchor)

**Don't archive by date alone.** A blunt 14-day timer keeps irrelevant entries and archives still-cited ones. Instead, an artefact stays active when it is referenced by any of:

1. **Open findings** — any `_findings-status/<id>.md` with status `OPEN`, `ESCALATED`, `VERIFIED-PENDING-*`
2. **Pending HSIs** — any `SYSTEM-CHANGELOG.md` entry with status `APPLIED-PENDING-VERIFICATION`, `PROPOSED`, or `REGRESSED`
3. **ROADMAP active phases** — any phase checkbox `[ ]` not yet ticked
4. **Scheduled FRs** — any `_feature-requests/FR-*.md` with status `scheduled` or `triaged`
5. **Current session** — the bottom entry in `SESSION-LOG.md` (always kept)

**Task-complete check:** an artefact's task is "complete" when:
- Finding: status = `VERIFIED` OR `ABANDONED` (no time delay — if it's done, it's done)
- HSI: status = `APPLIED-VERIFIED` + 3 supervisor passes confirmed
- Session entry: all findings/HSIs it references are archived OR have no active cross-references
- Specialist report: not cited by any active finding or HSI

**Archive trigger:** task is complete AND no active cross-reference points to it.

**How to check cross-references:**
- For a **finding ID** `F-XXX`: grep `SESSION-LOG.md` + `SYSTEM-CHANGELOG.md` + active `_findings-status/` files. If found → finding stays active.
- For an **HSI number** `HSI-NNN`: grep `SESSION-LOG.md` + active finding status files + build summaries. If found → HSI stays active.
- For a **session entry**: check if any active finding or HSI cites it (by date or finding IDs listed). If not cited → eligible for archive once its own tasks are complete.

The first time a project switches from time-based to cross-reference-anchored hygiene, expect a 50–70% reduction in active SESSION-LOG size. Nothing is lost — git history has everything; archive just moves from active view to `_archive/`.

---

## Retention rules per artefact

### `SYSTEM-CHANGELOG.md` — HSI iteration log

| HSI status | Stays active | Archive trigger | Archive path |
|------------|--------------|-----------------|--------------|
| `APPLIED-PENDING-VERIFICATION` | always (pending verification) | never | — |
| `APPLIED-VERIFIED` | while referenced by any open finding, active ROADMAP phase, or pending FR | no active cross-reference AND ≥3 supervisor passes confirmed | `_archive/hsi/<YYYY-QN>.md` |
| `REFUTED` | until replacement HSI ships | replacement HSI status = APPLIED-PENDING | `_archive/hsi/<YYYY-QN>.md` |
| `REGRESSED — superseded by HSI-NNN` | until successor reaches VERIFIED | successor VERIFIED AND no active cross-reference | `_archive/hsi/<YYYY-QN>.md` |

**Index file:** `SYSTEM-CHANGELOG-INDEX.md` — one line per HSI (active + archived) with: ID, headline, current status, link to detailed entry. Supervisor reads this first; only opens detailed entries when reasoning about a specific hypothesis.

### `SESSION-LOG.md` — append-only session record

| Section | Active retention | Archive trigger | Archive path |
|---------|------------------|-----------------|--------------|
| Entries cited by active work | always (kept by cross-reference) | citation disappears + task complete | `_archive/sessions/<YYYY-MM>.md` |
| Entries with no citations | while its findings/HSIs are open or pending | all findings/HSIs archived AND entry's own tasks complete | `_archive/sessions/<YYYY-MM>.md` |
| Current session (bottom entry) | always | next session creates newer entry | `_archive/sessions/<YYYY-MM>.md` |
| Monthly rollup | always at the top of `SESSION-LOG.md` | regenerated on archive | inline header |

**How it works in practice:**
- A session entry that shipped `F-XXX` stays active while `F-XXX` status is open. Once `F-XXX` is fully VERIFIED with no cross-references, the entry becomes eligible for archive.
- A session entry that ran a `module-deep-dive` stays active while any finding from that run is OPEN or PENDING-*. Once all findings from that run are archived → entry eligible.
- A session entry whose findings are all archived AND whose HSIs are all verified/archived → archive it, regardless of age.

The monthly rollup format (1 line per month):

```
## YYYY-MM rollup
- 12 audits run · 38 findings shipped · 3 escalated (links)
- HSI flips: HSI-001 ✅ · HSI-002 ❌ → HSI-006 · HSI-003 ✅
- Top decisions: <one-liner per major decision>
- Archive: _archive/sessions/<YYYY-MM>.md
```

The active `SESSION-LOG.md` becomes: monthly rollups (compact) + entries that are either (a) cited by active work or (b) from the current session.

### `_findings-status/<finding-id>.md` and `<id>-brief.md`

| Status | Stays active | Archive trigger | Archive path |
|--------|--------------|-----------------|--------------|
| brief written, not yet shipped | always | never (until shipped) | — |
| shipped + tester PASS | while referenced by active HSI, open ROADMAP phase, or pending FR | not referenced AND 30 days post-PASS | `_archive/findings/<YYYY-MM>/` |
| shipped + tester FAIL (open) | always | becomes ESCALATED → see below | — |
| ESCALATED | always | resolved (PASS) → archive trigger same as PASS above | `_archive/findings/<YYYY-MM>/` |
| ABANDONED (orchestrator-decided not to ship) | until no active cross-reference | no active cross-reference AND 90 days post-decision | `_archive/findings/<YYYY-MM>/` |

**Index file:** `_findings-status/INDEX.md` — one line per finding (active + archived). Supervisor uses this to answer "did we ever ship a fix for X?"

### `_feature-requests/FR-<DOMAIN>-<NNNN>.md` — capability backlog filed by the harness

| FR status | Stays active | Archive trigger | Archive path |
|-----------|--------------|-----------------|--------------|
| `open` (filed, not yet triaged) | 90 days | unreviewed >90d → flagged for triage (NOT archived; supervisor surfaces in next snapshot) | — |
| `open` (>180d unreviewed) | until triaged | auto-rejected by supervisor with reason "stale-unreviewed" → archived 30d later | `_archive/feature-requests/<YYYY-QN>.md` |
| `triaged` | while referenced by active ROADMAP phase or pending HSI | no active cross-reference | — |
| `scheduled` | until shipped or rejected | status change | — |
| `shipped` (linked to commit + finding-ID) | while referenced by active finding or HSI | no active cross-reference AND 30 days post-ship | `_archive/feature-requests/<YYYY-QN>.md` |
| `rejected` (with reason) | 90 days | no active cross-reference AND 90 days post-rejection | `_archive/feature-requests/<YYYY-QN>.md` |

**Index file:** `_feature-requests/INDEX.md` — auto-regenerated by `/supervisor mode: hygiene`. One line per FR (active + archived) with: ID, severity, module, status, link.

**Hygiene actions on FR inbox:**
- Surface FR counts in every system-health snapshot (`open`, `triaged`, `scheduled`, `shipped-pending-archive`).
- Auto-flag FRs with status `open` older than 90d in the snapshot's "needs-attention" block.
- After 180d unreviewed `open`, auto-set status to `rejected` with reason `stale-unreviewed (auto)` — the user can override on review.
- Archive `shipped` FRs when no longer cross-referenced + 30d post-ship; archive `rejected` FRs when no longer cross-referenced + 90d post-rejection.
- Validate frontmatter on every hygiene run (`validate_feature_request_inbox()` in `verify_audit.py`); flag malformed FRs in the snapshot.

### Specialist reports (per agent)

| Active retention | Archive trigger | Archive path |
|------------------|-----------------|--------------|
| while referenced by active finding, active HSI, or open ROADMAP phase | no active cross-reference | quarterly rollup at `_archive/<specialist>/<YYYY-QN>.md` |

Quarterly rollup format:

```
## <specialist> · <YYYY-QN>
- N reports filed · top finding categories: <list>
- Recurring patterns: <list with HSI-ID references>
- Links to all archived reports.
```

### Orchestrator synthesis

Same rule as specialist reports: active while referenced by active work, then quarterly rollup at `_archive/orchestrator/<YYYY-QN>.md`.

The active synthesis directory keeps the most-recent strategic report and any synthesis still cited by an open `_findings-status/` entry.

---

## What hygiene does NOT do

- **Never deletes.** Only moves to `_archive/`. Git history is the ultimate retention.
- **Never edits an entry's content.** Move-and-link only.
- **Never archives an open finding.** A finding with `verifiable_outcome` mismatch on the latest supervisor pass is a load-bearing claim — keep it active until resolved.
- **Never archives an HSI in `APPLIED-PENDING-VERIFICATION`.** That's an open hypothesis the next supervisor pass will test.
- **Never archives a report that is cited by active work.** Cross-reference check is mandatory before archive.
- **Never runs during another playbook.** Hygiene is its own session. If `/supervisor mode: hygiene` is invoked while a heavy playbook is mid-flight (detected via SESSION-LOG.md tail), it defers and recommends running after the playbook completes.

---

## Hygiene-run protocol (what `/supervisor mode: hygiene` does)

1. **Read every artefact in `.planning/audits/`.** Compute current token-budget per category against the targets above.
2. **For each over-budget category, identify archive candidates** per the cross-reference rules above.
3. **For each candidate, verify it's safe to archive:**
   - Not referenced by any open finding-status
   - Not cited as the source for any APPLIED-PENDING HSI
   - Not the basis for an active orchestrator synthesis
   - Not referenced by any open ROADMAP phase or scheduled FR
4. **Move safe candidates** to the appropriate `_archive/` path.
5. **Update indexes:**
   - `SYSTEM-CHANGELOG-INDEX.md` — add archive-link for moved HSIs
   - `_findings-status/INDEX.md` — add archive-link for moved findings
   - `_feature-requests/INDEX.md` — regenerate from current inbox + archived FRs (one line per FR with ID, severity, module, status, link)
   - Active `SESSION-LOG.md` — regenerate monthly rollup at top
6. **Verify post-state.** Re-compute token-budget per category — must be at or below soft cap.
7. **Append hygiene-run entry to `SESSION-LOG.md`:**

```markdown
## <YYYY-MM-DD HH:MM UTC> — hygiene-run — <verdict>

**Pre-state:** SYSTEM-CHANGELOG <N>K · SESSION-LOG <N>K · findings <N> active · FRs <N> open / <N> shipped-pending · reports <N>
**Archived:**
- <N> HSI entries → `_archive/hsi/<quarter>.md`
- <N> session entries (no cross-references + task complete) → `_archive/sessions/<YYYY-MM>.md`
- <N> findings (VERIFIED + not referenced) → `_archive/findings/<YYYY-MM>/`
- <N> FRs (shipped/rejected + not referenced) → `_archive/feature-requests/<YYYY-QN>.md`
- <N> reports (no active cross-reference) → `_archive/<specialist>/<quarter>.md`
**Auto-rejected:** <N> stale-unreviewed FRs (>180d open) → status: rejected, reason: stale-unreviewed (auto)
**Post-state:** SYSTEM-CHANGELOG <N>K · SESSION-LOG <N>K · findings <N> active · FRs <N> open
**Verdict:** GREEN (under all soft caps) | AMBER (some still over) | RED (hard cap unreachable)
**Notes:** <any artefact that couldn't be archived and why>
```

8. **Commit the move.** Hygiene is an atomic operation:

```bash
git add .planning/audits/_archive/ .planning/audits/SYSTEM-CHANGELOG-INDEX.md \
        .planning/audits/_findings-status/INDEX.md .planning/audits/_feature-requests/INDEX.md \
        .planning/audits/SESSION-LOG.md .planning/audits/SYSTEM-CHANGELOG.md
git commit -m "chore(hygiene): archive <date> — <N> HSIs, <N> sessions, <N> findings, <N> FRs"
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

### Key principle: archive by relevance, not by age

Old doesn't mean useless. A 30-day-old session entry that is cited by an open ROADMAP phase stays active. A 2-day-old entry whose findings are all archived and whose HSIs are all verified with no cross-references gets archived immediately.

The question is never *"how old is it?"* — it's always *"is something active still pointing to it?"*

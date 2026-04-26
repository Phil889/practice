# Session Log

**Append-only record of every audit, build, workflow, and supervisor run in this project.**

The supervisor reads this file end-to-end on every invocation — it's the harness's working memory across sessions. Don't edit prior entries. Don't reorder. Newest entries at the bottom.

The hygiene policy keeps this file under budget: entries older than 14 days (or beyond the last 50 entries, whichever is more recent) roll up into the monthly summaries below; full entries archive to `_archive/sessions/<YYYY-MM>.md`.

---

## Monthly rollups

(The supervisor regenerates this section on every `mode: hygiene` run. Do not edit by hand.)

<!-- ROLLUPS-START -->
<!-- ROLLUPS-END -->

---

## Active entries

(Last 14 days OR last 50 entries, whichever is more recent. New runs append below.)

<!-- ACTIVE-START -->
<!-- ACTIVE-END -->

---

## Entry templates

When appending an entry, copy the template that matches the playbook + replace bracketed values.

### Audit-orchestrator entry

```markdown
## <YYYY-MM-DD HH:MM UTC> — audit:<scope-slug> — <verdict>

**Playbook:** <foundation-audit | release-readiness | feature-design | module-deep-dive | ...>
**Scope:** <full parameter>
**Specialists:** <comma-list>
**Verdict:** <PASS / PASS-WITH-WARNINGS / FAIL / HARD-FAIL>
**Reports written:**
- `.planning/audits/orchestrator/<date>-<slug>.md`
- `.planning/audits/<specialist>/<date>-<slug>.md` × <N>
- `.planning/audits/audit-verifier/<date>-<slug>.md`

**Top-3 findings:** <F-001, F-002, F-003 with one-line headlines>
**Context budget:** ~<N>K tokens consumed
**Recommended next:** <playbook + scope OR "break session">
**Why break (if applicable):** <heuristic that triggered>
**Open threads:** <unresolved items>

---
```

### Build-loop entry

```markdown
## <YYYY-MM-DD HH:MM UTC> — build:<scope-slug> — <verdict>

**Source:** <report-path>
**Findings:** <P>/<N> shipped + verified · <F> failed · <E> escalated
**Reports written:**
- `.planning/audits/orchestrator/<date>-build-<slug>.md`
- `.planning/audits/_findings-status/<id>.md` × <N>

**Commits:** <sha-list>
**Verdict:** GREEN | AMBER | RED
**Recommended next:** <push to remote → release-readiness scoped to module> | <re-dispatch escalated> | <break>
**Open threads:** <escalated findings + reasons>

---
```

### Workflow entry

```markdown
## <YYYY-MM-DD HH:MM UTC> — workflow:<name> · <key-input> — <verdict>

**Workflow:** <name>
**Inputs:** <inputs as comma-list>
**Phase verdicts:** P1=<v> · P2=<v> · P3=<v> · P4=<v> · P5=<v>
**Final verdict:** GREEN | AMBER | RED
**Reports written:** <link to workflow report>
**Recommended next:** <next workflow or break>

---
```

### Supervisor entry

```markdown
## <YYYY-MM-DD HH:MM UTC> — supervisor · <mode> — <posture>

**Mode:** <snapshot | latest-run | weekly-review | pre-push | hygiene | talk | ...>
**Posture:** GREEN | AMBER | RED
**HSI flips:** <list with verdicts>
**Open questions:** <list>
**Next move:** <one-line recommendation>

---
```

### Hygiene-run entry

```markdown
## <YYYY-MM-DD HH:MM UTC> — hygiene-run — <verdict>

**Pre-state:** SYSTEM-CHANGELOG <N>K · SESSION-LOG <N>K · findings <N> active · reports <N>
**Archived:**
- <N> HSI entries → `_archive/hsi/<quarter>.md`
- <N> session entries (>14d) → `_archive/sessions/<YYYY-MM>.md`
- <N> findings (PASS+30d) → `_archive/findings/<YYYY-MM>/`
- <N> reports (>90d) → `_archive/<specialist>/<quarter>.md`
**Post-state:** SYSTEM-CHANGELOG <N>K · SESSION-LOG <N>K · findings <N> active
**Verdict:** GREEN (under all soft caps) | AMBER (some still over) | RED (hard cap unreachable)
**Notes:** <any artefact that couldn't be archived and why>

---
```

---

## Why this file matters

The session log is the **harness's working memory across sessions**. A new Claude session that opens cold can't reconstruct what happened yesterday — but it can read this file and pick up where the last session left off. The supervisor depends on this; the orchestrators depend on this; you depend on this.

**Three rules:**

1. **Append, never edit.** History is sacred. If a run made a mistake, the next run logs the mistake-and-correction; you don't rewrite the past.
2. **Use the templates above.** The supervisor's parser scans for specific fields. Free-form entries break that parser.
3. **Newest at the bottom.** Top of file is the rollups + active marker. New runs are appended after the `<!-- ACTIVE-START -->` block.

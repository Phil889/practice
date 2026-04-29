# Changelog

All notable changes to `practice` get a numbered version + date here. Versions are git-tagged.

Format: [version] — date · one-line summary, followed by What's new / Affected templates / Migration notes (if any).

---

## [0.11.0] — 2026-04-29 · Harness robustness: auto-vocabulary, brief ceilings, warm-start, specialist heuristic

Five field-validated improvements ported from the production Zenith harness. All reduce token waste and eliminate recurring maintenance friction without sacrificing audit-grade quality.

### What's new

**`verify_audit.py` — Auto-vocabulary extraction from agent specs.**
The verifier now auto-discovers required section headings from agent `.md` specs' output templates. Eliminates false-positive FAILs when specialists use heading vocabulary that drifts from `REQUIRED_SECTIONS`. Two new capabilities:

- `--refresh-patterns` CLI flag: scan all agent specs in `.claude/agents/` and report headings not yet covered by `REQUIRED_SECTIONS`. Run after adding/editing specialists.
- Auto-warning on every verification run: if gaps exist, prints a non-blocking warning to stderr.

**`build-loop` SKILL — Brief size ceiling (8 KB body).**
Briefs now have a hard cap of 8 KB. When the specialist's finding text would push the brief over 8 KB, the orchestrator switches to citation-only format (reference to the source report, not verbatim quote). Saves ~500-1000 tokens per dispatch. The ceiling is validated after each brief write; oversized briefs are automatically rewritten.

**`build-loop` SKILL — Sub-directory convention for complex findings.**
When a finding decomposes into >3 sub-findings, use a sub-directory with `INDEX.md` instead of flat naming. Keeps `_findings-status/` scannable as the project scales past 50+ findings.

**`supervisor` SKILL — `mode: warm-start` (lightweight mid-session resumption).**
New mode for returning after a short break (<4 hours, same session). Reads only the last SESSION-LOG entry + verifies HEAD matches expectations. ~1.5K tokens vs ~5K for full `mode: snapshot`. Auto-escalates to `snapshot` if HEAD diverged.

**`audit-orchestrator` SKILL — Specialist relevance heuristic.**
Before Phase 1 dispatch in `module-deep-dive`, the orchestrator evaluates each specialist's expected marginal value using a specialist × module affinity matrix. Tertiary-domain specialists may be skipped if prior coverage exists (<90 days old). `qa-engineer` and compliance specialists are NEVER skippable. First-ever module-deep-dive always dispatches full roster. Expected savings: ~15-20% token reduction on subsequent runs.

### Affected templates

- `templates/planning/verify_audit.py` — auto-vocabulary extraction + `--refresh-patterns` CLI
- `templates/planning/quality-bar.md` — maintenance section references `--refresh-patterns`
- `templates/skills/build-loop/SKILL.md` — brief size ceiling + sub-directory convention
- `templates/skills/supervisor/SKILL.md` — `mode: warm-start` protocol
- `templates/skills/audit-orchestrator/SKILL.md` — specialist relevance heuristic in `module-deep-dive`

### Migration notes (existing v0.10.x installations)

1. **Re-run `/init` is NOT required.** All changes augment existing specs.
2. **`verify_audit.py`:** Replace your `.planning/audits/_context/verify_audit.py` with the new template. The new version is backwards-compatible — existing verification runs produce identical results; `--refresh-patterns` is additive.
3. **Build-loop brief ceiling:** Copy the `### Brief size ceiling` and `### Sub-directory convention` sections from `templates/skills/build-loop/SKILL.md` into your `.claude/skills/<your-build-loop>/SKILL.md` after the brief filename convention paragraph.
4. **Supervisor warm-start:** Copy the `### mode: warm-start` section from `templates/skills/supervisor/SKILL.md` into your `.claude/skills/<your-supervisor>/SKILL.md` mode list.
5. **Specialist heuristic:** Copy the `### Specialist relevance heuristic` section from `templates/skills/audit-orchestrator/SKILL.md` into your `.claude/skills/<your-orchestrator>/SKILL.md` under the `module-deep-dive` playbook. Customize the affinity matrix for your domain's specialists.

---

## [0.10.1] — 2026-04-28 · Token-efficiency: TL;DR specialist sections + lighter brief format

Two surgical specs that reduce per-cycle token spend by ~30-50% with zero quality loss. Both ship as field-validated optimizations after observing 6+ weeks of real audit + ship cycles.

### What's new

**Specialist agents — REQUIRED `## TL;DR` section.**
Every specialist (qa-engineer, audit-verifier, and any project-domain specialist generated via `_specialist-template.md`) now writes a TL;DR section as the first block of its output:

- Top 3 findings (most-load-bearing first), each ≤30 words
- Confidence (low / medium / medium-high / high)
- Re-dispatch flag (none, or "consider re-dispatch if X")
- ≤500 tokens total

**Why:** the orchestrator currently reads ~25-50K tokens to synthesize 5 specialist reports. With TL;DRs at the top, orchestrator reads ~5K of TL;DRs first and only drills into specific sections when synthesis needs detail. **~50-70% token reduction in the synthesis phase, no quality loss** (the underlying detail is still on disk if needed).

**`build-loop` SKILL — Lighter brief format.**
The per-finding brief no longer includes verbatim quotes from specialist reports. Instead, briefs reference the source via citation + one-line summary:

- `## Source` block: citation `<report-path>:§<finding-id>` + ≤30-word load-bearing-problem summary (was: full one-paragraph verbatim quote)
- `## Recommended fix` block: citation + ≤2-line approach summary (was: full verbatim quote of the specialist's "Fix" or "Recommendation" block)

**Why:** implementer reads the brief and follows the citation back to the original report when context is needed. Today's verbatim quotes mostly get ignored. Lighter briefs save **~500-1000 tokens per dispatch**, no quality loss (citation still leads to the source).

### Affected templates

- `templates/agents/_specialist-template.md` — TL;DR section added before the Output schema
- `templates/agents/qa-engineer.md` — same
- `templates/agents/audit-verifier.md` — TL;DR adapted for verifier output (Verdict + Quality bar + Re-dispatch)
- `templates/skills/build-loop/SKILL.md` — Source + Recommended fix blocks lightened (citations + summaries)

### Migration notes (existing v0.10.0 installations)

1. **Re-run `/init` is NOT required.**
2. **Manually copy the new sections** if you want the savings immediately:
   - From `templates/agents/_specialist-template.md` to your `.claude/agents/<each-specialist>.md`: the `## TL;DR (REQUIRED)` block right after `# Output`.
   - From `templates/agents/audit-verifier.md` to your `.claude/agents/audit-verifier.md`: the verifier-specific TL;DR block.
   - From `templates/skills/build-loop/SKILL.md` to your `.claude/skills/<your-build-loop>/SKILL.md`: replace the `## Source` and `## Recommended fix` blocks with the citation+summary versions.
3. **First audit run after the upgrade** will surface specialists' compliance with the new TL;DR rule. Specialists that miss it: re-dispatch with explicit reminder. After ~3 runs the rule sticks.

---

## [0.10.0] — 2026-04-28 · Worktree base-ref discipline + atomic-commit (a)-pattern + bundled-commit convention

Six months of harness iteration in real ship-clusters surfaced three patterns the v0.9.0 templates didn't yet codify. v0.10.0 promotes them from field-tested to canonical.

### What's new

**`build-loop` SKILL — Step 3a-pre: Pre-dispatch base-ref refresh.**
The Agent runtime's `isolation: "worktree"` snapshots from the parent's HEAD at dispatch-time and does not refresh between phases. If the parent's HEAD lags `origin/<dev-branch>`, every implementer inherits a stale base — causing migration-filename collisions, stale-content cherry-pick conflicts, and silent bugs where an implementer thinks an earlier-phase commit isn't on disk yet. Three consecutive ship-clusters manifested this before codification. Now:

- Orchestrator runs `git fetch && git pull --ff-only` and captures `BASE_REF` BEFORE Phase 1 dispatch and BETWEEN phases.
- Implementer prompt now includes a **canonical pre-edit rebase** (`git fetch && git rebase BASE_REF`) as the FIRST action, not a fallback. Costs ~0 wall-clock when the snapshot is fresh; saves ~2 min/dispatch when it's stale.
- Implementer prompt also carries a **falsifier-of-last-resort assertion** (`git merge-base HEAD BASE_REF`) — if the rebase claimed success but the assertion still diverges, abort BEFORE any edit and ESCALATED. Defence-in-depth.
- Build PLAN template gains a `## Pre-flight` section recording `BASE_REF`.

**`implementer` agent — Step 6.1: The status-file (a)-pattern.**
The status file at `.planning/audits/_findings-status/<finding-id>.md` cannot reference its own commit SHA before the commit exists. Resolving with a `Commit: (pending)` placeholder or `git commit --amend` after-the-fact breaks `git log --grep` reproducibility and audit-trail integrity. New rule:

- **The status file is NEVER staged in the feat commit.** Step 6 ships the code/migration only.
- After the feat commit lands, Step 7 captures the SHA via `git rev-parse --short HEAD`, writes the status file with the SHA filled in (no placeholders), and ships it as a **separate atomic commit** (`docs(<scope>): finalise <finding-id> status file [<finding-id>]`).
- The bracketed `[<finding-id>]` on both commits restores `git log --grep "<finding-id>"` returning both — bidirectional cross-reference preserved.
- The docs commit's body has a `ship-commit:` line pointing back to the Step 6 SHA.
- For cluster commits: one docs commit per finding-ID, all pointing to the same Step 6 cluster SHA.

**`implementer` agent — Step 6.4: Schema-Bundle Exception (the only legitimate path for multi-finding commits).**
Sometimes 2+ findings share logically inseparable schema work (a column-add + CHECK + trigger function on the same table; a coupled domain-model + frontend-type that must land atomically). Splitting them corrupts the migration. New rule:

- The build PLAN must pre-authorize the consolidation with a "Migration consolidation" section naming bundled findings + why splitting would corrupt them.
- Commit subject lists ALL bundled finding-IDs in brackets: `[F-001+F-004+F-006-schema]`. This restores `git log --grep "<finding-id>"` for every bundled finding.
- Body has `additional-findings:` line listing non-primary findings explicitly.
- Body has `consolidation-rationale:` line citing the PLAN section.
- Each consolidated finding gets its own status-file marked `BUNDLED`.
- Per-finding service/UI commits remain atomic — only the schema bundles.
- **Unintentional bundling is still a violation** (the pre-stage `git status --short` validation in §6.0 should have caught it). The Schema-Bundle Exception only applies when the PLAN explicitly authorized it.

**`implementer` agent — Step 6.5: Retry commit format.**
When the tester FAILed and the implementer re-ships, the new commit format includes `retry-of:` (prior SHA) and `retry-reason:` (verbatim from tester's `### Failure delta`). Subject reads `[F-002 retry-1]`.

**README — Recommended companions section.**
Lists the Karpathy guidelines plugin as a soft prerequisite — the build-loop's behavioural assumptions lean on the discipline it provides. Not required, but recommended.

### Affected templates

- `templates/skills/build-loop/SKILL.md` — Step 2 PLAN template, Step 3a-pre (NEW), Step 3a implementer prompt
- `templates/agents/implementer.md` — Step 6 (rewritten — (a)-pattern, Schema-Bundle Exception, Retry format), Step 7 (rewritten — separate docs commit)
- `README.md` — Recommended companions section (NEW)

### Migration notes (existing v0.9.0 installations)

If you've already run `/init` and your harness scaffolded against v0.9.0:

1. **Re-run `/init` is NOT required.** v0.10.0 changes don't break v0.9.0 specs — they augment them.
2. **Manually copy the new sections** if you want the discipline immediately:
   - From `templates/skills/build-loop/SKILL.md` to your `.claude/skills/build-loop/SKILL.md`: Step 3a-pre (Pre-dispatch base-ref refresh) and the implementer prompt update in Step 3a.
   - From `templates/agents/implementer.md` to your `.claude/agents/implementer.md`: Step 6 (the (a)-pattern + Schema-Bundle Exception + retry format) and Step 7 (separate docs commit).
3. **First ship after the upgrade** will surface any drift the new rules catch. Read the implementer's status file's `### Pre-flight` section if it ESCALATEDs — that's the falsifier-of-last-resort firing, working as designed.

---

## [0.9.0] — 2026-04-26 · Initial public release

First public scaffold:

- 3 orchestrator skills (`audit-orchestrator`, `build-loop`, `supervisor`) + 4 universal agent templates (`qa-engineer`, `audit-verifier`, `implementer`, `tester`) + 1 specialist base + 1 worked example specialist (`regulatory-officer`).
- 5 workflow templates (`release-readiness`, `audit-and-ship`, `weekly-review`, `incident-response`, `feature-launch`).
- Planning templates: `quality-bar` (R1–R5 spec), `HYGIENE-POLICY`, `SESSION-LOG`, `SYSTEM-CHANGELOG`, `_findings-status` README + INDEX, `refresh.py`, `verify_audit.py`.
- `install.sh` with sanity checks + clone-in-place mode.
- `/init` bootstrapper (5-phase: Discovery → Interview → Team design → Generate → Smoke test).
- README with PNG hero, examples, four-tier architecture explanation.

# Example: a real HSI self-improvement run

This is a real run from a project running `practice` in production — anonymised slightly (project-specific module names → generic placeholders) but otherwise verbatim.

It shows what the harness's self-improvement loop actually produces. **No marketing claims; just the artefacts on disk.**

---

## The setup

After 4 audit playbooks ran on 2026-04-26 (a foundation-audit, a module-deep-dive on `<module-A>`, a feature-design on `<feature-X>`, and a release-readiness on `<module-A>`), the supervisor noticed something:

- **Qualitative `audit-verifier` verdict on all 4 runs:** PASS-WITH-WARNINGS
- **Deterministic `verify_audit.py` verdict on all 4 runs:** FAIL

That gap is the harness lying to itself. Every run, the supervisor had to override the deterministic verdict with the qualitative one. **The deterministic verifier was producing 100% false-FAILs.**

The supervisor proposed an HSI:

```
HSI-006 — verify_audit.py deterministic-verifier defect cluster
Status: PROPOSED
```

## The hypothesis

> If `verify_audit.py` is patched to handle the 10 specific defects observed across the 4 runs (parser tolerance, scope-aware overrides, citation-resolution paths, slug-filename aliases), the deterministic verdict matches the qualitative verdict on every run. False-FAIL rate drops from 100% to 0%.

The 10 defects (D1–D10) were classified individually:

| Defect | Class | Example |
|--------|-------|---------|
| D1 | parser-too-strict | `## Self-Check (R4)` not matched by `^## Self-Check$` |
| D2 | scope-blind | release-readiness has different required sections than foundation-audit; verifier treated all scopes the same |
| D3 | over-eager-citation-detection | bare filename `SUMMARY.md` mentioned in prose was treated as a code citation |
| D4 | over-eager-specialist-check | release-readiness only requires qa+regulatory; verifier WARNed on missing workflow-architect peer |
| D5 | parser-too-strict | `Confidence: **high**` (bold) not matched by literal regex |
| D6 | date-collision | reports from a prior same-date run treated as in-scope and section-checked |
| D7 | citation-overreach | `.md` cross-reference paths (audit-trail pointers) treated as source-code citations |
| D8 | greedy-substring-match | `module-deep-dive-<module-A>` greedily picked `release-readiness-<module-A>` filename |
| D9 | filename-divergence | foundation-audit specialists write to `<date>-full.md` but qa-engineer writes to `<date>-release.md` |
| D10 | path-resolution-too-narrow | reports cited `models/dsgvo.py` (relative) but file lives at `backend/app/models/dsgvo.py` |

Each defect was traced to the run that surfaced it, and the fix was tested against that run.

## The verification probe

```bash
python .planning/audits/_context/verify_audit.py 2026-04-26 --slug <each of 4 slugs>
```

**PASS condition:** all 4 produce `PASS` or `PASS-WITH-WARNINGS` matching the qualitative verdict on disk.
**FAIL condition:** any run produces `FAIL` or `HARD-FAIL` while qualitative said PASS-WITH-WARNINGS.

## The result

| Run | Pre-fix verdict | Post-fix verdict | Qualitative match |
|-----|-----------------|------------------|-------------------|
| `foundation-audit` | FAIL (5 missing-file fails) | PASS-WITH-WARNINGS (1 R1 nit) | ✓ |
| `module-deep-dive:<module-A>` | FAIL (12 fail / 1 warn) | PASS-WITH-WARNINGS (2 R1 nits) | ✓ |
| `feature-design:<feature-X>` | FAIL (18 fails) | PASS-WITH-WARNINGS (1 R1 nit) | ✓ |
| `release-readiness:<module-A>` | FAIL (17 fail / 5 warn) | PASS-WITH-WARNINGS (1 R1 nit) | ✓ |

**Verdict: ✅ HYPOTHESIS-VERIFIED**

False-FAIL rate: 100% → 0%.

The supervisor flipped HSI-006's status to `APPLIED-VERIFIED` and appended this verification block to `SYSTEM-CHANGELOG.md` (per the hygiene policy, the entry stays active for 14 days + 3 supervisor passes before archive eligibility).

## What the supervisor *didn't* claim

The remaining warnings on the post-fix runs are real. They're R1-citations-resolve nits in the report **content** — specialists referenced relative paths like `dashboard/<module>/page.tsx` without the framework's full path prefix. The supervisor explicitly noted:

> *"All remaining warns are R1-citations-resolve nits in the **report content** — not script defects. The deterministic verifier now matches the qualitative verifier on every run."*

It could have claimed clean PASS. It didn't, because the warnings are real and orthogonal to the HSI hypothesis. **That's audit-grade self-honesty.**

The warnings spawned a separate proposal (a new HSI on the specialists' citation conventions) for a future run.

## The commit

The fix shipped as one atomic commit following the harness's own commit-message convention:

```
fix(harness): HSI-006 — verify_audit.py defect cluster D1–D10
              (4/4 historical runs FAIL → PASS-WITH-WARNINGS)

audit: release-readiness:<module-A>/2026-04-26 (verifier surfaced D1–D4)
       feature-design:<feature-X>/2026-04-26 (re-confirmed D1–D4)
roadmap: harness-self-improvement
finding: HSI-006

Verifiable-outcome (pre): all 4 runs FAIL, qualitative PASS-WITH-WARNINGS — 100% false-FAIL
Verifiable-outcome (post): all 4 runs PASS-WITH-WARNINGS — qualitative match
Regression-check: D1–D10 each tested against the run that surfaced it; no
specialist or scope was over-relaxed (all severity/citation/section gates
still fire on genuine R1/R2/R4 defects in report content)

[2-3 paragraphs explaining the mechanism of each defect class]

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

`git log --grep "HSI-006"` returns this single commit. `git log --grep "audit-trail integrity"` returns every harness-improvement commit ever shipped. **The audit trail is greppable, by design.**

## What this proves

1. **The compounding is real.** Each HSI iteration is measured against a probe; either the probe matches the hypothesis (VERIFIED) or it doesn't (REFUTED). No vibes, no claims.

2. **The supervisor is honest under pressure.** It surfaced PASS-WITH-WARNINGS — not PASS — because warnings still existed even after the verified hypothesis. *A tool that claims clean victories isn't a tool you trust.*

3. **The defect-cluster pattern is replicable.** D1–D10 weren't ten random tweaks; they were ten testable hypotheses, each tied to the run that produced its evidence, each verifiable independently. Future verify_audit.py iterations can reuse the same pattern.

4. **The harness improves itself without dropping standards.** The fix didn't bypass any quality-bar rule. It made the deterministic verifier match the qualitative verifier — closing the gap, not lowering the bar.

## Try it yourself

After running `/init` on your project, your harness will produce its own HSIs as it encounters its own friction. **You don't author them yourself; the supervisor proposes them, the build-loop ships them, the next supervisor pass verifies them.**

Open `SYSTEM-CHANGELOG.md` after a few weeks. **You'll see the compounding on disk.**

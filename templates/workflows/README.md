# Workflows

Workflows are the **third tier of the practice harness**, above skills and agents. They chain multiple skills and agents into a single user-facing command so the user doesn't have to remember which skill, in what order, with what scope.

## When to add a new workflow

A workflow earns its place in `/workflows/` when:

1. **You run the same multi-skill recipe more than 3 times.** Two times is coincidence; three is a pattern.
2. **The order matters and is non-obvious.** A new project lead should not have to discover it from a session log.
3. **The recipe has a gate.** It produces a GO/NO-GO or PASS/FAIL verdict that downstream work depends on.

If the recipe is just two skills back-to-back with no gate, document it in the README, don't promote it to a workflow. Workflow files are not free — they have to be maintained.

## Workflow vs skill mode vs orchestrator scope

| Construct | Lives in | Purpose | Example |
|-----------|----------|---------|---------|
| **Workflow** | `.claude/workflows/<name>.md` | Chain ≥2 skills with a gate | `/release-readiness` (build-loop verify → audit-orchestrator → supervisor pre-push → GO/NO-GO) |
| **Skill mode** | inside one skill's `mode:` arg | Variant inside one skill | `/supervisor mode: weekly-review` |
| **Orchestrator scope** | inside `audit-orchestrator` or `build-loop` | Decompose into specialist invocations | `/audit-orchestrator scope: foundation-audit` |

The user invokes all three the same way (`/<command>` in Claude Code), but you (the engineer) make the architectural choice when building.

## Shipped workflows

| Workflow | When to run | Chains |
|----------|-------------|--------|
| `/release-readiness` | After implementation, before push | tester re-run → audit-orchestrator release → supervisor pre-push → GO/NO-GO |
| `/audit-and-ship` | Per-module weekly cycle | audit-orchestrator module-deep-dive → audit-verifier → build-loop → release-readiness |
| `/weekly-review` | End of every week | supervisor weekly-review → backlog burn → roadmap drift check → next-week plan |
| `/incident-response` | When something breaks in production | qa-engineer pattern scan → build-loop ship-cluster → release-readiness → supervisor post-incident |
| `/feature-launch` | Per new feature | audit-orchestrator feature-design → build-loop ship → release-readiness → supervisor pre-push |

## Adding your own workflow

```bash
cp templates/workflows/_workflow-template.md .claude/workflows/<your-name>.md
```

Fill in:
1. Frontmatter (name, description, user-invocable)
2. The phase diagram (workflows have 3–5 phases by convention)
3. Per-phase dispatch logic (which skill/agent, what scope/mode/args)
4. The synthesis verdict format
5. Anti-patterns specific to misuse of this workflow

The supervisor will pick up new workflows on next `/supervisor mode: snapshot` and surface them in its "next move" recommendations when the trigger conditions match.

## Anti-patterns for workflow design

- **Don't chain three skills if two would do.** Workflows are about removing decisions from the user, not adding ceremony.
- **Don't make workflows that can't fail.** A workflow without a GO/NO-GO gate is just a script — make it a slash-command on a skill instead.
- **Don't bury the verdict.** Phase 5 (or whichever is last) must produce a single-word verdict the user reads first.
- **Don't run sub-workflows without telling the user.** Workflows that dispatch other workflows confuse the audit trail. If you need that depth, refactor into a single workflow with more phases.
- **Don't write workflows that mutate code.** Workflows orchestrate; they don't edit. The implementer agent edits.

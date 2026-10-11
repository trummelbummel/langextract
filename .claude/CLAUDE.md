# Project GSD instructions

This file is the GSD `claude_md_path` target. Style rules for the Python
library live in the repo-root `CLAUDE.md`.

## Post-plan review gate

After every GSD **phase plan/wave** or **`/gsd-quick`** task finishes and its
SUMMARY is committed:

1. Run the **post-plan-review** skill (`gsd-post-plan-review` /
   `capabilities/post-plan-review`). Do not start the next plan or quick task
   first.
2. That skill runs, in order:
   - **style-review** (incl. R15 HITL) → commit fixes + `{id}-STYLE-REVIEW.md`
   - **dedup-review** → commit fixes + `{id}-DEDUP-REVIEW.md`
   - **human commit review** — list commits, wait for `approved` or `undo`
3. On `undo`: phase plans → `/gsd-undo --plan {id}`; quick ids → confirmed
   `git revert` of that quick_id's commits. Then stop.
4. On `approved`, only then continue.

### How it is wired

- Config: `workflow.post_plan_review: true` (keep `workflow.auto_advance: false`).
- Capability hooks:
  - `execute:wave:post` → after each execute-phase wave
  - `execute:post` → after hosts that render this point (including
    `/gsd-quick --full`, where Step 6.25 runs)
- **Plain `/gsd-quick` (no `--full`):** GSD skips Step 6.25, so no native
  `execute:post` dispatch. **Still run this skill yourself** after
  `{quick_id}-SUMMARY.md` is committed — this CLAUDE.md rule is the gate.
- Manual: `/gsd-post-plan-review` or `/post-plan-review`.
- Prefer `/gsd-execute-plan NN-MM` over `/gsd-execute-phase` when reviewing
  one phase plan at a time.

### Install / refresh the capability

```bash
node ~/.claude/gsd-core/bin/gsd-tools.cjs capability install ./capabilities/post-plan-review --yes
```

Source: `capabilities/post-plan-review/`.
Cursor skill: `.claude/skills/gsd-post-plan-review/`.

# post-plan-review capability

GSD overlay that runs after execution:

1. **style-review** → commit + artifact
2. **dedup-review** → commit + artifact
3. **human commit gate** (`approved` / `undo`)

## Hooks

| Point | When it fires |
|-------|----------------|
| `execute:wave:post` | After each execute-phase wave |
| `execute:post` | After hosts that dispatch this point (e.g. `/gsd-quick --full`) |

Plain `/gsd-quick` without `--full` skips GSD's Step 6.25, so the project's
`.claude/CLAUDE.md` still requires running this skill after the quick SUMMARY.

## Install

```bash
node ~/.claude/gsd-core/bin/gsd-tools.cjs capability install ./capabilities/post-plan-review --yes
node ~/.claude/gsd-core/bin/gsd-tools.cjs config-set workflow.post_plan_review true
```

Verify:

```bash
node ~/.claude/gsd-core/bin/gsd-tools.cjs loop render-hooks execute:wave:post --raw
node ~/.claude/gsd-core/bin/gsd-tools.cjs loop render-hooks execute:post --raw
```

Both should list `capId: "post-plan-review"` with `kind: "step"`.

## Layout

- `capability.json` — manifest
- `skills/post-plan-review/SKILL.md` — procedure

Keep `.claude/skills/gsd-post-plan-review/SKILL.md` in sync when editing.

---
name: post-plan-review
description: >
  After a GSD plan/wave or gsd-quick task finishes: run style-review, then
  dedup-review, commit any fixes and review artifacts, then pause for human
  commit review (approved or undo) before continuing. Invoked at
  execute:wave:post / execute:post when workflow.post_plan_review is true, or
  via /post-plan-review.
---

<objective>
Close the loop after executor commits: polish the diff with style + dedup
reviews (committed), then give the human a clean commit list to approve or undo
before any further plan or quick task runs.
</objective>

<required_skills>
Resolve these paths (prefer project, then user home):

1. Style: `$HOME/.claude/skills/style-review/SKILL.md`
2. Dedup: `$HOME/.claude/skills/dedup-review/SKILL.md`

If a path is missing, STOP and tell the user to install that skill. Do not skip
either review when both are available.
</required_skills>

<inputs>
Resolve from the host context:

**Phase / wave (execute-phase):**
- `PHASE_NUMBER`, `PLAN_IDS`, `PHASE_DIR` (`.planning/phases/<phase-dir>/`)

**Quick (gsd-quick):**
- `quick_id` — e.g. from init.quick
- `QUICK_DIR` / `task_dir` — `.planning/quick/<quick_id>-<slug>/`
- Treat `PLAN_IDS = [quick_id]` and artifact dir = `QUICK_DIR`

If none of these can be resolved, ask the user which plan id or quick_id to review.
</inputs>

<process>

<step name="1_scope_commits">
For each id in `PLAN_IDS` (phase plan id or `quick_id`):

```bash
git log --oneline --grep="{id}" -30
```

Collect touched production/test files from those commits
(`git show --name-only --pretty=format: <hash>`). Exclude `.planning/` unless
the only changes are review artifacts from this skill.

Artifact directory:
- phase: `{PHASE_DIR}`
- quick: `{QUICK_DIR}`

Print:

```
## Post-plan review — {id}
Mode: {phase|quick}
Commits under review:
{hash list}
Files: {paths}
```
</step>

<step name="2_style_review">
Read and **fully execute** the style-review skill on the scoped files
(including its R15 swallowed-exception HITL gate). Do not abbreviate.

After it finishes:

1. Write `{artifact_dir}/{id}-STYLE-REVIEW.md` with plan/quick id, commit
   range, timestamp, refactors, remaining findings (incl. R15 verdicts).
2. If code/test changes or the new artifact need committing:

```bash
gsd_run query commit "refactor({id}): apply style-review" --files <changed paths> "{artifact_dir}/{id}-STYLE-REVIEW.md"
```

If `gsd_run` is unavailable, use normal `git add` + `git commit` with the same
message. Never `--no-verify`. Skip if nothing to commit.
</step>

<step name="3_dedup_review">
Read and **fully execute** the dedup-review skill on the same scoped files
(plus one-hop importers/importees as that skill requires). Auto-apply only safe
consolidations; surface propose-only moves without blocking the gate.

After it finishes:

1. Write `{artifact_dir}/{id}-DEDUP-REVIEW.md`.
2. Commit any code/test changes plus the artifact:

```bash
gsd_run query commit "refactor({id}): apply dedup-review" --files <changed paths> "{artifact_dir}/{id}-DEDUP-REVIEW.md"
```

Same fallback rules as style-review.
</step>

<step name="4_human_commit_gate" priority="high">
**Blocking human gate — do not start the next plan or quick task.**

```bash
git log --oneline --grep="{id}" -30
```

Present:

```
## Human commit review — {id}

Review these commits in Source Control or:
  git show <hash>
  git diff <base>..<tip>

Artifacts:
  {artifact_dir}/{id}-STYLE-REVIEW.md
  {artifact_dir}/{id}-DEDUP-REVIEW.md

Reply with one of:
  - approved     → allow the next plan / wave / quick task
  - undo         → revert this id's commits (confirm first)
  - <feedback>   → stay halted until approved or undo
```

Use AskUserQuestion when available; otherwise print and **stop and wait**.
Never auto-approve.

If `undo`:
- **Phase plan id** (`NN-MM`): `/gsd-undo --plan {id}` after confirm.
- **Quick id**: list commits matching `{id}`, confirm, then
  `git revert --no-edit <hashes newest-first>` (or soft-reset only if the user
  explicitly asks and nothing else landed after). Do not use `/gsd-undo` for
  quick ids unless that command gains quick support.
- After undo, STOP (do not advance).

If `approved`, end successfully so the host may continue.
</step>

</process>

<constraints>
- Prefer `/gsd-execute-plan` for one phase plan at a time.
- Keep `workflow.auto_advance` false.
- Do not fold unrelated dirty files into review commits.
- Diff-budget still applies (~150 non-test lines per refactor commit).
- **gsd-quick note:** native `execute:post` dispatch inside `quick.md` only runs
  when `$FULL_MODE` is true (`--full` or all granular flags). For plain
  `/gsd-quick`, the project `.claude/CLAUDE.md` still requires this skill after
  SUMMARY — honor that even when no capability hook fired.
</constraints>

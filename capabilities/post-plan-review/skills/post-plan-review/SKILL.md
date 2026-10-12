---
name: gsd-post-plan-review
description: >
  After a GSD plan/wave or gsd-quick task finishes: run style-review, then
  dedup-review, commit any fixes and review artifacts, then pause for human
  commit review (approved or undo) before continuing. Invoked at
  execute:wave:post / execute:post when workflow.post_plan_review is true, or
  via /gsd-post-plan-review / /post-plan-review.
---

<objective>
Close the loop after executor commits: polish the diff with style + dedup
reviews (committed), then give the human a clean commit list to approve or undo
**and** a joint triage of every style REPORTED finding and dedup propose-only
item before any further plan or quick task runs.
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
   range, timestamp, refactors, remaining findings (incl. R15 verdicts) and
   the coverage line. Copy the merged ledger to
   `{artifact_dir}/{id}-STYLE-LEDGER.jsonl`. Do not continue unless the
   style-review coverage gate (`rules.py check`) passed or the report lists
   every unreviewed cell.
2. If code/test changes or the new artifact need committing:

```bash
gsd_run query commit "refactor({id}): apply style-review" --files <changed paths> "{artifact_dir}/{id}-STYLE-REVIEW.md" "{artifact_dir}/{id}-STYLE-LEDGER.jsonl"
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

List this id's commits oldest-first:

```bash
git log --reverse --format='%h %s' --grep="{id}" -30
```

1. Open the **combined** diff of all those commits at once in the editor
   (Cursor, falling back to VS Code): one side-by-side tab per file touched by
   any of the commits, comparing the state before the oldest commit with the
   state at the newest commit. Snapshots go to a temp dir so the tabs stay
   valid after the command exits; a missing side (added/deleted file, root
   commit) is an empty file:

```bash
d="${TMPDIR:-/tmp}/gsd-commit-review/{id}"
rm -rf "$d" && mkdir -p "$d/before" "$d/after"
git log --reverse --format=%h --grep="{id}" -30 > "$d/commits"
base=$(head -1 "$d/commits"); tip=$(tail -1 "$d/commits")
while IFS= read -r h; do
  git diff-tree --root --no-commit-id -r --name-only "$h"
done < "$d/commits" | sort -u > "$d/files"
editor=$(command -v cursor || command -v code)
while IFS= read -r f; do
  mkdir -p "$d/before/$(dirname "$f")" "$d/after/$(dirname "$f")"
  git show "$base^:$f" > "$d/before/$f" 2>/dev/null || : > "$d/before/$f"
  git show "$tip:$f" > "$d/after/$f" 2>/dev/null || : > "$d/after/$f"
  [ -n "$editor" ] && "$editor" --reuse-window --diff "$d/before/$f" "$d/after/$f"
done < "$d/files"
git diff --stat "$base^" "$tip" -- $(cat "$d/files")
```

   If commits from other ids landed between `base` and `tip` on the same
   files, their changes show up too — mention it when the log shows such
   commits. If neither `cursor` nor `code` is on PATH, say so (Cursor:
   Command Palette → "Install 'cursor' command", or symlink
   `/Applications/Cursor.app/Contents/Resources/app/bin/cursor` into PATH)
   and tell the user to inspect with `git diff {base}^ {tip}` instead.

2. Collect **open findings** from the artifacts just written (do not invent
   new ones):
   - Style: every `REPORTED` row in `{id}-STYLE-REVIEW.md` / ledger
   - Dedup: every **Propose-only** row in `{id}-DEDUP-REVIEW.md`
   Deduplicate when style and dedup describe the same change (one bullet,
   cite both IDs). If both lists are empty, say so explicitly.

3. Ask for **one joint reply** covering commits **and** findings
   (AskUserQuestion when available; otherwise print and **stop and wait**).
   Never auto-approve commits. Never silently defer findings — always
   surface them in this same gate, even when the commit verdict is already
   clear. Group findings by cost (safe / API-breaking / conflicts with a
   locked plan) so the human can pick quickly:

```
## Human commit review — {id}

Commits under review ({total}):
{hash subject list}

{diff stat}

All changed files are open as diffs in the editor. Artifacts:
  {artifact_dir}/{id}-STYLE-REVIEW.md
  {artifact_dir}/{id}-DEDUP-REVIEW.md

### Open findings (style REPORTED + dedup propose-only)
{numbered list: ID — one-line summary — cost: safe | breaking | locked-conflict}
(or: none)

Reply with:
  1. Commit verdict: approved | undo | <feedback>
  2. Findings: none | all-safe | <ids to implement> | defer:<ids> | skip:<ids>
     (combine freely, e.g. "approved; implement 1,3; skip 2; defer rest")
```

If `undo`:
- **Phase plan id** (`NN-MM`): `/gsd-undo --plan {id}` after confirm.
- **Quick id**: list commits matching `{id}`, confirm, then
  `git revert --no-edit <hashes newest-first>` (or soft-reset only if the user
  explicitly asks and nothing else landed after). Do not use `/gsd-undo` for
  quick ids unless that command gains quick support.
- After undo, STOP (do not advance). Do not implement findings after undo.

If commit verdict is `approved` (or feedback that keeps the commits):
- For findings marked **implement** / **all-safe**: apply them now under the
  diff budget (separate commit(s) `refactor({id}): address review finding
  {rule-or-signal}`), re-run the relevant tests, then STOP so the human can
  approve those follow-up commits before the next plan/quick.
- For **defer**: note them in the artifact (or a one-line STATE/backlog
  mention) and leave the code alone.
- For **skip** / **none**: leave them alone; do not re-ask later in this gate.
- If the human only answers the commit half, **ask once more** for the
  findings half before ending. Do not treat silence as skip.

Only end the gate as fully complete when both halves have an explicit answer.
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

---
description: Resync balitech models from /v3/catalog
---

Run `python3 ~/.config/kilo/scripts/resolve_balitech.py` first (dry run), then apply
with `--write` if the diff looks right. `--write` edits a chezmoi-managed file, so
follow it with `chezmoi re-add '~/.config/kilo/kilo.jsonc'` to keep the source in sync
(use the tilde form; the relative path is rejected as "not managed"), then confirm with
`chezmoi diff '~/.config/kilo/kilo.jsonc'` (must be empty).

Then publish the change from the chezmoi source repo — only if it actually changed
(`git -C "$(chezmoi source-path)" status --porcelain` non-empty):

```sh
cd "$(chezmoi source-path)"
git add dot_config/kilo/kilo.jsonc
git commit -m "chore(kilo): sync balitech models"
git push
```

Skip commit/push entirely when the source repo is clean (no-op run or the file is
already up to date). If push is rejected (non-fast-forward), stop and report — do not
force-push or rebase without asking.

Pass any `/bt-models` arguments through as model ids to refresh just those
(e.g. `/bt-models bt/gpt-6-sol`); that run merges instead of resyncing the block.
Do not pass `--no-probe` unless asked — it skips the 403 plan-access check.

Report the ADDED / REMOVED / CHANGED lines and the skip reasons. Two things matter
in what you report:

- A model that moved to `403 model_not_allowed` is gated by the plan, not down. Say so.
- A `CHANGED ... cost` line means the multiplier moved; give old -> new.

End the report with whether the commit/push happened (and the commit sha) or why it was skipped.
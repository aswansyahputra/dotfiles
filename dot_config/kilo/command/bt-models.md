---
description: Resync balitech models from /v3/catalog
---

Run `python3 ~/.config/kilo/scripts/resolve_balitech.py` first (dry run), then apply
with `--write` if the diff looks right. `--write` edits a chezmoi-managed file, so
follow it with `chezmoi re-add .config/kilo/kilo.jsonc` to keep the source in sync.

Pass any `/bt-models` arguments through as model ids to refresh just those
(e.g. `/bt-models bt/gpt-6-sol`); that run merges instead of resyncing the block.
Do not pass `--no-probe` unless asked — it skips the 403 plan-access check.

Report the ADDED / REMOVED / CHANGED lines and the skip reasons. Two things matter
in what you report:

- A model that moved to `403 model_not_allowed` is gated by the plan, not down. Say so.
- A `CHANGED ... cost` line means the multiplier moved; give old -> new.
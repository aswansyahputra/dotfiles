# dotfiles

Managed with [chezmoi](https://www.chezmoi.io). Source lives here; targets are
deployed to `~`.

```bash
chezmoi status        # drift between source and home
chezmoi diff ~/.zshrc # review a change
chezmoi apply         # deploy source -> home
```

## What is tracked

| Target | Purpose |
| --- | --- |
| `~/.config/opencode/opencode.json` | OpenCode config (providers, MCP servers) |
| `~/.config/kilo/kilo.jsonc` | Kilo Code config |
| `~/.posit/assistant/settings.json` | Posit Assistant settings |
| `~/.agents/.skill-lock.json` | Agent skills lock file (see below) |
| `~/.local/bin/nusagate-sync` | Provider model sync |
| `~/.local/bin/relink-skills` | Collapse duplicate skill copies into symlinks |
| `~/.local/bin/skills-restore` | Rebuild the skills install from the lock file |

## Editing and syncing

`autoAdd` and `autoCommit` are on (see `.chezmoi.toml.tmpl`), so commands that
change the source state stage and commit for you:

```bash
chezmoi re-add ~/.config/opencode/opencode.json   # edit -> staged -> committed
chezmoi git -- log -1 -p                          # review the commit
chezmoi git -- push                               # publish — never automatic
```

Commit messages follow conventional commits, generated from the changed paths:

```
feat(opencode): add .config/opencode/opencode.json
chore(kilo): update .config/kilo/kilo.jsonc
docs: add README.md
chore: update 2 files

- .config/kilo/kilo.jsonc
- .config/opencode/opencode.json
```

Types: `feat` (all new), `chore` (updates/removals), `docs` (`*.md`). Scope comes
from the first changed path — `dot_config/opencode/x` → `opencode`,
`dot_agents/*` → `skills`. Multi-file commits drop the scope and list the source
paths in the body.

**`autoPush` is deliberately off.** A commit is local and amendable; a push is
published. That pause is where you read the diff.

Two behaviours to keep in mind:

- `autoAdd` runs `git add .`, so it stages **everything** in the source tree, not
  just your target. Don't leave half-finished edits lying around — the next
  unrelated `chezmoi add` will sweep them into its commit.
- Bulk `chezmoi re-add` copies every tracked file's current contents into source
  and commits them as one change, with no per-file review. Prefer
  `chezmoi re-add <file>`.

### Secret gate

A `git-auto-commit` pre-hook runs `~/.local/bin/chezmoi-secret-guard` after
staging and before the commit. It scans the staged diff for API-key, token, and
private-key patterns. On a match it:

1. removes the offending files from the index,
2. deletes their source copies (the `$HOME` files are untouched),
3. exits non-zero, so chezmoi aborts the commit.

Deleting the source copy matters: leaving it staged would let the secret ride
along in the *next* auto-commit.

`chezmoi diff` resolves home-relative targets (`~/.agents/x.json`), not bare
relative paths — `chezmoi diff .agents/x.json` reports "not managed".

## Agent skills

Skills are installed with [`npx skills`](https://github.com/vercel-labs/skills)
into one canonical directory, then linked into each agent:

```
~/.agents/skills/<name>/          ← the only real copy
~/.claude/skills/<name>    -> ../../.agents/skills/<name>
```

OpenCode reads `~/.agents/skills` natively, so it needs no link of its own.
Chezmoi tracks **the lock file only** — never the skill contents, which
`npx skills update` owns.

### The install rule

The CLI picks symlink vs copy mode from how many distinct agent directories you
target (`defaultInstallMode` in `src/add.ts`): one directory → copy, two or more
→ symlink. So installing for a single agent leaves a real directory behind.

**Always name every agent in one command:**

```bash
npx skills add <owner>/<repo> --skill <name> -g -a opencode -a claude-code -a antigravity -y
```

That writes one copy to `~/.agents/skills` and symlinks the rest. No cleanup
needed.

### relink-skills

Repairs installs that took the copy path — a `-a claude-code`-only install, or a
manual clone dropped into `~/.claude/skills`.

```bash
relink-skills --dry-run          # preview
relink-skills                    # repair ~/.claude/skills
relink-skills ~/.cursor/skills   # any other agent dir
```

It only touches a directory when all three hold: it is a real directory, a
same-named twin exists in `~/.agents/skills`, and `diff -rq` reports them
identical. Everything else is reported and left alone.

### skills-restore

`npx skills` has no global restore — `experimental_install` reads only a project
`skills-lock.json` and has no `-g` flag. So a fresh machine gets the lock from
chezmoi and nothing else. This script replays it:

```bash
skills-restore                  # print the plan (changes nothing)
skills-restore --run            # execute it
skills-restore --verify         # compare lock against disk
skills-restore --json           # machine-readable
skills-restore --agents opencode,claude-code,cursor
skills-restore --lock <path>    # a project skills-lock.json
```

It groups skills by source so each repo is cloned once, uses
`--skill <orig> --rename <new>` for renamed skills, and flags entries it cannot
replay (signed download URLs, unknown source types) instead of guessing.

## Fresh machine

```bash
chezmoi init --apply git@github.com:aswansyahputra/dotfiles.git
skills-restore --verify                    # what's missing
skills-restore --run                       # rebuild skills
relink-skills --dry-run && relink-skills   # collapse any copies
```

`chezmoi init --apply` deploys configs, the lock, and both scripts. The skills
themselves come from `skills-restore`.

# Contributing to GSentinel

> Read this before opening a branch or PR. These rules keep the repo clean and the pipeline trustworthy.

---

## Hard Rules

| # | Rule |
|---|------|
| 1 | NEVER commit `.env` or any file containing a live API key |
| 2 | NEVER let any node guess a financial field — all corrections must come from `internal_db.json` |
| 3 | NEVER use `--no-verify` to skip pre-commit hooks |
| 4 | NEVER force-push to `main` or `develop` |
| 5 | NEVER merge a PR that hasn't passed the critic validation step (confidence < 0.9 is a signal, not a result) |
| 6 | ALWAYS update `CHANGELOG.md` under `[Unreleased]` before opening a PR |
| 7 | ALWAYS run `python sentinel.py` locally and confirm the action card is correct before pushing |
| 8 | The pipeline is called **GSentinel** — never "the agent", "the tool", or "the system" |

---

## Branching Strategy — Gitflow

```
main
 │   (stable releases only — tagged vX.Y.Z)
 │
develop
 │   (integration branch — all features merge here first)
 │
 ├── feature/short-description
 ├── fix/short-description
 └── docs/short-description
```

### Branch naming

| Type | Pattern | Example |
|------|---------|---------|
| New feature | `feature/<short-description>` | `feature/batch-rejection-processing` |
| Bug fix | `fix/<short-description>` | `fix/critic-regex-415` |
| Documentation | `docs/<short-description>` | `docs/add-api-reference` |
| Release prep | `release/vX.Y.Z` | `release/v0.3.0` |

### Rules

- Branch off `develop` — never branch off `main` directly
- Keep branches short-lived — open a PR within 3 days of creating a branch
- Delete the branch after the PR merges

---

## Commit Message Format

```
<type>: <imperative summary, max 72 chars>

<body: what changed and why — bullet points if multiple areas>
- Area 1: what changed and why
- Area 2: what changed and why

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

### Types

| Type | When to use |
|------|-------------|
| `feat` | New node, new endpoint, new UI capability |
| `fix` | Bug in existing node logic or validation |
| `docs` | README, CHANGELOG, CONTRIBUTING, CLAUDE.md only |
| `refactor` | Internal restructure with no behaviour change |
| `test` | Adding or updating tests |
| `chore` | Dependency updates, `.gitignore`, config |

### Examples

```
feat: add batch rejection processing for multi-employee carrier files

- parser_node: extended regex to handle multi-record rejection format
- healer_node: loops over extracted employee IDs, one DB lookup per record
- sentinel.py: accepts directory path as input in addition to single file
```

```
fix: critic regex for Error 415 dob validation rejects valid leap year dates

- critic_node: replaced strict YYYY-MM-DD with dateutil parse + format check
- Resolves false HUMAN_REVIEW on dob values like 2000-02-29
```

---

## Pull Request Process

### Opening a PR

1. Branch off `develop` (not `main`)
2. Make your changes and confirm `python sentinel.py` produces the correct action card
3. Update `CHANGELOG.md` under `[Unreleased]` — describe what changed and why
4. Push your branch and open a PR against `develop`

### PR title format

```
<type>: <same as your commit summary>
```

Example: `feat: add Error 415 date-of-birth auto-correction`

### PR description template

```markdown
## What changed
<!-- 1–3 bullets on what this PR does -->

## Why
<!-- The motivation — bug, missing feature, user request -->

## How to verify
<!-- Steps to confirm it works: which command to run, what output to expect -->

## Checklist
- [ ] `python sentinel.py` runs clean — action card is correct
- [ ] `CHANGELOG.md` updated under [Unreleased]
- [ ] No secrets staged (no `.env`, no API keys)
- [ ] Branch is off `develop`, not `main`
```

### Merge rules

| Target | Who can merge | Method |
|--------|--------------|--------|
| `develop` | Author (after self-review) | Squash merge |
| `main` | Requires release PR from `develop` | Merge commit — creates a tagged release |

---

## Release Process (Gitflow)

```
1. Cut a release branch:    git checkout -b release/v0.3.0 develop
2. Bump version in docs:    Update CHANGELOG.md — move [Unreleased] → [0.3.0] with date
3. Open PR:                 release/v0.3.0 → main
4. After merge to main:     git tag v0.3.0 && git push origin v0.3.0
5. Back-merge to develop:   git checkout develop && git merge main
```

---

## What to Never Commit

| Pattern | Reason |
|---------|--------|
| `.env` | Contains API keys |
| `logs/agent_trace.json` | Runtime output, regenerated each run |
| `__pycache__/` | Python bytecode |
| `*.pyc` | Compiled Python |
| `.DS_Store` | macOS metadata |

All of these are already in `.gitignore`. If you accidentally stage one, run:

```bash
git rm --cached <file>
```

---

## Claude Skills

Use these skills instead of running raw git commands:

### `/github-push`
Handles secrets scanning, `.gitignore` hygiene, selective staging, and structured commit messages. Always invoke this instead of raw `git add / commit / push`.

```
/github-push "feat: add batch rejection processing"
```

---

*GSentinel — April 2026*

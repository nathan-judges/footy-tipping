# Git Operations Skill

This skill provides common Git operations following the project's branching strategy.

## Starting New Feature Work

When starting a new feature:

1. Ensure main is up to date:
```bash
git checkout main
git pull origin main
```

2. Create appropriately named branch:
```bash
# For features
git checkout -b feat/descriptive-name

# For bug fixes
git checkout -b fix/descriptive-name

# For maintenance
git checkout -b chore/descriptive-name
```

3. Make changes and commit with conventional format:
```bash
git add <files>
git commit -m "feat: add descriptive message"
```

4. Push to remote:
```bash
git push -u origin feat/descriptive-name
```

## Keeping Branch Current

Before opening a PR or when main has advanced:

```bash
# Fetch latest changes
git fetch origin

# Rebase on main (preferred for clean history)
git rebase origin/main

# If conflicts occur, resolve them then:
git add .
git rebase --continue

# Force push (safe with --force-with-lease)
git push --force-with-lease origin feat/descriptive-name
```

## Creating Pull Request

1. Ensure branch is pushed and up to date with main
2. Open PR on GitHub targeting `main`
3. Use conventional commit format for PR title
4. Include in PR description:
   - Summary of changes
   - Testing performed
   - Screenshots (if UI changes)
   - Breaking changes (if any)
5. Wait for CI checks to pass
6. Squash merge to main
7. Delete feature branch after merge

## Commit Message Guidelines

Format: `<type>(<scope>): <description>`

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `chore`: Maintenance, refactoring, deps
- `docs`: Documentation only
- `test`: Test additions or fixes
- `perf`: Performance improvement
- `ci`: CI/CD changes

**Scopes (optional):**
- `data`: Data pipeline or baked JSON
- `ui`: Frontend components
- `api`: API routes
- `model`: Prediction model
- `deps`: Dependencies

**Examples:**
```bash
git commit -m "feat(model): add injury weighting to ensemble"
git commit -m "fix(ui): prevent margin input overflow on mobile"
git commit -m "chore(deps): upgrade Next.js to 15.5.15"
git commit -m "docs: update branching strategy"
git commit -m "test(model): add ELO rating edge cases"
```

## Common Scenarios

### Syncing Diverged Branch

When your branch is behind main:
```bash
git fetch origin
git rebase origin/main
git push --force-with-lease
```

### Fixing Merge Conflicts

During rebase:
```bash
# Edit conflicted files
git add .
git rebase --continue

# Or abort and try merge instead
git rebase --abort
git merge origin/main
```

### Accidentally Committed to Main

```bash
# Create branch from current state
git branch feat/my-changes

# Reset main to origin
git checkout main
git reset --hard origin/main

# Continue work on feature branch
git checkout feat/my-changes
```

### Renaming Current Branch

```bash
# Rename local branch
git branch -m old-name new-name

# Delete old remote branch and push new one
git push origin -u new-name
git push origin --delete old-name
```

## Pre-Commit Checklist

Before committing, ensure:
- [ ] Code follows project standards (see `coding-standards.md`)
- [ ] Tests pass: `npm run check`
- [ ] TypeScript compiles: `npm run typecheck`
- [ ] Linter passes: `npm run lint`
- [ ] Python tests pass (if applicable): `npm run test:python`
- [ ] Commit message follows conventional format
- [ ] Changes are focused and atomic

## Pre-PR Checklist

Before opening a PR:
- [ ] Branch is up to date with main (rebased)
- [ ] All commits follow conventional format
- [ ] CI checks pass locally
- [ ] PR title follows conventional format
- [ ] PR description is complete
- [ ] No merge commits (use rebase)
- [ ] Feature branch will be deleted after merge

## Quick Reference

| Task | Command |
|------|---------|
| Start feature | `git checkout -b feat/my-feature` |
| Start bugfix | `git checkout -b fix/my-bug` |
| Update from main | `git fetch origin && git rebase origin/main` |
| Push new branch | `git push -u origin feat/my-feature` |
| Force push safely | `git push --force-with-lease` |
| Check status | `git status` |
| View history | `git log --oneline --graph --all` |
| Delete local branch | `git branch -d feat/my-feature` |
| Delete remote branch | `git push origin --delete feat/my-feature` |

## CI/CD Integration

All PRs trigger:
- ESLint checks
- TypeScript type checking
- Vitest frontend tests
- pytest Python tests

**All checks must pass before merge.**

Automated data updates bypass PR process and commit directly to main as `tipping-bot[bot]`.

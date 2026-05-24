# Git Workflow & Branching Strategy

## Current State Analysis

### Branch Structure
- **main**: Production branch, protected, auto-deploys to Vercel
- **cursor/fix-vercel-app-router**: Feature branch (currently active, ahead of main)
- Remote: `origin` → https://github.com/nathan-judges/footy-tipping.git

### Issues Identified
1. Feature branch `cursor/fix-vercel-app-router` has diverged from main (main has 4 newer commits)
2. Branch naming uses tool prefix (`cursor/`) which couples workflow to tooling
3. No documented branching strategy or merge workflow
4. Automated commits go directly to main (data updates bypass PR process)

## Recommended Branching Strategy

### Branch Types

#### 1. `main` (protected)
- **Purpose**: Production-ready code, always deployable
- **Protection rules**:
  - Require PR reviews before merge
  - Require status checks to pass (CI workflow)
  - No direct pushes (except automated bot commits)
  - Require linear history (rebase or squash merge)
- **Auto-deploys**: Vercel production deployment

#### 2. Feature branches: `feat/<description>`
- **Purpose**: New features or enhancements
- **Naming**: `feat/user-authentication`, `feat/injury-tracking`
- **Lifetime**: Delete after merge
- **Merge strategy**: Squash merge to main (keeps history clean)

#### 3. Bugfix branches: `fix/<description>`
- **Purpose**: Bug fixes
- **Naming**: `fix/margin-validation`, `fix/archive-deduplication`
- **Lifetime**: Delete after merge
- **Merge strategy**: Squash merge to main

#### 4. Chore branches: `chore/<description>`
- **Purpose**: Maintenance, refactoring, dependency updates
- **Naming**: `chore/upgrade-next`, `chore/cleanup-tests`
- **Lifetime**: Delete after merge
- **Merge strategy**: Squash merge to main

#### 5. Automated bot commits
- **Purpose**: Scheduled data updates from GitHub Actions
- **Commit format**: `chore(data): update tips for round N`
- **Exception**: Bot commits go directly to main (bypass PR)
- **Rationale**: Data updates are non-breaking, validated by CI, and time-sensitive

### Branch Naming Convention

```
<type>/<short-description>

Types:
  feat/     - New features
  fix/      - Bug fixes
  chore/    - Maintenance, refactoring, deps
  docs/     - Documentation only
  test/     - Test additions or fixes
  perf/     - Performance improvements

Examples:
  feat/injury-data-integration
  fix/round-selector-overflow
  chore/migrate-tailwind-v4
  docs/update-api-guide
```

**Avoid**:
- Tool prefixes (`cursor/`, `kiro/`, `copilot/`)
- Issue numbers alone (`issue-42`)
- Vague names (`updates`, `fixes`, `changes`)

## Workflow

### Starting New Work

```bash
# Ensure main is up to date
git checkout main
git pull origin main

# Create feature branch
git checkout -b feat/my-feature

# Work and commit
git add .
git commit -m "feat: add injury data to model"

# Push to remote
git push -u origin feat/my-feature
```

### Creating Pull Request

1. Push branch to origin
2. Open PR on GitHub targeting `main`
3. PR title follows Conventional Commits: `feat: add injury data to model`
4. PR description includes:
   - Summary of changes
   - Testing performed
   - Screenshots (if UI changes)
   - Breaking changes (if any)
5. Wait for CI checks to pass
6. Request review (if team grows beyond solo dev)
7. Squash merge to main
8. Delete feature branch

### Keeping Branch Up to Date

```bash
# Rebase on main to incorporate latest changes
git checkout feat/my-feature
git fetch origin
git rebase origin/main

# If conflicts, resolve and continue
git add .
git rebase --continue

# Force push (rebase rewrites history)
git push --force-with-lease origin feat/my-feature
```

### Handling Diverged Branches

**Current situation**: `cursor/fix-vercel-app-router` is behind main by 4 commits.

**Resolution**:
```bash
# Option 1: Rebase (preferred for clean history)
git checkout cursor/fix-vercel-app-router
git fetch origin
git rebase origin/main
git push --force-with-lease origin cursor/fix-vercel-app-router

# Option 2: Merge (if rebase conflicts are complex)
git checkout cursor/fix-vercel-app-router
git merge origin/main
git push origin cursor/fix-vercel-app-router
```

## CI/CD Integration

### Pull Request Checks (`.github/workflows/ci.yml`)
Runs on every PR to main:
- ESLint
- TypeScript type checking
- Vitest frontend tests
- pytest Python tests

**All checks must pass before merge.**

### Automated Data Updates (`.github/workflows/update-tips.yml`)
Runs on schedule (Tuesday/Thursday midnight UTC):
- Fetches latest NRL data
- Generates predictions
- Commits directly to main as `tipping-bot[bot]`
- Triggers Vercel deployment

**Exception to PR workflow**: Data updates are time-sensitive and validated by existing CI.

## Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `chore`: Maintenance (deps, config, refactor)
- `docs`: Documentation only
- `test`: Test additions or fixes
- `perf`: Performance improvement
- `ci`: CI/CD changes

### Scopes (optional)
- `data`: Data pipeline or baked JSON
- `ui`: Frontend components
- `api`: API routes
- `model`: Prediction model
- `deps`: Dependencies

### Examples
```
feat(model): add injury weighting to ensemble
fix(ui): prevent margin input overflow on mobile
chore(deps): upgrade Next.js to 15.5.15
docs: update branching strategy in steering files
test(model): add ELO rating edge case tests
```

## GitHub Settings Recommendations

### Branch Protection Rules (main)
Enable on GitHub repository settings:
- ✅ Require pull request before merging
- ✅ Require status checks to pass
  - `lint-typecheck-and-tests`
  - `python-tests`
- ✅ Require branches to be up to date before merging
- ✅ Require linear history (squash or rebase)
- ⚠️ Allow specified actors to bypass (add `tipping-bot[bot]` for automated commits)
- ✅ Do not allow bypassing the above settings (except bot)

### Repository Settings
- Default branch: `main`
- Automatically delete head branches: ✅ (after PR merge)
- Allow squash merging: ✅
- Allow merge commits: ❌ (keeps history clean)
- Allow rebase merging: ✅

## Migration Plan

### Immediate Actions

1. **Sync current feature branch**
   ```bash
   git checkout cursor/fix-vercel-app-router
   git rebase origin/main
   git push --force-with-lease
   ```

2. **Rename branch** (optional, for consistency)
   ```bash
   git branch -m cursor/fix-vercel-app-router feat/vercel-app-router-fix
   git push origin -u feat/vercel-app-router-fix
   git push origin --delete cursor/fix-vercel-app-router
   ```

3. **Open PR** to merge into main

4. **Enable branch protection** on GitHub (see settings above)

### Future Work

- All new branches follow `<type>/<description>` naming
- All changes go through PR process (except bot commits)
- Delete branches after merge
- Keep main clean and deployable

## Quick Reference

| Task | Command |
|------|---------|
| Start new feature | `git checkout -b feat/my-feature` |
| Update branch from main | `git rebase origin/main` |
| Push new branch | `git push -u origin feat/my-feature` |
| Force push after rebase | `git push --force-with-lease` |
| Delete local branch | `git branch -d feat/my-feature` |
| Delete remote branch | `git push origin --delete feat/my-feature` |
| Check branch status | `git status` |
| View branch history | `git log --oneline --graph --all` |

## Troubleshooting

### Diverged branch (local ahead and behind remote)
```bash
git fetch origin
git rebase origin/main
git push --force-with-lease
```

### Merge conflicts during rebase
```bash
# Fix conflicts in editor
git add .
git rebase --continue

# Or abort and try merge instead
git rebase --abort
git merge origin/main
```

### Accidentally committed to main
```bash
# Create branch from current state
git branch feat/my-changes

# Reset main to origin
git checkout main
git reset --hard origin/main

# Continue work on feature branch
git checkout feat/my-changes
```

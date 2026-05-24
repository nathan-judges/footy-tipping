# Sync Current Branch Skill

This skill handles syncing the current `cursor/fix-vercel-app-router` branch with main and optionally renaming it to follow project conventions.

## Current Situation

- **Current branch**: `cursor/fix-vercel-app-router`
- **Status**: Behind main by 4 commits (data updates)
- **Issue**: Branch name uses tool prefix, violating naming conventions

## Option 1: Sync and Rename (Recommended)

This brings the branch up to date and renames it to follow conventions:

```bash
# Sync with main
git fetch origin
git rebase origin/main

# Rename to follow conventions
git branch -m cursor/fix-vercel-app-router feat/vercel-app-router-fix

# Push renamed branch
git push origin -u feat/vercel-app-router-fix

# Delete old remote branch
git push origin --delete cursor/fix-vercel-app-router

# Force push if rebase rewrote history
git push --force-with-lease origin feat/vercel-app-router-fix
```

## Option 2: Sync Only (Keep Name)

If you want to keep the current name temporarily:

```bash
# Sync with main
git fetch origin
git rebase origin/main

# Force push
git push --force-with-lease origin cursor/fix-vercel-app-router
```

## Handling Rebase Conflicts

If conflicts occur during rebase:

1. Git will pause and show conflicted files
2. Open each file and resolve conflicts (look for `<<<<<<<`, `=======`, `>>>>>>>`)
3. Stage resolved files:
```bash
git add <resolved-files>
```
4. Continue rebase:
```bash
git rebase --continue
```
5. Repeat until rebase completes

If rebase becomes too complex:
```bash
# Abort and use merge instead
git rebase --abort
git merge origin/main
git push origin cursor/fix-vercel-app-router
```

## After Syncing

1. Verify branch is up to date:
```bash
git log --oneline --graph --all --decorate -10
```

2. Run checks to ensure everything still works:
```bash
npm run check
npm run test:python
```

3. Open PR to merge into main:
   - Title: `feat: fix Vercel App Router compatibility` (or appropriate description)
   - Description: Summarize changes and testing
   - Wait for CI checks
   - Squash merge to main
   - Delete feature branch

## Why Sync is Needed

The main branch has 4 new commits (data updates from bot):
- `chore(data): update tips for round 12`
- `chore(data): update tips for round 11`
- `chore(data): update tips for round 10`
- `chore(data): update tips for round 9`

These are automated data updates that don't conflict with feature work, but keeping branches in sync:
- Ensures CI runs against latest code
- Prevents merge conflicts later
- Makes PR review easier
- Maintains clean git history

## Post-Merge Cleanup

After PR is merged:

```bash
# Switch to main
git checkout main

# Pull latest (includes your merged changes)
git pull origin main

# Delete local feature branch
git branch -d feat/vercel-app-router-fix

# Remote branch should auto-delete if GitHub setting enabled
# If not, manually delete:
git push origin --delete feat/vercel-app-router-fix
```

## Quick Command Sequence

For the recommended path (sync + rename + PR):

```bash
# 1. Sync
git fetch origin
git rebase origin/main

# 2. Rename
git branch -m cursor/fix-vercel-app-router feat/vercel-app-router-fix

# 3. Push
git push origin -u feat/vercel-app-router-fix
git push --force-with-lease origin feat/vercel-app-router-fix
git push origin --delete cursor/fix-vercel-app-router

# 4. Verify
npm run check
npm run test:python

# 5. Open PR on GitHub, wait for CI, merge, delete branch
```

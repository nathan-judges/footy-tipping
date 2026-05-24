# Repository Cleanup & Professional Standards Checklist

This document tracks the cleanup and standardization of the footy-tipping repository to ensure professional best practices are followed.

## ✅ Completed

### Documentation
- [x] Git workflow and branching strategy documented (`git-workflow.md`)
- [x] Git operations skill created (`skills/git-operations.md`)
- [x] Branch sync guide created (`skills/sync-current-branch.md`)
- [x] Steering files overview created (`steering/README.md`)
- [x] Coding standards updated with Git guidelines

### Git & Branching
- [x] Branch renamed from `cursor/fix-vercel-app-router` to `feat/vercel-app-router-fix`
- [x] Documentation changes committed and pushed
- [x] Branch protection rules enabled on main:
  - Require PR before merging
  - Require CI checks to pass (`lint-typecheck-and-tests`, `python-tests`)
  - Require linear history
  - Auto-delete branches after merge

### Code Quality
- [x] ESLint: No warnings or errors
- [x] TypeScript: Type checking passes
- [x] Frontend tests: 12 tests passing (5 test files)

## 🔄 In Progress

### Bot Bypass Configuration
- [ ] **Issue**: Cannot configure bot bypass for `tipping-bot[bot]` in GitHub UI
- [ ] **Workaround needed**: Modify workflow to use Personal Access Token (PAT)
- [ ] **Alternative**: Accept that bot commits will need manual approval or create PRs

### Branch Protection Testing
- [ ] Test direct push to main (should fail)
- [ ] Test PR workflow (should succeed)
- [ ] Test automated workflow with current protection rules

## 📋 Pending Tasks

### Code Quality & Standards

#### 1. Migrate from deprecated `next lint`
**Priority**: Medium  
**Issue**: `next lint` is deprecated in Next.js 16  
**Action**:
```bash
npx @next/codemod@canary next-lint-to-eslint-cli .
```
**Files affected**: `package.json`, potentially ESLint config

#### 2. Add missing test coverage
**Priority**: High  
**Gaps identified**:
- `src/lib/accuracyHelpers.ts` - No tests for core accuracy logic
- `src/lib/loadArchive.ts` - No tests for deduplication logic
- Edge cases: draws, missing scores, null picks

**Action**: Create test files:
- `src/lib/__tests__/accuracyHelpers.test.ts`
- `src/lib/__tests__/loadArchive.test.ts`

#### 3. Python test coverage review
**Priority**: Medium  
**Action**:
```bash
pytest tests/python/ --cov=scripts/lib --cov-report=term-missing
```
**Goal**: Identify gaps in Python pipeline coverage

#### 4. Add pre-commit hooks
**Priority**: Medium  
**Tools**: husky + lint-staged  
**Hooks**:
- Run `npm run lint` on staged files
- Run `npm run typecheck`
- Run relevant tests
- Validate commit message format

**Action**:
```bash
npm install --save-dev husky lint-staged
npx husky init
```

### Documentation

#### 5. Add CONTRIBUTING.md
**Priority**: High  
**Content**:
- Link to `git-workflow.md`
- Development setup instructions
- Testing requirements
- PR checklist
- Code review guidelines

#### 6. Enhance README.md
**Priority**: Medium  
**Additions needed**:
- Badges (CI status, deployment status)
- Architecture diagram
- Link to documentation in `.kiro/steering/`
- Development workflow overview
- Deployment process

#### 7. Add API documentation
**Priority**: Low  
**Files**: Document edge API routes in `src/app/api/`
- `/api/live-override` - Purpose, parameters, response format
- Add JSDoc comments to API handlers

### Repository Structure

#### 8. Add .editorconfig
**Priority**: Low  
**Purpose**: Ensure consistent formatting across editors
**Content**:
```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.{js,ts,tsx,json,yml,yaml}]
indent_style = space
indent_size = 2

[*.py]
indent_style = space
indent_size = 4

[*.md]
trim_trailing_whitespace = false
```

#### 9. Review and clean .gitignore
**Priority**: Low  
**Action**: Ensure all build artifacts, secrets, and temp files are ignored
**Check**:
- `.env` files (except `.env.example`)
- Build outputs (`.next/`, `dist/`)
- Python artifacts (`__pycache__/`, `*.pyc`, `.pytest_cache/`)
- Virtual environments (`.venv/`, `.venv-test/`)
- IDE files (`.vscode/`, `.idea/`)

#### 10. Add LICENSE file
**Priority**: Medium  
**Action**: Choose and add appropriate license (MIT, Apache 2.0, etc.)

### CI/CD Improvements

#### 11. Add deployment status checks
**Priority**: Low  
**Action**: Configure Vercel to report deployment status to GitHub
**Benefit**: See deployment status in PR checks

#### 12. Add code coverage reporting
**Priority**: Medium  
**Tools**: Codecov or Coveralls  
**Action**:
- Add coverage generation to CI
- Upload coverage reports
- Add coverage badge to README

#### 13. Add dependency update automation
**Priority**: Low  
**Tools**: Dependabot or Renovate  
**Action**: Configure automated PR creation for dependency updates
**File**: `.github/dependabot.yml`

#### 14. Enhance Python tests in CI
**Priority**: Medium  
**Current**: Python 3.11  
**Should match**: Python 3.13 (per project-overview.md)  
**Action**: Update `.github/workflows/ci.yml`

### Security & Best Practices

#### 15. Add security scanning
**Priority**: Medium  
**Tools**:
- GitHub Dependabot security alerts (enable in repo settings)
- npm audit in CI
- Python safety check

**Action**: Add to CI workflow:
```yaml
- name: Security audit (npm)
  run: npm audit --audit-level=moderate

- name: Security audit (Python)
  run: pip install safety && safety check
```

#### 16. Review and secure secrets
**Priority**: High  
**Action**:
- Audit `.env.example` - ensure no real secrets
- Verify `ODDS_API_KEY` is properly secured in GitHub Secrets
- Add documentation about required secrets

#### 17. Add SECURITY.md
**Priority**: Medium  
**Content**:
- How to report security vulnerabilities
- Supported versions
- Security update policy

### Data Pipeline

#### 18. Implement auto-populate results
**Priority**: High (from implementation-plan.md)  
**Files**: `scripts/update_tips.py`, `scripts/lib/fetch_data.py`  
**Action**: Automatically fetch and populate results for completed games

#### 19. Add scheduled result backfill
**Priority**: High (from implementation-plan.md)  
**Action**: Add daily workflow to backfill results for completed rounds

### Code Improvements

#### 20. Remove deprecated code
**Priority**: Low  
**Action**: Search for TODO, FIXME, DEPRECATED comments and address them

#### 21. Add JSDoc comments
**Priority**: Low  
**Action**: Add JSDoc to public functions in `src/lib/`
**Benefit**: Better IDE autocomplete and documentation

#### 22. Standardize error handling
**Priority**: Medium  
**Action**: Review API routes and ensure consistent error responses
**Pattern**: Always return valid JSON, never throw to client

## 🎯 Priority Order

### Immediate (This Week)
1. Fix bot bypass issue (PAT or accept manual approval)
2. Add missing test coverage (accuracyHelpers, loadArchive)
3. Add CONTRIBUTING.md
4. Update Python version in CI to 3.13

### Short Term (This Month)
5. Migrate from deprecated `next lint`
6. Add pre-commit hooks
7. Enhance README with badges and architecture
8. Add security scanning to CI
9. Implement auto-populate results in data pipeline

### Long Term (Next Quarter)
10. Add code coverage reporting
11. Add dependency update automation
12. Add comprehensive API documentation
13. Implement scheduled result backfill

## Testing Checklist

Before considering cleanup complete:

### Local Testing
- [ ] `npm run check` passes (lint + typecheck + tests)
- [ ] `npm run test:python` passes
- [ ] `npm run build` succeeds
- [ ] Dev server runs without errors: `npm run dev`

### Git Workflow Testing
- [ ] Cannot push directly to main
- [ ] Can create feature branch and push
- [ ] Can open PR from feature branch
- [ ] CI checks run on PR
- [ ] Can merge PR (squash merge)
- [ ] Branch auto-deletes after merge

### Deployment Testing
- [ ] Vercel deployment succeeds
- [ ] Production site loads correctly
- [ ] All routes work (/, /round/[id], /archive)
- [ ] Data freshness indicator shows correct status

### Automated Workflow Testing
- [ ] Manual trigger of "Update Baked Tips" workflow
- [ ] Workflow completes successfully
- [ ] Data files are updated
- [ ] Commit is created (or PR if using PAT workaround)

## Documentation Standards

All documentation should follow these standards:

### Markdown Files
- Use ATX-style headers (`#` not underlines)
- Include table of contents for files >200 lines
- Use code fences with language identifiers
- Keep line length reasonable (~100 chars)
- Use relative links for internal docs

### Code Comments
- TypeScript: JSDoc for public APIs
- Python: Docstrings (Google style)
- Inline comments for complex logic only
- Keep comments up to date with code

### Commit Messages
- Follow Conventional Commits
- Use present tense ("add" not "added")
- Keep first line under 72 characters
- Add body for non-obvious changes

## Review Schedule

This checklist should be reviewed:
- Weekly during active development
- Monthly during maintenance
- After major feature additions
- Before releases

## Notes

- Bot bypass issue is blocking automated data updates with current branch protection
- Consider creating a separate "data-updates" branch that merges to main via automated PR
- All tests currently passing - maintain this standard
- Documentation is comprehensive - keep it updated as project evolves

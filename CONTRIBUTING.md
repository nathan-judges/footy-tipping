# Contributing to Footy Tipping

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to this project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Commit Message Guidelines](#commit-message-guidelines)

## Getting Started

### Prerequisites

- **Node.js**: 20.x or later
- **Python**: 3.13
- **npm**: Comes with Node.js
- **Git**: For version control

### Initial Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/nathan-judges/footy-tipping.git
   cd footy-tipping
   ```

2. **Install Node.js dependencies:**
   ```bash
   npm install
   ```

3. **Set up Python virtual environment:**
   ```bash
   python3.13 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
   ```

4. **Create environment file:**
   ```bash
   cp .env.example .env
   # Edit .env and add your ODDS_API_KEY if needed
   ```

5. **Verify setup:**
   ```bash
   npm run check      # Runs lint, typecheck, and frontend tests
   npm run test:python  # Runs Python tests
   ```

## Development Workflow

We follow a feature branch workflow with pull requests. See [.kiro/steering/git-workflow.md](.kiro/steering/git-workflow.md) for complete details.

### Quick Start

1. **Ensure main is up to date:**
   ```bash
   git checkout main
   git pull origin main
   ```

2. **Create a feature branch:**
   ```bash
   # For features
   git checkout -b feat/your-feature-name
   
   # For bug fixes
   git checkout -b fix/bug-description
   
   # For maintenance
   git checkout -b chore/task-description
   ```

3. **Make your changes and commit:**
   ```bash
   git add <files>
   git commit -m "feat: add your feature description"
   ```

4. **Push to remote:**
   ```bash
   git push -u origin feat/your-feature-name
   ```

5. **Open a Pull Request** on GitHub targeting `main`

### Branch Naming Convention

Use the following prefixes:

- `feat/` - New features
- `fix/` - Bug fixes
- `chore/` - Maintenance, refactoring, dependencies
- `docs/` - Documentation only
- `test/` - Test additions or fixes
- `perf/` - Performance improvements

**Examples:**
- `feat/injury-data-integration`
- `fix/round-selector-overflow`
- `chore/upgrade-dependencies`
- `docs/api-documentation`

**Avoid:**
- Tool prefixes (`cursor/`, `kiro/`)
- Issue numbers alone (`issue-42`)
- Vague names (`updates`, `fixes`)

## Code Standards

### TypeScript / JavaScript

- **Strict mode**: No `any` types in new code
- **Server components by default**: Only add `"use client"` when necessary
- **Small, composable functions**: Keep functions focused and testable
- **Shared utilities**: Use `src/lib/utils.ts` for common helpers
- **No duplication**: Extract shared logic into reusable functions

### React / Next.js

- **App Router only**: No Pages Router patterns
- **Server-side data loading**: Use direct imports or `loadXxx()` helpers
- **Edge runtime for APIs**: Use `export const runtime = "edge"`
- **Fail-soft APIs**: Always return valid JSON, never throw to client

### Python

- **PEP 8 compliance**: Follow Python style guide
- **Docstrings**: Use Google-style docstrings for functions
- **Type hints**: Add type hints to function signatures
- **Pipeline modules**: Keep all pipeline code in `scripts/lib/`

### File Organization

```
src/
  app/          # Next.js routes (page.tsx, layout.tsx, api/)
  components/   # React components
    ui/         # shadcn primitives only
  lib/          # Pure helpers, types, data loaders
scripts/
  lib/          # Python pipeline modules
tests/
  python/       # pytest tests
data/           # Baked JSON artifacts (committed)
docs/           # Architecture decisions, runbooks
.kiro/
  steering/     # Project-wide guidance (auto-included)
  skills/       # Reusable operation guides (on-demand)
```

## Testing Requirements

### Before Committing

Run the full test suite:

```bash
npm run check      # Lint + typecheck + frontend tests
npm run test:python  # Python tests
```

### Writing Tests

#### Frontend Tests (Vitest + Testing Library)

- Location: `src/**/__tests__/*.test.ts(x)`
- Run: `npm test`
- Coverage: Aim for >80% on new code

**Example:**
```typescript
import { describe, it, expect } from 'vitest';
import { myFunction } from '../myModule';

describe('myFunction', () => {
  it('should handle valid input', () => {
    expect(myFunction('valid')).toBe('expected');
  });

  it('should handle edge cases', () => {
    expect(myFunction('')).toBe('default');
  });
});
```

#### Python Tests (pytest)

- Location: `tests/python/`
- Run: `pytest tests/python/`
- Coverage: `pytest tests/python/ --cov=scripts/lib`

**Example:**
```python
import pytest
from scripts.lib.my_module import my_function

def test_my_function_valid_input():
    result = my_function("valid")
    assert result == "expected"

def test_my_function_edge_case():
    result = my_function("")
    assert result == "default"
```

### Test Coverage Expectations

- **New features**: Must include tests
- **Bug fixes**: Add test that reproduces the bug
- **Refactoring**: Existing tests must pass
- **Critical paths**: Aim for 100% coverage (accuracy helpers, data loaders)

## Pull Request Process

### Before Opening a PR

1. **Ensure branch is up to date:**
   ```bash
   git fetch origin
   git rebase origin/main
   ```

2. **Run all checks:**
   ```bash
   npm run check
   npm run test:python
   npm run build  # Verify production build works
   ```

3. **Review your changes:**
   ```bash
   git diff origin/main
   ```

### PR Checklist

- [ ] Branch is up to date with main
- [ ] All tests pass locally
- [ ] No linting or type errors
- [ ] Commit messages follow Conventional Commits format
- [ ] PR title follows Conventional Commits format
- [ ] PR description is complete (see template below)
- [ ] No merge commits (use rebase)
- [ ] Changes are focused and atomic

### PR Description Template

```markdown
## Summary
Brief description of what this PR does.

## Changes
- List key changes
- One per line
- Be specific

## Testing
- [ ] Unit tests added/updated
- [ ] Manual testing performed
- [ ] Edge cases considered

## Screenshots (if UI changes)
[Add screenshots here]

## Breaking Changes
List any breaking changes or "None"

## Related Issues
Closes #123 (if applicable)
```

### PR Review Process

1. **Automated checks**: CI must pass (lint, typecheck, tests)
2. **Code review**: Wait for review if team has multiple developers
3. **Address feedback**: Make requested changes
4. **Squash merge**: Merge using squash merge to keep history clean
5. **Delete branch**: Branch will auto-delete after merge

## Commit Message Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/):

### Format

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

```bash
feat(model): add injury weighting to ensemble
fix(ui): prevent margin input overflow on mobile
chore(deps): upgrade Next.js to 15.5.15
docs: update branching strategy
test(model): add ELO rating edge case tests
```

### Rules

- Use present tense ("add" not "added")
- Keep first line under 72 characters
- Add body for non-obvious changes
- Reference issues in footer: `Closes #123`

## Code Review Guidelines

### As a Reviewer

- **Be constructive**: Suggest improvements, don't just criticize
- **Be specific**: Point to exact lines and explain why
- **Be timely**: Review within 24 hours when possible
- **Check for**:
  - Code follows project standards
  - Tests are adequate
  - No obvious bugs or edge cases missed
  - Documentation is updated if needed

### As an Author

- **Be responsive**: Address feedback promptly
- **Be open**: Consider suggestions even if you disagree initially
- **Be clear**: Explain your reasoning if you disagree
- **Update the PR**: Push changes and re-request review

## Development Commands

| Command | Purpose |
|---------|---------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run start` | Start production server |
| `npm run lint` | Run ESLint |
| `npm run typecheck` | Run TypeScript type checking |
| `npm test` | Run frontend tests |
| `npm run check` | Run lint + typecheck + tests |
| `npm run test:python` | Run Python tests |
| `npm run check:all` | Run all checks (frontend + Python) |

## Project Architecture

### Key Concepts

- **Serverless**: No database, data baked into JSON files
- **Static generation**: Data committed to repo, served via Vercel
- **Edge runtime**: API routes run on Vercel Edge Network
- **Automated updates**: GitHub Actions refreshes data weekly

### Key Files

| File | Purpose |
|------|---------|
| `data/current_round_tips.json` | Current round tips + results |
| `data/archive/round_N.json` | Canonical per-round snapshot |
| `data/ladder.json` | Current NRL ladder |
| `data/last_update.json` | Freshness metadata |
| `scripts/update_tips.py` | Main data pipeline script |

### Architecture Decisions

See [.kiro/steering/project-overview.md](.kiro/steering/project-overview.md) for detailed architecture decisions and rationale.

## Getting Help

- **Documentation**: Check `.kiro/steering/` for project guidance
- **Git workflow**: See `.kiro/steering/git-workflow.md`
- **Coding standards**: See `.kiro/steering/coding-standards.md`
- **Issues**: Open a GitHub issue for bugs or feature requests
- **Questions**: Open a discussion on GitHub

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see LICENSE file).

## Additional Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Python Style Guide (PEP 8)](https://pep8.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Vitest Documentation](https://vitest.dev/)
- [pytest Documentation](https://docs.pytest.org/)

---

Thank you for contributing to Footy Tipping! 🏉

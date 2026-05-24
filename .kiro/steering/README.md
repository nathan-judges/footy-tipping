# Steering Files Overview

This directory contains project-wide guidance and standards that are automatically included in Kiro's context.

## Core Documentation

### [project-overview.md](./project-overview.md)
High-level architecture and key decisions:
- Stack: Next.js 15, React 19, TypeScript, Tailwind v4, Python 3.13
- Serverless architecture with baked JSON data
- No database (until specific needs arise)
- Key data files and their purposes
- Correctness invariants

### [coding-standards.md](./coding-standards.md)
Code quality and style guidelines:
- TypeScript strict mode, no `any`
- React/Next.js App Router patterns
- Python PEP 8 compliance
- Testing requirements (Vitest, pytest)
- Conventional Commits format
- File organization structure

### [git-workflow.md](./git-workflow.md) ⭐ NEW
Branching strategy and Git operations:
- Branch naming conventions (`feat/`, `fix/`, `chore/`)
- PR workflow and merge strategy
- Commit message format (Conventional Commits)
- CI/CD integration
- GitHub settings recommendations
- Migration plan for current branch
- Troubleshooting common scenarios

### [implementation-plan.md](./implementation-plan.md)
Outstanding work and completed features:
- Priority-ordered improvements
- Data pipeline enhancements needed
- Test coverage gaps
- Completed features checklist

## Skills Directory

The `.kiro/skills/` directory contains reusable operation guides:

### [git-operations.md](../skills/git-operations.md) ⭐ NEW
Common Git workflows:
- Starting new feature work
- Keeping branches current
- Creating pull requests
- Commit message guidelines
- Pre-commit and pre-PR checklists
- Quick reference commands

### [sync-current-branch.md](../skills/sync-current-branch.md) ⭐ NEW
Specific guide for current branch situation:
- Syncing `cursor/fix-vercel-app-router` with main
- Renaming to follow conventions
- Handling rebase conflicts
- Post-merge cleanup

## How These Files Work

### Steering Files (Always Included)
Files in `.kiro/steering/` are automatically included in Kiro's context for every interaction. They provide consistent guidance across all work.

### Skills (On-Demand)
Files in `.kiro/skills/` are loaded on-demand when relevant to the current task. They provide detailed step-by-step instructions for specific operations.

## Quick Links

**Starting new work?** → Read [git-workflow.md](./git-workflow.md) and [git-operations.md](../skills/git-operations.md)

**Need to sync current branch?** → Follow [sync-current-branch.md](../skills/sync-current-branch.md)

**Writing code?** → Follow [coding-standards.md](./coding-standards.md)

**Planning features?** → Check [implementation-plan.md](./implementation-plan.md)

**Understanding architecture?** → Read [project-overview.md](./project-overview.md)

## Maintenance

These files should be updated when:
- Architecture decisions change
- New patterns emerge
- Standards evolve
- Common issues are identified
- Workflows are refined

Keep them concise, actionable, and current.

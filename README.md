# Footy Tipping 🏉

[![CI](https://github.com/nathan-judges/footy-tipping/actions/workflows/ci.yml/badge.svg)](https://github.com/nathan-judges/footy-tipping/actions/workflows/ci.yml)
[![Deploy](https://img.shields.io/badge/deploy-vercel-black)](https://vercel.com)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A serverless NRL tipping application using baked JSON data, Next.js, and machine learning predictions.

## ✨ Features

- **AI-Powered Predictions**: ELO-based ensemble model for match predictions
- **Interactive Tipping**: Save your picks locally (no login required)
- **Live Updates**: Pre-kickoff polling for last-minute changes
- **Historical Archive**: View past rounds with accuracy tracking
- **Margin Game**: Select confidence picks with margin predictions
- **Responsive Design**: Works on desktop and mobile

## 🚀 Quick Start

### Prerequisites

- Node.js 20.x or later
- Python 3.13
- npm (comes with Node.js)

### Installation

```bash
# Clone the repository
git clone https://github.com/nathan-judges/footy-tipping.git
cd footy-tipping

# Install Node.js dependencies
npm install

# Set up Python environment
python3.13 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Copy environment file
cp .env.example .env
# Edit .env and add your ODDS_API_KEY if needed
```

### Development

```bash
# Start development server
npm run dev

# Run all checks (lint + typecheck + tests)
npm run check

# Run Python tests
npm run test:python

# Run everything
npm run check:all
```

Visit [http://localhost:3000](http://localhost:3000) to see the app.

## 📚 Documentation

- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute to this project
- **[Security Policy](SECURITY.md)** - Security practices and reporting
- **[Git Workflow](.kiro/steering/git-workflow.md)** - Branching strategy and Git operations
- **[Coding Standards](.kiro/steering/coding-standards.md)** - Code quality guidelines
- **[Project Overview](.kiro/steering/project-overview.md)** - Architecture and key decisions
- **[Implementation Plan](.kiro/steering/implementation-plan.md)** - Outstanding work and roadmap

## 🏗️ Architecture

### Stack

- **Frontend**: Next.js 15 (App Router), React 19, TypeScript (strict), Tailwind v4
- **Backend**: Edge API routes, no database
- **Data Pipeline**: Python 3.13, ELO ratings, ensemble model
- **Hosting**: Vercel (frontend) + GitHub Actions (data pipeline)
- **Testing**: Vitest (frontend), pytest (Python)

### Data Flow

```
NRL API → Python Pipeline → Baked JSON → Git Commit → Vercel Deploy → Edge CDN
```

1. **Data Collection**: Python scripts fetch NRL fixtures, ladder, and odds
2. **Prediction**: ELO-based ensemble model generates tips
3. **Baking**: Results written to JSON files in `data/`
4. **Commit**: GitHub Actions commits updated data to main branch
5. **Deploy**: Vercel automatically deploys on commit
6. **Serve**: Static JSON served via Edge CDN

### Key Files

| File | Purpose |
|------|---------|
| `data/current_round_tips.json` | Current round tips + results |
| `data/archive/round_N.json` | Historical round snapshots |
| `data/ladder.json` | Current NRL ladder |
| `data/last_update.json` | Freshness metadata |
| `scripts/update_tips.py` | Main data pipeline script |

## 🧪 Testing

### Frontend Tests

```bash
npm test                    # Run Vitest tests
npm run test:watch          # Watch mode
```

### Python Tests

```bash
pytest tests/python/                              # Run all tests
pytest tests/python/ --cov=scripts/lib            # With coverage
pytest tests/python/ -v                           # Verbose output
```

### All Checks

```bash
npm run check               # Lint + typecheck + frontend tests
npm run check:all           # Everything including Python tests
```

## 🔄 Data Pipeline

### Local Development

```bash
# Dry run (no file writes)
python scripts/update_tips.py --dry-run

# Generate baked files locally
python scripts/update_tips.py --write

# Generate for specific round
python scripts/update_tips.py --write --round 8 --season 2026

# Backfill multiple rounds
python scripts/update_tips.py --write --season 2026 --archive-through 8
```

### Automated Updates

- **Schedule**: Tuesday and Thursday at midnight UTC
- **Workflow**: `.github/workflows/update-tips.yml`
- **Manual trigger**: Available via GitHub Actions UI
- **Bot commits**: Automated commits as `tipping-bot[bot]`

## 📊 Features in Detail

### Predictions

- **ELO Ratings**: Team strength based on historical performance
- **Ensemble Model**: Combines multiple prediction methods
- **Margin Predictions**: Confidence-weighted margin estimates
- **Backtesting**: Historical accuracy tracking

### User Experience

- **Local Storage**: Picks saved in browser (no account needed)
- **Round Navigation**: View any round (current or historical)
- **Accuracy Tracking**: Compare your picks vs model predictions
- **Live Override**: Last-minute updates within 10 min of kickoff
- **Responsive Design**: Works on all devices

### Archive

- **Historical Rounds**: View past rounds with results
- **Accuracy Metrics**: Model and personal accuracy percentages
- **Deduplication**: Latest snapshot wins for each round
- **Snapshots**: Multiple dated snapshots per round supported

## 🛠️ Development Commands

| Command | Purpose |
|---------|---------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run start` | Start production server |
| `npm run lint` | Run ESLint |
| `npm run typecheck` | TypeScript type checking |
| `npm test` | Run frontend tests |
| `npm run check` | Lint + typecheck + tests |
| `npm run test:python` | Run Python tests |
| `npm run check:all` | All checks (frontend + Python) |

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:

- Development workflow
- Code standards
- Testing requirements
- Pull request process
- Commit message guidelines

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔒 Security

See our [Security Policy](SECURITY.md) for information on:

- Reporting vulnerabilities
- Supported versions
- Security best practices

## 📧 Contact

- **Issues**: [GitHub Issues](https://github.com/nathan-judges/footy-tipping/issues)
- **Discussions**: [GitHub Discussions](https://github.com/nathan-judges/footy-tipping/discussions)

## 🙏 Acknowledgments

- NRL for providing public fixture and ladder data
- The Odds API for betting odds data
- Vercel for hosting and deployment
- Open source community for amazing tools

---

Built with ❤️ using Next.js, React, and Python

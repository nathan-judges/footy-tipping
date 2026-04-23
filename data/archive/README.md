Store historical baked snapshots in this folder as JSON files.

Suggested naming:
- `round_1.json` (canonical per-round file, overwritten on new snapshot)
- `2026-04-23_round_1.json` (dated snapshots, append-only)

Each file should follow the same shape as `data/current_round_tips.json`.

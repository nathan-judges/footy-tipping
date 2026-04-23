# NRL API notes

These endpoints are currently used by the baking pipeline and were verified on 2026-04-23.

## Fixtures by round

- Endpoint: `https://www.nrl.com/draw/data?competition=111&round=<ROUND>&season=<SEASON>`
- Example: `https://www.nrl.com/draw/data?competition=111&round=8&season=2026`
- Auth: none required
- Important fields:
  - `fixtures[]`
  - `fixtures[].matchCentreUrl` (used to derive `nrlSlug`)
  - `fixtures[].matchState` and `fixtures[].matchMode` (mapped to `status`)
  - `fixtures[].homeTeam.nickName`, `fixtures[].awayTeam.nickName`
  - `fixtures[].clock.kickOffTimeLong`
  - `fixtures[].homeTeam.score`, `fixtures[].awayTeam.score` (present on completed games)

## Ladder

- Endpoint: `https://www.nrl.com/ladder/data?competition=111&season=<SEASON>`
- Example: `https://www.nrl.com/ladder/data?competition=111&season=2026`
- Auth: none required
- Important fields:
  - `positions[]`
  - `positions[].teamNickname`
  - `positions[].stats.played`
  - `positions[].stats.wins`
  - `positions[].stats.lost`
  - `positions[].stats.points`
  - `positions[].stats.points for`
  - `positions[].stats.points against`
  - `positions[].stats.points difference`

## Notes and caveats

- The draw payload currently does not reliably expose a numeric match id for every fixture. We always populate `nrlSlug` and populate `nrlMatchId` when discoverable.
- Fallback path in `scripts/lib/fetch_data.py` scrapes the draw page HTML and parses embedded `__NEXT_DATA__` JSON if direct API calls fail.
- Keep an eye on naming changes (for example `matchState` values) because the API is internal and may change without notice.

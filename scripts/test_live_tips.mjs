#!/usr/bin/env node

const baseUrl = process.env.BASE_URL || "http://localhost:3000";
const gameId = process.env.GAME_ID;

if (!gameId) {
  console.error("Missing GAME_ID environment variable.");
  process.exit(1);
}

const url = `${baseUrl}/api/live-tips?gameId=${encodeURIComponent(gameId)}`;
const response = await fetch(url);
if (!response.ok) {
  console.error(`Request failed: ${response.status} ${response.statusText}`);
  process.exit(1);
}

const payload = await response.json();
if (payload.gameId !== gameId || !("tipOverride" in payload) || !("checkedAt" in payload)) {
  console.error("Invalid response shape:", payload);
  process.exit(1);
}

console.log("live-tips check passed");
console.log(JSON.stringify(payload, null, 2));

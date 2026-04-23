import type { RoundGameTip } from "@/lib/types";

export function getNrlMatchUrl(game: RoundGameTip, season: number, round: number): string {
  if (game.nrlSlug) {
    return `https://www.nrl.com/draw/nrl-premiership/${season}/round-${round}/${game.nrlSlug}/`;
  }
  return "https://www.nrl.com/draw/";
}


import tipsData from "../../data/current_round_tips.json";
import updateData from "../../data/last_update.json";
import ladderData from "../../data/ladder.json";
import type { CurrentRoundTips, LadderData, LastUpdateMeta } from "./types";

export function loadCurrentRoundTips(): CurrentRoundTips {
  return tipsData as CurrentRoundTips;
}

export function loadLastUpdateMeta(): LastUpdateMeta {
  return updateData as LastUpdateMeta;
}

export function loadLadder(): LadderData {
  return ladderData as LadderData;
}

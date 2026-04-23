import tipsData from "../../data/current_round_tips.json";
import updateData from "../../data/last_update.json";
import ladderData from "../../data/ladder.json";
import seasonMetaData from "../../data/season_meta.json";
import type { CurrentRoundTips, LadderData, LastUpdateMeta, SeasonMeta } from "./types";

export function loadCurrentRoundTips(): CurrentRoundTips {
  return tipsData as CurrentRoundTips;
}

export function loadLastUpdateMeta(): LastUpdateMeta {
  return updateData as LastUpdateMeta;
}

export function loadLadder(): LadderData {
  return ladderData as LadderData;
}

export function loadSeasonMeta(): SeasonMeta {
  return seasonMetaData as SeasonMeta;
}

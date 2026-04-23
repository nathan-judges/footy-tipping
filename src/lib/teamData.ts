export interface TeamIdentity {
  primary: string;
  secondary: string;
  shortName: string;
}

const fallbackTeam: TeamIdentity = {
  primary: "#d0d7de",
  secondary: "#1f2328",
  shortName: "NRL"
};

export const TEAM_DATA: Record<string, TeamIdentity> = {
  Broncos: { primary: "#6F1E51", secondary: "#F5D76E", shortName: "BRI" },
  Bulldogs: { primary: "#0057B8", secondary: "#FFFFFF", shortName: "CBY" },
  Cowboys: { primary: "#002B5C", secondary: "#FFC72C", shortName: "NQL" },
  Dolphins: { primary: "#A50044", secondary: "#FFFFFF", shortName: "DOL" },
  Dragons: { primary: "#D2112C", secondary: "#FFFFFF", shortName: "STG" },
  Eels: { primary: "#003DA5", secondary: "#FFCC00", shortName: "PAR" },
  Knights: { primary: "#D71920", secondary: "#00529B", shortName: "NEW" },
  Panthers: { primary: "#111111", secondary: "#7A7A7A", shortName: "PEN" },
  Rabbitohs: { primary: "#006341", secondary: "#FFFFFF", shortName: "SOU" },
  Raiders: { primary: "#7A9A01", secondary: "#FFFFFF", shortName: "CAN" },
  Roosters: { primary: "#D71920", secondary: "#FFFFFF", shortName: "SYD" },
  "Sea Eagles": { primary: "#6D1A36", secondary: "#FFFFFF", shortName: "MAN" },
  Sharks: { primary: "#00A3E0", secondary: "#111111", shortName: "CRO" },
  Storm: { primary: "#4B2E83", secondary: "#FFFFFF", shortName: "MEL" },
  Titans: { primary: "#00A3E0", secondary: "#F7B500", shortName: "GLD" },
  Warriors: { primary: "#111111", secondary: "#FFFFFF", shortName: "NZW" },
  "Wests Tigers": { primary: "#F37021", secondary: "#111111", shortName: "WTI" }
};

export function getTeamIdentity(teamName: string): TeamIdentity {
  return TEAM_DATA[teamName] ?? fallbackTeam;
}

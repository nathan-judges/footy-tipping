export interface TeamIdentity {
  primary: string;
  secondary: string;
  shortName: string;
  logoPath: string;
}

const fallbackTeam: TeamIdentity = {
  primary: "#d0d7de",
  secondary: "#1f2328",
  shortName: "NRL",
  logoPath: "/team-logos/nrl.png"
};

export const TEAM_DATA: Record<string, TeamIdentity> = {
  Broncos: { primary: "#7B0055", secondary: "#FFCC33", shortName: "BRI", logoPath: "/team-logos/broncos.png" },
  Bulldogs: { primary: "#1F4BA8", secondary: "#FFFFFF", shortName: "CBY", logoPath: "/team-logos/bulldogs.png" },
  Cowboys: { primary: "#0B2A67", secondary: "#F7C600", shortName: "NQL", logoPath: "/team-logos/cowboys.png" },
  Dolphins: { primary: "#F05A84", secondary: "#FFFFFF", shortName: "DOL", logoPath: "/team-logos/dolphins.png" },
  Dragons: { primary: "#CE1126", secondary: "#FFFFFF", shortName: "STG", logoPath: "/team-logos/dragons.png" },
  Eels: { primary: "#0052A5", secondary: "#F7C600", shortName: "PAR", logoPath: "/team-logos/eels.png" },
  Knights: { primary: "#D51F2B", secondary: "#FFFFFF", shortName: "NEW", logoPath: "/team-logos/knights.png" },
  Panthers: { primary: "#111111", secondary: "#6D6E71", shortName: "PEN", logoPath: "/team-logos/panthers.png" },
  Rabbitohs: { primary: "#006B3F", secondary: "#FFFFFF", shortName: "SOU", logoPath: "/team-logos/rabbitohs.png" },
  Raiders: { primary: "#2C8C4A", secondary: "#0A4E7A", shortName: "CAN", logoPath: "/team-logos/raiders.png" },
  Roosters: { primary: "#CC1F2F", secondary: "#17478F", shortName: "SYD", logoPath: "/team-logos/roosters.png" },
  "Sea Eagles": { primary: "#6B1E4B", secondary: "#D4AF63", shortName: "MAN", logoPath: "/team-logos/sea-eagles.png" },
  Sharks: { primary: "#00A9E0", secondary: "#111111", shortName: "CRO", logoPath: "/team-logos/sharks.png" },
  Storm: { primary: "#4A247E", secondary: "#FFFFFF", shortName: "MEL", logoPath: "/team-logos/storm.png" },
  Titans: { primary: "#00A3E0", secondary: "#F5C242", shortName: "GLD", logoPath: "/team-logos/titans.png" },
  Warriors: { primary: "#1F8A57", secondary: "#2A3D8F", shortName: "NZW", logoPath: "/team-logos/warriors.png" },
  "Wests Tigers": { primary: "#F26A21", secondary: "#111111", shortName: "WTI", logoPath: "/team-logos/wests-tigers.png" }
};

export function getTeamIdentity(teamName: string): TeamIdentity {
  return TEAM_DATA[teamName] ?? fallbackTeam;
}

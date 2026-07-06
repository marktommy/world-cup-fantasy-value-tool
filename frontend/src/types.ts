// Shape of the data emitted by the Python pipeline (data/output/players.json).

export type Position = "GK" | "DF" | "MF" | "FW";

export interface MatchProjection {
  opponent: string;
  opponent_rating: number;
  xp: number;
  floor: number;
  ceiling: number;
  p_haul: number; // probability of a 9+ point haul
}

export interface Player {
  name: string;
  nation: string;
  nation_code: string;
  group: string;
  position: Position;
  club: string | null;
  age: number | null;
  caps: number | null;
  team_rating: number;
  price: number;
  xp_per_match: number;
  group_xp: number;
  value: number;
  ceiling: number;
  floor: number;
  p_start: number;
  goals90: number;
  assists90: number;
  sample_90s: number;
  matches: MatchProjection[];
  xp_rank: number;
  value_rank: number;
}

export interface Meta {
  generated_at: string;
  n_players: number;
  n_nations: number;
  price_source: string;
  scoring: string;
  horizon: string;
  positions: Position[];
  groups: string[];
}

export interface Dataset {
  meta: Meta;
  players: Player[];
}

// Small formatting + presentation helpers shared across components.

// FIFA 3-letter code -> ISO-2 (for flagcdn.com flag images).
const ISO2: Record<string, string> = {
  ALG: "dz", ARG: "ar", AUS: "au", AUT: "at", BEL: "be", BIH: "ba", BRA: "br",
  CPV: "cv", CAN: "ca", COL: "co", COD: "cd", CRO: "hr", CUW: "cw", CZE: "cz",
  CIV: "ci", ECU: "ec", EGY: "eg", ENG: "gb-eng", FRA: "fr", GER: "de", GHA: "gh",
  HAI: "ht", IRN: "ir", IRQ: "iq", JPN: "jp", JOR: "jo", KOR: "kr", MEX: "mx",
  MAR: "ma", NED: "nl", NZL: "nz", NOR: "no", PAN: "pa", PAR: "py", POR: "pt",
  QAT: "qa", KSA: "sa", SCO: "gb-sct", SEN: "sn", RSA: "za", ESP: "es", SWE: "se",
  SUI: "ch", TUN: "tn", TUR: "tr", USA: "us", URU: "uy", UZB: "uz",
};

export function flagUrl(code: string): string {
  const iso = ISO2[code] ?? "un";
  return `https://flagcdn.com/w40/${iso}.png`;
}

export const fmt = (n: number | null | undefined, digits = 1): string =>
  n == null ? "—" : n.toFixed(digits);

// Interpolate a red -> amber -> green colour for a 0..1 heat value.
export function heatColor(t: number): string {
  const clamped = Math.max(0, Math.min(1, t));
  // two-stop lerp through amber at 0.5
  const lerp = (a: number, b: number, x: number) => Math.round(a + (b - a) * x);
  let r: number, g: number, b: number;
  if (clamped < 0.5) {
    const x = clamped / 0.5; // red -> amber
    r = lerp(185, 183, x); g = lerp(28, 121, x); b = lerp(28, 31, x);
  } else {
    const x = (clamped - 0.5) / 0.5; // amber -> green
    r = lerp(183, 14, x); g = lerp(121, 159, x); b = lerp(31, 110, x);
  }
  return `rgb(${r}, ${g}, ${b})`;
}

// Soft background version of the heat colour, for pills.
export function heatBg(t: number): string {
  const c = heatColor(t);
  return c.replace("rgb(", "rgba(").replace(")", ", 0.12)");
}

export const POSITIONS = ["GK", "DF", "MF", "FW"] as const;
export const POSITION_LABEL: Record<string, string> = {
  GK: "Goalkeeper", DF: "Defender", MF: "Midfielder", FW: "Forward",
};

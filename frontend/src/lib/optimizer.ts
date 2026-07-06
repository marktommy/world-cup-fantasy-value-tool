// Budget-constrained squad optimiser.
//
// Picks a 15-player fantasy squad (2 GK, 5 DF, 5 MF, 3 FW) that maximises total
// group-stage expected points subject to: a total budget, and at most 3 players per
// nation (the real World Cup Fantasy constraint).
//
// We solve it by Lagrangian relaxation. Instead of a hard budget, we penalise price:
// each player is scored group_xp − λ·price, and we greedily fill the positional slots
// (respecting the nation cap) by that score. A larger λ makes the squad cheaper, so we
// binary-search λ for the smallest penalty whose squad fits the budget — this spends the
// budget efficiently, unlike a naive "buy the biggest upgrades" greedy. A final local
// pass swaps in any affordable upgrades to use up leftover funds.

import type { Player, Position } from "../types";

export const SQUAD_SHAPE: Record<Position, number> = { GK: 2, DF: 5, MF: 5, FW: 3 };
export const MAX_PER_NATION = 3;
const XI_MIN: Record<Position, number> = { GK: 1, DF: 3, MF: 2, FW: 1 };

export interface OptimResult {
  squad: Player[];
  startingXI: Set<string>;
  totalCost: number;
  totalXp: number; // sum of the starting XI's expected points
  feasible: boolean;
}

const key = (p: Player) => `${p.name}|${p.nation_code}`;

// Greedily fill the squad slots by (group_xp − λ·price), honouring position quotas
// and the per-nation cap.
function selectForLambda(players: Player[], lambda: number): { squad: Player[]; cost: number } {
  const scored = players
    .map((p) => ({ p, s: p.group_xp - lambda * p.price }))
    .sort((a, b) => b.s - a.s);

  const left: Record<Position, number> = { ...SQUAD_SHAPE };
  const nations: Record<string, number> = {};
  const squad: Player[] = [];
  let need = 15;

  for (const { p } of scored) {
    if (need === 0) break;
    if (left[p.position] <= 0) continue;
    if ((nations[p.nation_code] ?? 0) >= MAX_PER_NATION) continue;
    squad.push(p);
    left[p.position]--;
    nations[p.nation_code] = (nations[p.nation_code] ?? 0) + 1;
    need--;
  }
  return { squad, cost: squad.reduce((s, p) => s + p.price, 0) };
}

export function optimiseSquad(players: Player[], budget: number): OptimResult {
  if (players.length < 15) return emptyResult();

  // Scan the penalty (λ) frontier to gather candidate squads. Each λ yields a
  // different mix: small λ = expensive/strong, large λ = cheap. We collect the
  // distinct budget-feasible ones (keyed by cost so we don't polish duplicates).
  const candidates = new Map<number, Player[]>();
  for (let lambda = 0; lambda <= 8; lambda += 0.04) {
    const { squad, cost } = selectForLambda(players, lambda);
    if (cost <= budget) candidates.set(Math.round(cost * 2), squad);
  }
  if (candidates.size === 0) {
    const cheapest = selectForLambda(players, 999);
    return { ...pickStartingXI(cheapest.squad), squad: cheapest.squad,
             totalCost: cheapest.cost, feasible: false };
  }

  // Multi-start local search: polish a spread of candidates and keep the best XI.
  // Cheaper candidates leave spare budget for polish to buy premium-value players,
  // which escapes the "full budget spent on mediocre players" trap. We sample an
  // evenly-spaced subset (by cost) so this stays fast enough for a live slider.
  const starts = sampleEvenly([...candidates.values()], 24);
  let bestSquad: Player[] | null = null;
  let bestXi = { startingXI: new Set<string>(), totalXp: -Infinity };
  for (const start of starts) {
    const squad = polish(start, players, budget);
    const xi = pickStartingXI(squad);
    if (xi.totalXp > bestXi.totalXp) { bestXi = xi; bestSquad = squad; }
  }

  const squad = bestSquad!;
  const cost = squad.reduce((s, p) => s + p.price, 0);
  return { squad, startingXI: bestXi.startingXI, totalXp: bestXi.totalXp,
           totalCost: cost, feasible: true };
}

// Spend any leftover budget: repeatedly apply the best affordable single-player upgrade.
function polish(base: Player[], players: Player[], budget: number): Player[] {
  const squad = [...base];
  const inSquad = new Set(squad.map(key));
  const byPos: Record<Position, Player[]> = { GK: [], DF: [], MF: [], FW: [] };
  for (const p of players) byPos[p.position].push(p);
  for (const pos of Object.keys(byPos) as Position[]) byPos[pos].sort((a, b) => b.group_xp - a.group_xp);

  let cost = squad.reduce((s, p) => s + p.price, 0);
  for (let iter = 0; iter < 60; iter++) {
    let best: { i: number; cand: Player; gain: number } | null = null;
    for (let i = 0; i < squad.length; i++) {
      const cur = squad[i];
      for (const cand of byPos[cur.position]) {
        if (inSquad.has(key(cand))) continue;
        const gain = cand.group_xp - cur.group_xp;
        if (gain <= 0) break;
        if (cost - cur.price + cand.price > budget) continue;
        const nations: Record<string, number> = {};
        for (const p of squad) if (p !== cur) nations[p.nation_code] = (nations[p.nation_code] ?? 0) + 1;
        if ((nations[cand.nation_code] ?? 0) >= MAX_PER_NATION) continue;
        if (!best || gain > best.gain) best = { i, cand, gain };
      }
    }
    if (!best) break;
    inSquad.delete(key(squad[best.i]));
    cost += best.cand.price - squad[best.i].price;
    squad[best.i] = best.cand;
    inSquad.add(key(best.cand));
  }
  return squad;
}

// Choose the 11 highest-xP players that form a valid formation.
function pickStartingXI(squad: Player[]): { startingXI: Set<string>; totalXp: number } {
  const byPos: Record<Position, Player[]> = { GK: [], DF: [], MF: [], FW: [] };
  for (const p of squad) byPos[p.position].push(p);
  for (const pos of Object.keys(byPos) as Position[]) byPos[pos].sort((a, b) => b.group_xp - a.group_xp);

  const xi: Player[] = [];
  for (const pos of Object.keys(XI_MIN) as Position[]) xi.push(...byPos[pos].slice(0, XI_MIN[pos]));
  const chosen = new Set(xi.map(key));
  const rest = squad
    .filter((p) => !chosen.has(key(p)) && p.position !== "GK")
    .sort((a, b) => b.group_xp - a.group_xp);
  xi.push(...rest.slice(0, 11 - xi.length));

  return { startingXI: new Set(xi.map(key)), totalXp: xi.reduce((s, p) => s + p.group_xp, 0) };
}

// Take up to `n` evenly-spaced items from a list (keeps the variety without
// polishing hundreds of near-identical candidates).
function sampleEvenly<T>(items: T[], n: number): T[] {
  if (items.length <= n) return items;
  const step = (items.length - 1) / (n - 1);
  return Array.from({ length: n }, (_, i) => items[Math.round(i * step)]);
}

function emptyResult(): OptimResult {
  return { squad: [], startingXI: new Set(), totalCost: 0, totalXp: 0, feasible: false };
}

export { key as playerKey };

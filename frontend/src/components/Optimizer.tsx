// The "Optimizer" view: solve for the budget-constrained squad that maximises
// projected group-stage points, and lay the starting XI out on a pitch.

import { useMemo, useState } from "react";
import type { Player, Position } from "../types";
import { optimiseSquad, playerKey, SQUAD_SHAPE, MAX_PER_NATION } from "../lib/optimizer";
import { Flag } from "./atoms";
import { fmt } from "../lib/format";

const ORDER: Position[] = ["GK", "DF", "MF", "FW"];

function PitchCard({ p }: { p: Player }) {
  return (
    <div className="pitch-card">
      <img className="pc-flag" src={`https://flagcdn.com/w20/${p.nation_code.toLowerCase()}.png`}
           alt="" onError={(e) => ((e.target as HTMLImageElement).style.visibility = "hidden")} />
      <div className="pc-name">{p.name}</div>
      <div className="pc-meta num">${fmt(p.price, 1)}</div>
      <div className="pc-stat num">{fmt(p.group_xp, 1)} xP</div>
    </div>
  );
}

export default function Optimizer({ players }: { players: Player[] }) {
  const [budget, setBudget] = useState(100);
  const result = useMemo(() => optimiseSquad(players, budget), [players, budget]);

  const xi = result.squad.filter((p) => result.startingXI.has(playerKey(p)));
  const bench = result.squad.filter((p) => !result.startingXI.has(playerKey(p)));
  const xiByPos = (pos: Position) => xi.filter((p) => p.position === pos);

  return (
    <div className="opt-layout">
      <div className="opt-controls">
        <div className="card">
          <div className="field">
            <label>Budget <span className="rangeval num">${budget.toFixed(1)}</span></label>
            <input type="range" min={92} max={130} step={1} value={budget}
                   onChange={(e) => setBudget(parseFloat(e.target.value))} />
          </div>

          <div className="squad-summary">
            <div className="metric">
              <div className="m-val num">{fmt(result.totalXp, 1)}</div>
              <div className="m-lab">XI xP</div>
            </div>
            <div className="metric">
              <div className="m-val num">${fmt(result.totalCost, 1)}</div>
              <div className="m-lab">Squad cost</div>
            </div>
            <div className="metric">
              <div className="m-val num">${fmt(budget - result.totalCost, 1)}</div>
              <div className="m-lab">In the bank</div>
            </div>
          </div>

          <p className="muted" style={{ fontSize: 12.5, lineHeight: 1.6, marginTop: 4 }}>
            Optimiser picks a 15-player squad
            (<b>{SQUAD_SHAPE.GK} GK, {SQUAD_SHAPE.DF} DF, {SQUAD_SHAPE.MF} MF, {SQUAD_SHAPE.FW} FW</b>)
            maximising total group-stage xP under the budget, with at most{" "}
            <b>{MAX_PER_NATION} players per nation</b>. Drag the budget to see how the
            optimal squad shifts.
          </p>
        </div>
      </div>

      <div>
        <div className="pitch">
          {ORDER.map((pos) => (
            <div className="pitch-row" key={pos}>
              {xiByPos(pos).map((p) => <PitchCard key={playerKey(p)} p={p} />)}
            </div>
          ))}
        </div>

        <div className="section-label">Bench</div>
        <div className="pitch-row" style={{ justifyContent: "flex-start", gap: 12 }}>
          {bench.map((p) => (
            <div className="chip" key={playerKey(p)}>
              <Flag code={p.nation_code} /> {p.name} · {p.position} · ${fmt(p.price, 1)}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

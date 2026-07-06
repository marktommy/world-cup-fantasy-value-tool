// Slide-in detail panel for a single player: headline metrics, a per-opponent
// expected-points breakdown, and the underlying model inputs.

import type { Player } from "../types";
import { Flag, PositionBadge, RangeBar } from "./atoms";
import { fmt, POSITION_LABEL } from "../lib/format";

export default function PlayerDetail({ player, onClose }: { player: Player; onClose: () => void }) {
  const maxCeil = Math.max(...player.matches.map((m) => m.ceiling), 6);

  return (
    <>
      <div className="overlay" onClick={onClose} />
      <aside className="panel" role="dialog" aria-label={`${player.name} detail`}>
        <div className="panel-head">
          <button className="panel-close" onClick={onClose} aria-label="Close">×</button>
          <div className="panel-title">
            <Flag code={player.nation_code} large />
            <div>
              <h2>{player.name}</h2>
              <div className="player-sub">
                <PositionBadge pos={player.position} /> &nbsp;{POSITION_LABEL[player.position]} ·{" "}
                {player.nation} · Group {player.group}
              </div>
            </div>
          </div>
        </div>

        <div className="panel-body">
          <div className="metric-row">
            <div className="metric">
              <div className="m-val num">{fmt(player.group_xp, 1)}</div>
              <div className="m-lab">Group xP</div>
            </div>
            <div className="metric">
              <div className="m-val num">{fmt(player.value, 2)}</div>
              <div className="m-lab">Value</div>
            </div>
            <div className="metric">
              <div className="m-val num">${fmt(player.price, 1)}</div>
              <div className="m-lab">Price</div>
            </div>
          </div>

          <div className="section-label">Expected points by fixture</div>
          {player.matches.map((m) => (
            <div className="fixture" key={m.opponent}>
              <div className="opp">
                <Flag code={m.opponent} />
                <div>
                  <div className="oname">{m.opponent}</div>
                  <div className="orat num">rating {fmt(m.opponent_rating, 0)}</div>
                </div>
              </div>
              <div className="barwrap">
                <RangeBar floor={m.floor} mean={m.xp} ceiling={m.ceiling} max={maxCeil} width={150} />
              </div>
              <div className="fxp num">{fmt(m.xp, 1)}</div>
            </div>
          ))}

          <div className="section-label">Model inputs</div>
          <div className="kv"><span className="k">Team strength rating</span><span className="v num">{fmt(player.team_rating, 1)}</span></div>
          <div className="kv"><span className="k">Start probability</span><span className="v num">{Math.round(player.p_start * 100)}%</span></div>
          <div className="kv"><span className="k">Goals per 90 (shrunk)</span><span className="v num">{fmt(player.goals90, 2)}</span></div>
          <div className="kv"><span className="k">Assists per 90 (shrunk)</span><span className="v num">{fmt(player.assists90, 2)}</span></div>
          <div className="kv"><span className="k">Sample (90s played)</span><span className="v num">{fmt(player.sample_90s, 1)}</span></div>
          <div className="kv"><span className="k">Ceiling / floor per match</span><span className="v num">{fmt(player.ceiling, 1)} / {fmt(player.floor, 1)}</span></div>
          <div className="kv"><span className="k">Club</span><span className="v">{player.club ?? "—"}</span></div>
          <div className="kv"><span className="k">Age · Caps</span><span className="v num">{player.age ?? "—"} · {player.caps ?? "—"}</span></div>
        </div>
      </aside>
    </>
  );
}

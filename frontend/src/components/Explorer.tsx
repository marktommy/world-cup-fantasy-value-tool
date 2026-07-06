// The main "Explorer" view: summary cards, filters, and a sortable player table.

import { useMemo, useState } from "react";
import type { Player } from "../types";
import { Flag, PositionBadge, RangeBar } from "./atoms";
import PlayerDetail from "./PlayerDetail";
import { fmt, heatColor, heatBg, POSITIONS } from "../lib/format";

type SortKey = "group_xp" | "value" | "price" | "xp_per_match" | "team_rating" | "name";

const COLUMNS: { key: SortKey; label: string; left?: boolean }[] = [
  { key: "name", label: "Player", left: true },
  { key: "price", label: "Price" },
  { key: "xp_per_match", label: "xP / match" },
  { key: "group_xp", label: "Group xP" },
  { key: "value", label: "Value" },
];

function StatCards({ players }: { players: Player[] }) {
  const topXp = players.reduce((a, b) => (b.group_xp > a.group_xp ? b : a), players[0]);
  const topVal = players.reduce((a, b) => (b.value > a.value ? b : a), players[0]);
  const avgXp = players.reduce((s, p) => s + p.group_xp, 0) / players.length;
  return (
    <div className="stat-grid">
      <div className="stat">
        <div className="label">Players modelled</div>
        <div className="value num">{players.length.toLocaleString()}</div>
        <div className="sub">across <b>48</b> nations</div>
      </div>
      <div className="stat">
        <div className="label">Highest projected</div>
        <div className="value">{topXp?.name}</div>
        <div className="sub"><b className="num">{fmt(topXp?.group_xp, 1)}</b> group xP</div>
      </div>
      <div className="stat">
        <div className="label">Best value pick</div>
        <div className="value">{topVal?.name}</div>
        <div className="sub"><b className="num">{fmt(topVal?.value, 2)}</b> pts per $</div>
      </div>
      <div className="stat">
        <div className="label">Average group xP</div>
        <div className="value num">{fmt(avgXp, 2)}</div>
        <div className="sub">over 3 group games</div>
      </div>
    </div>
  );
}

export default function Explorer({ players }: { players: Player[] }) {
  const [query, setQuery] = useState("");
  const [pos, setPos] = useState<string>("ALL");
  const [group, setGroup] = useState<string>("ALL");
  const [sort, setSort] = useState<SortKey>("group_xp");
  const [asc, setAsc] = useState(false);
  const [selected, setSelected] = useState<Player | null>(null);

  const groups = useMemo(
    () => Array.from(new Set(players.map((p) => p.group))).sort(),
    [players]
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const rows = players.filter(
      (p) =>
        (pos === "ALL" || p.position === pos) &&
        (group === "ALL" || p.group === group) &&
        (q === "" ||
          p.name.toLowerCase().includes(q) ||
          p.nation.toLowerCase().includes(q) ||
          (p.club ?? "").toLowerCase().includes(q))
    );
    rows.sort((a, b) => {
      const av = a[sort], bv = b[sort];
      const cmp = typeof av === "string" ? av.localeCompare(bv as string) : (av as number) - (bv as number);
      return asc ? cmp : -cmp;
    });
    return rows;
  }, [players, query, pos, group, sort, asc]);

  const maxCeil = useMemo(() => Math.max(...filtered.map((p) => p.ceiling), 6), [filtered]);
  const [vMin, vMax] = useMemo(() => {
    const vals = filtered.map((p) => p.value);
    return [Math.min(...vals), Math.max(...vals)];
  }, [filtered]);

  const clickSort = (key: SortKey) => {
    if (key === sort) setAsc(!asc);
    else { setSort(key); setAsc(false); }
  };

  return (
    <>
      <StatCards players={players} />

      <div className="controls">
        <label className="search">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.5" />
            <path d="M11 11L14 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          <input
            placeholder="Search player, nation or club…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>

        <div className="segmented">
          <button className={pos === "ALL" ? "active" : ""} onClick={() => setPos("ALL")}>All</button>
          {POSITIONS.map((p) => (
            <button key={p} className={pos === p ? "active" : ""} onClick={() => setPos(p)}>{p}</button>
          ))}
        </div>

        <select className="select" value={group} onChange={(e) => setGroup(e.target.value)}>
          <option value="ALL">All groups</option>
          {groups.map((g) => <option key={g} value={g}>Group {g}</option>)}
        </select>
      </div>

      <div className="card table-wrap">
        <table className="players">
          <thead>
            <tr>
              <th className="left" style={{ width: 30 }}>#</th>
              {COLUMNS.map((c) => (
                <th
                  key={c.key}
                  className={`${c.left ? "left" : ""} ${sort === c.key ? "sorted" : ""}`}
                  onClick={() => clickSort(c.key)}
                >
                  {c.label}
                  {sort === c.key && <span className="sort-caret">{asc ? "▲" : "▼"}</span>}
                </th>
              ))}
              <th style={{ width: 130 }}>Range (floor–ceiling)</th>
            </tr>
          </thead>
          <tbody>
            {filtered.slice(0, 300).map((p, i) => {
              const t = vMax > vMin ? (p.value - vMin) / (vMax - vMin) : 0.5;
              return (
                <tr
                  key={`${p.name}-${p.nation_code}`}
                  className={selected === p ? "selected" : ""}
                  onClick={() => setSelected(p)}
                >
                  <td className="left rank num">{i + 1}</td>
                  <td className="left">
                    <div className="player-cell">
                      <Flag code={p.nation_code} />
                      <div>
                        <div className="player-name">{p.name}</div>
                        <div className="player-sub">
                          <PositionBadge pos={p.position} /> {p.nation}
                          {p.club ? ` · ${p.club}` : ""}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="num price">{fmt(p.price, 1)}</td>
                  <td className="num">{fmt(p.xp_per_match, 2)}</td>
                  <td className="num" style={{ fontWeight: 620 }}>{fmt(p.group_xp, 1)}</td>
                  <td>
                    <span className="value-pill num" style={{ color: heatColor(t), background: heatBg(t) }}>
                      {fmt(p.value, 2)}
                    </span>
                  </td>
                  <td>
                    <RangeBar floor={p.floor} mean={p.xp_per_match} ceiling={p.ceiling} max={maxCeil} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {filtered.length === 0 && <div className="empty">No players match those filters.</div>}
      </div>
      {filtered.length > 300 && (
        <p className="muted" style={{ marginTop: 12, fontSize: 12.5 }}>
          Showing the top 300 of {filtered.length.toLocaleString()} matching players — refine with search or filters.
        </p>
      )}

      {selected && <PlayerDetail player={selected} onClose={() => setSelected(null)} />}
    </>
  );
}

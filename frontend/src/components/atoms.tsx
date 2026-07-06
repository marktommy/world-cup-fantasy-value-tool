// Small shared presentational pieces: flag, position badge, and the floor→ceiling
// range bar used in the table and the player panel.

import { flagUrl } from "../lib/format";
import type { Position } from "../types";

export function Flag({ code, large }: { code: string; large?: boolean }) {
  return (
    <img
      className={large ? "flag flag-lg" : "flag"}
      src={flagUrl(code)}
      alt={code}
      loading="lazy"
      onError={(e) => ((e.target as HTMLImageElement).style.visibility = "hidden")}
    />
  );
}

export function PositionBadge({ pos }: { pos: Position }) {
  return <span className={`badge ${pos}`}>{pos}</span>;
}

// A thin bar showing the 10th–90th percentile points range, with a dot at the mean.
export function RangeBar({
  floor, mean, ceiling, max, width = 120,
}: { floor: number; mean: number; ceiling: number; max: number; width?: number }) {
  const h = 18;
  const scale = (v: number) => Math.max(0, Math.min(1, v / max)) * width;
  const x0 = scale(floor);
  const x1 = scale(ceiling);
  const xm = scale(mean);
  return (
    <svg className="rangebar" width={width} height={h} viewBox={`0 0 ${width} ${h}`}>
      <line x1={0} y1={h / 2} x2={width} y2={h / 2} stroke="var(--border)" strokeWidth={1} />
      <rect x={x0} y={h / 2 - 3} width={Math.max(2, x1 - x0)} height={6} rx={3}
        fill="var(--accent-soft)" stroke="var(--accent)" strokeWidth={0.75} />
      <circle cx={xm} cy={h / 2} r={3.4} fill="var(--accent)" />
    </svg>
  );
}

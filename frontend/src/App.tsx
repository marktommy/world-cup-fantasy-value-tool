import { useState } from "react";
import { useDataset } from "./data";
import Explorer from "./components/Explorer";
import Optimizer from "./components/Optimizer";

type Tab = "explorer" | "optimizer";

export default function App() {
  const { data, error } = useDataset();
  const [tab, setTab] = useState<Tab>("explorer");

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <div className="brand-mark">26</div>
            <div>
              <h1>World Cup Fantasy Value</h1>
              <p>Expected-points &amp; value model · FIFA World Cup 2026</p>
            </div>
          </div>

          <nav className="tabs">
            <button className={`tab ${tab === "explorer" ? "active" : ""}`} onClick={() => setTab("explorer")}>
              Explorer
            </button>
            <button className={`tab ${tab === "optimizer" ? "active" : ""}`} onClick={() => setTab("optimizer")}>
              Squad optimizer
            </button>
          </nav>

          {data && (
            <div className="topbar-meta">
              <div><b>{data.meta.n_players.toLocaleString()}</b> players · <b>{data.meta.price_source}</b> prices</div>
              <div>{data.meta.horizon}</div>
            </div>
          )}
        </div>
      </header>

      <main className="container">
        {error && (
          <div className="empty">
            Couldn’t load model data ({error}).<br />
            Run the pipeline first: <code>python run_pipeline.py</code>
          </div>
        )}
        {!data && !error && (
          <div className="empty"><div className="spinner" />Loading projections…</div>
        )}

        {data && tab === "explorer" && <Explorer players={data.players} />}
        {data && tab === "optimizer" && <Optimizer players={data.players} />}

        {data && (
          <div className="footnote">
            Methodology: recency-weighted club + international form → empirical-Bayes shrinkage
            toward position baselines → a Poisson match model driven by team strength
            (live World Cup odds where priced, priors elsewhere) → {" "}
            <b>Monte-Carlo simulation</b> of each fixture for the points distribution.
            Prices are <b>{data.meta.price_source}</b>; value is group-stage xP per unit cost.
            Data generated {new Date(data.meta.generated_at).toLocaleDateString()}.
          </div>
        )}
      </main>
    </div>
  );
}

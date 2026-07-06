import { useEffect, useState } from "react";
import type { Dataset } from "./types";

// Loads the pipeline's players.json (copied into public/data by the export stage).
export function useDataset() {
  const [data, setData] = useState<Dataset | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/players.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);

  return { data, error };
}

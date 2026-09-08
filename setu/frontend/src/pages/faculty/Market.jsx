import { useEffect, useState } from "react";
import { api } from "../../api";
import { ErrorNote, Loading, Stat, useToast } from "../../components/ui";

export default function FacultyMarket() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [lastRun, setLastRun] = useState(null);
  const [showToast, toast] = useToast();

  function load() {
    api.analytics(null).then(setData).catch((err) => setError(err.message));
  }

  useEffect(load, []);

  async function refresh() {
    setBusy(true);
    try {
      const outcome = await api.refreshMarket();
      setLastRun(outcome);
      showToast(`Imported ${outcome.imported} new market postings, skipped ${outcome.skipped}.`);
      load();
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      setBusy(false);
    }
  }

  if (error) return <ErrorNote error={error} />;
  if (!data) return <Loading />;

  return (
    <div className="grid gap-6">
      {toast}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="label">where "market demand" comes from</div>
          <h1 className="font-display text-5xl">Market feed</h1>
        </div>
        <button type="button" className="btn-primary" onClick={refresh} disabled={busy}>
          {busy ? "fetching" : "Refresh from open market"}
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Stat label="internal postings" value={data.active_postings - data.market_postings} hint="posted by recruiters on Setu" />
        <Stat label="market postings" value={data.market_postings} hint="imported from the Arbeitnow public job feed" accent="#7285C2" />
        <Stat label="total demand signal" value={data.active_postings} hint="every gap percentage is computed over this set" accent="#2F9599" />
      </div>

      <section className="card grid gap-3 text-sm text-plum/80">
        <h2 className="font-display text-2xl">How the importer works</h2>
        <p>The backend calls a free public job-board API, reads each posting's title, description and tags, and matches them against Setu's own skill taxonomy with simple keyword patterns.</p>
        <p>A skill mentioned twice or more becomes a must-have at level 3; mentioned once becomes nice-to-have at level 2. Postings with fewer than two recognised skills are skipped so the demand signal stays clean.</p>
        <p>Imported postings are stored with source = market. Students see them scored like any other opening but apply on the company site; faculty analytics count them as demand. The importer is a plain module, so a LinkedIn or Naukri partner feed would plug in at the same place.</p>
        {lastRun && (
          <div className="rounded-2xl bg-petal/60 p-3 font-mono text-xs">
            last run: imported {lastRun.imported}, skipped {lastRun.skipped}, market total {lastRun.total_market_postings}
          </div>
        )}
      </section>
    </div>
  );
}

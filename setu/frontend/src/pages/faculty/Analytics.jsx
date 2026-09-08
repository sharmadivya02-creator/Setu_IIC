import { useEffect, useState } from "react";
import { api } from "../../api";
import { Bar, ErrorNote, Loading, Ring, Stat } from "../../components/ui";

function GapRow({ gap }) {
  return (
    <div className="rounded-2xl bg-white/80 p-3">
      <div className="flex items-center justify-between">
        <div className="font-semibold">{gap.skill}</div>
        <div className="font-mono text-xs" style={{ color: gap.gap > 20 ? "#BC1F2B" : gap.gap > 0 ? "#C08010" : "#2F9599" }}>
          gap {gap.gap > 0 ? "+" : ""}
          {gap.gap}
        </div>
      </div>
      <div className="mt-2 grid gap-1.5">
        <div className="flex items-center gap-2 font-mono text-[11px] text-plum/70">
          <span className="w-28">required by</span>
          <Bar value={gap.demand_pct} color="#7285C2" />
          <span className="w-12 text-right">{gap.demand_pct}%</span>
        </div>
        <div className="flex items-center gap-2 font-mono text-[11px] text-plum/70">
          <span className="w-28">held at any level</span>
          <Bar value={gap.held_pct} color="#95709F" />
          <span className="w-12 text-right">{gap.held_pct}%</span>
        </div>
        <div className="flex items-center gap-2 font-mono text-[11px] text-plum/70">
          <span className="w-28">ready at L{gap.typical_level}+</span>
          <Bar value={gap.ready_pct} color="#2F9599" />
          <span className="w-12 text-right">{gap.ready_pct}%</span>
        </div>
      </div>
    </div>
  );
}

export default function FacultyAnalytics() {
  const [batches, setBatches] = useState([]);
  const [batchId, setBatchId] = useState("");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.batches().then(setBatches).catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    setData(null);
    api.analytics(batchId || null).then(setData).catch((err) => setError(err.message));
  }, [batchId]);

  if (error) return <ErrorNote error={error} />;

  const buckets = data?.readiness_buckets || {};
  const total = data?.student_count || 1;

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="label">cohort skill gaps versus live demand</div>
          <h1 className="font-display text-5xl">Analytics</h1>
        </div>
        <select className="input w-56" value={batchId} onChange={(event) => setBatchId(event.target.value)}>
          <option value="">All batches</option>
          {batches.map((batch) => (
            <option key={batch.id} value={batch.id}>
              {batch.name}
            </option>
          ))}
        </select>
      </div>

      {!data ? (
        <Loading />
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-4">
            <Stat label="students" value={data.student_count} hint={data.batch} />
            <Stat label="live postings" value={data.active_postings} hint={`${data.market_postings} from open market feed`} accent="#7285C2" />
            <div className="card-mauve flex items-center justify-center">
              <Ring value={data.avg_readiness} color={data.avg_readiness >= 60 ? "#2F9599" : "#C08010"} label="avg readiness" sublabel="top 5 matches" />
            </div>
            <div className="card-mauve">
              <div className="label">readiness spread</div>
              <div className="mt-2 grid gap-1.5">
                {[
                  ["ready", "70%+", "#2F9599"],
                  ["close", "50-69%", "#7285C2"],
                  ["developing", "30-49%", "#C08010"],
                  ["at_risk", "under 30%", "#BC1F2B"],
                ].map(([key, range, color]) => (
                  <div key={key} className="flex items-center gap-2 font-mono text-[11px]">
                    <span className="w-16">{key.replace("_", " ")}</span>
                    <Bar value={(100 * (buckets[key] || 0)) / total} color={color} track="rgba(255,255,255,0.7)" />
                    <span className="w-6 text-right">{buckets[key] || 0}</span>
                    <span className="hidden w-14 text-plum/50 lg:inline">{range}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
            <section className="card">
              <h2 className="font-display text-2xl">Biggest gaps</h2>
              <p className="mt-1 text-xs text-plum/60">Gap = share of postings requiring the skill minus share of students holding it at the typical required level. Teach these first.</p>
              <div className="mt-4 grid gap-3">
                {data.gaps.map((gap) => (
                  <GapRow key={gap.skill_id} gap={gap} />
                ))}
                {data.gaps.length === 0 && <div className="text-sm text-plum/60">No active postings to measure against.</div>}
              </div>
            </section>
            <section className="card">
              <h2 className="font-display text-2xl">Strengths</h2>
              <p className="mt-1 text-xs text-plum/60">Skills where the cohort is ahead of demand.</p>
              <div className="mt-4 grid gap-3">
                {data.strengths.map((gap) => (
                  <GapRow key={gap.skill_id} gap={gap} />
                ))}
              </div>
            </section>
          </div>
        </>
      )}
    </div>
  );
}

import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../../api";
import { Empty, ErrorNote, Loading, Ring, scoreColor, useToast } from "../../components/ui";

const COLUMNS = ["applied", "shortlisted", "interview", "offered", "rejected"];
const NEXT = { applied: "shortlisted", shortlisted: "interview", interview: "offered" };

export default function RecruiterPipeline() {
  const [postings, setPostings] = useState(null);
  const [params, setParams] = useSearchParams();
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(null);
  const [showToast, toast] = useToast();
  const postingId = params.get("posting");

  useEffect(() => {
    api
      .recruiterPostings()
      .then((data) => {
        setPostings(data);
        if (!postingId && data.length) setParams({ posting: data[0].id });
      })
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!postingId) return;
    setRows(null);
    api.postingApplications(postingId).then(setRows).catch((err) => setError(err.message));
  }, [postingId]);

  async function move(row, status) {
    try {
      await api.setStatus(row.application_id, status);
      setRows((current) => current.map((item) => (item.application_id === row.application_id ? { ...item, application_status: status } : item)));
      showToast(`${row.full_name} moved to ${status}.`);
    } catch (err) {
      showToast(err.message, "error");
    }
  }

  if (error) return <ErrorNote error={error} />;
  if (!postings) return <Loading />;

  return (
    <div className="grid gap-6">
      {toast}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="label">applied to offered, one click per step</div>
          <h1 className="font-display text-5xl">Pipeline</h1>
        </div>
        <select className="input w-72" value={postingId || ""} onChange={(event) => setParams({ posting: event.target.value })}>
          {postings.map((posting) => (
            <option key={posting.id} value={posting.id}>
              {posting.title}
            </option>
          ))}
        </select>
      </div>

      {postings.length === 0 ? (
        <Empty title="No postings" body="Create a posting first." />
      ) : !rows ? (
        <Loading />
      ) : (
        <div className="grid gap-3 overflow-x-auto md:grid-cols-5">
          {COLUMNS.map((column) => {
            const items = rows.filter((row) => row.application_status === column);
            return (
              <div key={column} className="min-w-[13rem] rounded-card bg-petal/40 p-3">
                <div className="flex items-center justify-between">
                  <div className="label">{column}</div>
                  <div className="font-mono text-xs">{items.length}</div>
                </div>
                <div className="mt-3 grid gap-2">
                  {items.map((row) => (
                    <div key={row.application_id} className="rounded-2xl bg-white/85 p-3 shadow-soft">
                      <div className="flex items-center gap-2">
                        <Ring value={row.score} size={40} stroke={5} color={scoreColor(row.score)} />
                        <div className="min-w-0">
                          <div className="truncate text-sm font-semibold">{row.full_name}</div>
                          <div className="truncate font-mono text-[10px] text-plum/60">{row.batch}</div>
                        </div>
                      </div>
                      {row.missing.length > 0 && <div className="mt-2 font-mono text-[10px] text-signal">missing {row.missing.map((item) => item.skill).join(", ")}</div>}
                      {row.email && <div className="mt-1 truncate font-mono text-[10px] text-plum/60">{row.email}</div>}
                      <div className="mt-2 flex gap-1">
                        {NEXT[column] && (
                          <button type="button" className="chip bg-plum text-cream" onClick={() => move(row, NEXT[column])}>
                            to {NEXT[column]}
                          </button>
                        )}
                        {column !== "rejected" && column !== "offered" && (
                          <button type="button" className="chip bg-signal/10 text-signal" onClick={() => move(row, "rejected")}>
                            reject
                          </button>
                        )}
                        {column === "rejected" && (
                          <button type="button" className="chip bg-white" onClick={() => move(row, "applied")}>
                            reopen
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

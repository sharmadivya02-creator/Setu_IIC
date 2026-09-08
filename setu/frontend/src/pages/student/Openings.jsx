import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../../api";
import { AiSimilarityMap, Empty, ErrorNote, Loading, Modal, Ring, ScoreBreakdown, SkillChip, scoreColor, useToast } from "../../components/ui";

const STATUS_TONE = { applied: "petal", shortlisted: "teal", interview: "amber", offered: "teal", rejected: "red" };

export default function StudentOpenings() {
  const [matches, setMatches] = useState(null);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("all");
  const [params, setParams] = useSearchParams();
  const [showToast, toast] = useToast();
  const openId = Number(params.get("open")) || null;

  useEffect(() => {
    api.studentMatches().then(setMatches).catch((err) => setError(err.message));
  }, []);

  const visible = useMemo(() => {
    if (!matches) return [];
    if (filter === "all") return matches;
    if (filter === "market") return matches.filter((match) => match.posting.source === "market");
    return matches.filter((match) => match.posting.kind === filter && match.posting.source === "internal");
  }, [matches, filter]);

  const open = matches?.find((match) => match.posting.id === openId) || null;

  async function apply(postingId) {
    try {
      const application = await api.apply(postingId);
      setMatches((current) => current.map((match) => (match.posting.id === postingId ? { ...match, application_status: application.status } : match)));
      showToast("Applied. The recruiter sees your score and what you are missing.");
    } catch (err) {
      showToast(err.message, "error");
    }
  }

  if (error) return <ErrorNote error={error} />;
  if (!matches) return <Loading />;

  return (
    <div className="grid gap-6">
      {toast}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="label">{matches.length} live openings, scored against your profile</div>
          <h1 className="font-display text-5xl">Openings</h1>
        </div>
        <div className="flex gap-1">
          {["all", "job", "internship", "market"].map((item) => (
            <button key={item} type="button" onClick={() => setFilter(item)} className={`chip ${filter === item ? "bg-plum text-cream" : "bg-petal/60"}`}>
              {item}
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-2xl border border-periwinkle/30 bg-periwinkle/10 px-4 py-2 text-xs text-periwinkle">
        <span className="font-mono font-semibold">✦ AI</span> tag on a skill chip means it was matched by an AI embedding model (not an exact skill-name match) — you don't hold that exact skill, but you hold something close enough to earn partial credit.
      </div>

      {visible.length === 0 && <Empty title="Nothing here yet" body="No openings match this filter." />}

      <div className="grid gap-4 md:grid-cols-2">
        {visible.map((match) => (
          <button key={match.posting.id} type="button" onClick={() => setParams({ open: match.posting.id })} className="card text-left transition-transform hover:-translate-y-0.5">
            <div className="flex items-start gap-4">
              <Ring value={match.score} size={72} stroke={7} color={scoreColor(match.score)} />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <div className="truncate font-semibold">{match.posting.title}</div>
                  {match.application_status && <SkillChip name={match.application_status} tone={STATUS_TONE[match.application_status]} />}
                </div>
                <div className="text-xs text-plum/60">
                  {match.posting.company} · {match.posting.location} · {match.posting.kind}
                  {match.posting.source === "market" && " · open market"}
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {match.posting.required_skills.slice(0, 5).map((req) => {
                    const missing = match.missing.some((item) => item.skill_id === req.skill_id);
                    const below = match.below_level.some((item) => item.skill_id === req.skill_id);
                    const related = (match.related || []).some((item) => item.skill_id === req.skill_id);
                    return (
                      <SkillChip
                        key={req.skill_id}
                        name={`${req.skill} L${req.min_level}`}
                        tone={missing ? "red" : below ? "amber" : related ? "periwinkle" : "teal"}
                      />
                    );
                  })}
                  {match.posting.required_skills.length > 5 && <span className="chip bg-white">+{match.posting.required_skills.length - 5}</span>}
                </div>
              </div>
            </div>
          </button>
        ))}
      </div>

      <Modal open={Boolean(open)} onClose={() => setParams({})} title={open?.posting.title || ""} wide>
        {open && (
          <div className="grid gap-5 md:grid-cols-[auto_1fr]">
            <div className="flex flex-col items-center gap-3">
              <Ring value={open.score} size={120} stroke={10} color={scoreColor(open.score)} label="match" />
              {open.posting.source === "market" ? (
                <a href={open.posting.external_url} target="_blank" rel="noreferrer" className="btn-secondary">
                  Apply on company site
                </a>
              ) : open.application_status ? (
                <SkillChip name={open.application_status} tone={STATUS_TONE[open.application_status]} />
              ) : (
                <button type="button" className="btn-primary" onClick={() => apply(open.posting.id)}>
                  Apply
                </button>
              )}
            </div>
            <div className="grid gap-4">
              <div>
                <div className="label">
                  {open.posting.company} · {open.posting.location} · {open.posting.kind}
                </div>
                <p className="mt-1 text-sm text-plum/80">{open.posting.description}</p>
              </div>
              <ScoreBreakdown match={open} />
              <AiSimilarityMap requiredSkills={open.posting.required_skills} />
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
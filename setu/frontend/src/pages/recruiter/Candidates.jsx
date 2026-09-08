import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../../api";
import { Empty, ErrorNote, Loading, Modal, Ring, ScoreBreakdown, SkillChip, scoreColor, useToast } from "../../components/ui";

const STATUS_TONE = { applied: "petal", shortlisted: "teal", interview: "amber", offered: "teal", rejected: "red" };

export default function RecruiterCandidates() {
  const { postingId } = useParams();
  const [posting, setPosting] = useState(null);
  const [candidates, setCandidates] = useState(null);
  const [open, setOpen] = useState(null);
  const [error, setError] = useState(null);
  const [showToast, toast] = useToast();

  useEffect(() => {
    Promise.all([api.recruiterPostings(), api.candidates(postingId)])
      .then(([postings, candidateData]) => {
        setPosting(postings.find((item) => item.id === Number(postingId)) || null);
        setCandidates(candidateData);
      })
      .catch((err) => setError(err.message));
  }, [postingId]);

  async function shortlist(candidate) {
    try {
      const application = await api.shortlist(postingId, candidate.student_id);
      const refreshed = await api.candidates(postingId);
      setCandidates(refreshed);
      setOpen(refreshed.find((item) => item.student_id === candidate.student_id) || null);
      showToast(`${candidate.full_name} shortlisted. Contact details are now visible.`);
      return application;
    } catch (err) {
      showToast(err.message, "error");
      return null;
    }
  }

  if (error) return <ErrorNote error={error} />;
  if (!candidates) return <Loading />;

  return (
    <div className="grid gap-6">
      {toast}
      <div>
        <Link to="/recruiter" className="font-mono text-xs text-periwinkle underline">
          back to postings
        </Link>
        <div className="mt-2 flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="label">every student scored, best first · contact hidden until shortlisted</div>
            <h1 className="font-display text-4xl">{posting?.title || "Candidates"}</h1>
          </div>
          <div className="flex flex-wrap gap-1">
            {posting?.required_skills.map((req) => (
              <SkillChip key={req.skill_id} name={`${req.skill} L${req.min_level}`} tone={req.importance === "must_have" ? "plum" : "petal"} />
            ))}
          </div>
        </div>
      </div>

      {candidates.length === 0 && <Empty title="No students in the system" body="Once students register and add skills they appear here, ranked." />}

      <div className="grid gap-3">
        {candidates.map((candidate, index) => (
          <button key={candidate.student_id} type="button" onClick={() => setOpen(candidate)} className="card flex items-center gap-4 text-left hover:-translate-y-0.5">
            <div className="w-8 font-mono text-sm text-plum/40">#{index + 1}</div>
            <Ring value={candidate.score} size={64} stroke={6} color={scoreColor(candidate.score)} />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold">{candidate.full_name}</span>
                <span className="font-mono text-[11px] text-plum/60">
                  {candidate.batch} · cgpa {candidate.cgpa.toFixed(1)} · {candidate.verified_skill_count} verified
                </span>
                {candidate.application_status && <SkillChip name={candidate.application_status} tone={STATUS_TONE[candidate.application_status]} />}
              </div>
              <div className="mt-1.5 flex flex-wrap gap-1">
                {candidate.matched.slice(0, 4).map((row) => (
                  <SkillChip key={row.skill_id} name={row.skill} tone="teal" />
                ))}
                {candidate.below_level.slice(0, 2).map((row) => (
                  <SkillChip key={row.skill_id} name={`${row.skill} L${row.level}/${row.needed}`} tone="amber" />
                ))}
                {(candidate.related || []).slice(0, 2).map((row) => (
                  <SkillChip key={row.skill_id} name={`${row.skill} via ${row.via_skill}`} tone="periwinkle" />
                ))}
                {candidate.missing.slice(0, 3).map((row) => (
                  <SkillChip key={row.skill_id} name={`missing ${row.skill}`} tone="red" />
                ))}
              </div>
            </div>
            {!candidate.application_status && (
              <span
                role="button"
                className="btn-secondary hidden md:inline-flex"
                onClick={(event) => {
                  event.stopPropagation();
                  shortlist(candidate);
                }}
              >
                Shortlist
              </span>
            )}
          </button>
        ))}
      </div>

      <Modal open={Boolean(open)} onClose={() => setOpen(null)} title={open?.full_name || ""} wide>
        {open && (
          <div className="grid gap-5 md:grid-cols-[auto_1fr]">
            <div className="flex flex-col items-center gap-3">
              <Ring value={open.score} size={120} stroke={10} color={scoreColor(open.score)} label="match" />
              {open.application_status ? (
                <SkillChip name={open.application_status} tone={STATUS_TONE[open.application_status]} />
              ) : (
                <button type="button" className="btn-primary" onClick={() => shortlist(open)}>
                  Shortlist
                </button>
              )}
              <div className="text-center font-mono text-[11px] text-plum/60">
                {open.batch}
                <br />
                {open.roll_number} · cgpa {open.cgpa.toFixed(2)}
              </div>
              {open.email ? (
                <div className="rounded-2xl bg-petal/60 p-3 text-center font-mono text-[11px]">
                  {open.email}
                  {open.phone && <div>{open.phone}</div>}
                  {open.github_url && (
                    <a href={open.github_url} target="_blank" rel="noreferrer" className="block text-periwinkle underline">
                      github
                    </a>
                  )}
                  {open.resume_url && (
                    <a href={open.resume_url} target="_blank" rel="noreferrer" className="block text-periwinkle underline">
                      resume
                    </a>
                  )}
                </div>
              ) : (
                <div className="text-center font-mono text-[11px] text-plum/50">contact visible after shortlist</div>
              )}
            </div>
            <ScoreBreakdown match={open} />
          </div>
        )}
      </Modal>
    </div>
  );
}

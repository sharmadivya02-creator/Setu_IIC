import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api";
import { Bar, Empty, ErrorNote, Loading, Ring, SkillChip, Stat, scoreColor } from "../../components/ui";

export default function StudentDashboard() {
  const [profile, setProfile] = useState(null);
  const [matches, setMatches] = useState(null);
  const [gaps, setGaps] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([api.studentProfile(), api.studentMatches(), api.studentGaps()])
      .then(([profileData, matchData, gapData]) => {
        setProfile(profileData);
        setMatches(matchData);
        setGaps(gapData);
      })
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <ErrorNote error={error} />;
  if (!profile || !matches || !gaps) return <Loading />;

  const topFive = matches.slice(0, 5);
  const readiness = topFive.length ? topFive.reduce((sum, match) => sum + match.score, 0) / topFive.length : 0;
  const verified = profile.skills.filter((skill) => skill.verified).length;
  const verifiedPct = profile.skills.length ? (100 * verified) / profile.skills.length : 0;

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="label">{profile.batch} · {profile.roll_number}</div>
          <h1 className="font-display text-5xl">Hello, {profile.full_name.split(" ")[0]}</h1>
        </div>
        <Link to="/student/skills" className="btn-primary">
          Update my skills
        </Link>
      </div>

      {profile.skills.length === 0 ? (
        <Empty title="Your profile is empty" body="Add your skills with a level from 1 to 5 and every opening gets scored for you instantly." />
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          <div className="card flex items-center justify-around">
            <Ring value={readiness} color={scoreColor(readiness)} label="Readiness" sublabel="avg of top 5 matches" />
            <Ring value={matches[0]?.score || 0} color="#7285C2" label="Best match" sublabel={matches[0]?.posting.title.slice(0, 22) || "none"} />
          </div>
          <div className="card flex items-center justify-around">
            <Ring value={verifiedPct} color="#C08010" label="Verified" sublabel={`${verified} of ${profile.skills.length} skills`} />
          </div>
          <Stat label="live openings scored" value={matches.length} hint={`${matches.filter((match) => match.posting.source === "market").length} from the open market feed`} accent="#95709F" />
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-[1.2fr_1fr]">
        <section className="card">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-2xl">Top matches</h2>
            <Link to="/student/openings" className="font-mono text-xs text-periwinkle underline">
              see all
            </Link>
          </div>
          <div className="mt-4 grid gap-3">
            {topFive.map((match) => (
              <Link key={match.posting.id} to={`/student/openings?open=${match.posting.id}`} className="flex items-center gap-4 rounded-2xl bg-petal/40 p-3 hover:bg-petal/70">
                <div className="w-14 text-center font-mono text-lg" style={{ color: scoreColor(match.score) }}>
                  {Math.round(match.score)}%
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate font-semibold">{match.posting.title}</div>
                  <div className="truncate text-xs text-plum/60">
                    {match.posting.company} · {match.posting.location} · {match.posting.kind}
                  </div>
                  <div className="mt-1.5">
                    <Bar value={match.score} color={scoreColor(match.score)} />
                  </div>
                </div>
                <div className="hidden text-right font-mono text-[11px] text-plum/60 sm:block">
                  {match.missing.length ? `${match.missing.length} missing` : "all skills present"}
                </div>
              </Link>
            ))}
          </div>
        </section>

        <section className="card">
          <h2 className="font-display text-2xl">Learn next</h2>
          <p className="mt-1 text-xs text-plum/60">Ranked by how much each skill would lift your average match score across every live opening.</p>
          <div className="mt-4 grid gap-3">
            {gaps.map((gap) => (
              <div key={gap.skill_id} className="rounded-2xl bg-white/80 p-3">
                <div className="flex items-center justify-between">
                  <SkillChip name={gap.skill} tone="plum" />
                  <span className="font-mono text-xs text-teal">+{gap.avg_score_lift} avg</span>
                </div>
                <div className="mt-2 flex items-center justify-between font-mono text-[11px] text-plum/60">
                  <span>target level {gap.target_level}</span>
                  <span>required by {gap.demand_pct}% of openings</span>
                </div>
              </div>
            ))}
            {gaps.length === 0 && <div className="text-sm text-plum/60">You already meet every requirement in the current openings.</div>}
          </div>
        </section>
      </div>
    </div>
  );
}

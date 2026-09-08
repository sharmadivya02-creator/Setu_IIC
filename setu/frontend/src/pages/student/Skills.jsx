import { useEffect, useMemo, useState } from "react";
import { api } from "../../api";
import { ErrorNote, LEVEL_NAMES, LevelDots, Loading, SkillChip, useToast } from "../../components/ui";

export default function StudentSkills() {
  const [taxonomy, setTaxonomy] = useState(null);
  const [profile, setProfile] = useState(null);
  const [levels, setLevels] = useState({});
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("all");
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [showToast, toast] = useToast();

  useEffect(() => {
    Promise.all([api.skills(), api.studentProfile()])
      .then(([skills, profileData]) => {
        setTaxonomy(skills);
        setProfile(profileData);
        setLevels(Object.fromEntries(profileData.skills.map((skill) => [skill.skill_id, skill.level])));
      })
      .catch((err) => setError(err.message));
  }, []);

  const categories = useMemo(() => (taxonomy ? [...new Set(taxonomy.map((skill) => skill.category))] : []), [taxonomy]);
  const visible = useMemo(() => {
    if (!taxonomy) return [];
    const needle = query.trim().toLowerCase();
    return taxonomy.filter((skill) => (category === "all" || skill.category === category) && (!needle || skill.name.toLowerCase().includes(needle)));
  }, [taxonomy, query, category]);

  const verifiedIds = useMemo(() => new Set((profile?.skills || []).filter((skill) => skill.verified).map((skill) => skill.skill_id)), [profile]);

  function setLevel(skillId, level) {
    setLevels((current) => {
      const next = { ...current };
      if (level === 0) delete next[skillId];
      else next[skillId] = level;
      return next;
    });
  }

  async function save() {
    setSaving(true);
    try {
      const updated = await api.saveStudentSkills(Object.entries(levels).map(([skill_id, level]) => ({ skill_id: Number(skill_id), level })));
      setProfile(updated);
      showToast("Skills saved. Your matches are recalculated.");
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      setSaving(false);
    }
  }

  if (error) return <ErrorNote error={error} />;
  if (!taxonomy || !profile) return <Loading />;

  const selected = taxonomy.filter((skill) => levels[skill.id]);

  return (
    <div className="grid gap-6">
      {toast}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="label">structured profile, no free text</div>
          <h1 className="font-display text-5xl">My skills</h1>
        </div>
        <button type="button" className="btn-primary" onClick={save} disabled={saving}>
          {saving ? "saving" : `Save ${selected.length} skills`}
        </button>
      </div>

      <section className="card">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-display text-2xl">Selected</h2>
          <div className="font-mono text-xs text-plum/60">changing a verified skill's level removes its verification</div>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {selected.length === 0 && <div className="text-sm text-plum/60">Nothing yet. Pick skills below.</div>}
          {selected.map((skill) => (
            <SkillChip key={skill.id} name={skill.name} level={levels[skill.id]} verified={verifiedIds.has(skill.id) && levels[skill.id] === profile.skills.find((item) => item.skill_id === skill.id)?.level} tone="plum" onRemove={() => setLevel(skill.id, 0)} />
          ))}
        </div>
      </section>

      <div className="card-mauve flex flex-wrap items-center gap-4 text-xs text-plum/70">
        <span className="label">levels</span>
        {[1, 2, 3, 4, 5].map((value) => (
          <span key={value} className="inline-flex items-center gap-1">
            <LevelDots level={value} /> {LEVEL_NAMES[value]}
          </span>
        ))}
      </div>

      <section className="card">
        <div className="grid gap-3 md:grid-cols-[1fr_auto]">
          <input className="input" placeholder="search the taxonomy" value={query} onChange={(event) => setQuery(event.target.value)} />
          <div className="flex flex-wrap gap-1">
            {["all", ...categories].map((item) => (
              <button key={item} type="button" onClick={() => setCategory(item)} className={`chip ${category === item ? "bg-plum text-cream" : "bg-petal/60"}`}>
                {item}
              </button>
            ))}
          </div>
        </div>
        <div className="mt-4 grid gap-2 md:grid-cols-2">
          {visible.map((skill) => {
            const level = levels[skill.id] || 0;
            return (
              <div key={skill.id} className={`flex items-center justify-between rounded-2xl px-3 py-2 ${level ? "bg-petal/60" : "bg-white/70"}`}>
                <div>
                  <div className="text-sm font-medium">{skill.name}</div>
                  <div className="font-mono text-[10px] text-violet">{skill.category}{level ? ` · ${LEVEL_NAMES[level]}` : ""}</div>
                </div>
                <div className="flex items-center gap-1">
                  {[1, 2, 3, 4, 5].map((value) => (
                    <button
                      key={value}
                      type="button"
                      aria-label={`${skill.name} level ${value}`}
                      onClick={() => setLevel(skill.id, level === value ? 0 : value)}
                      className={`h-7 w-7 rounded-full font-mono text-xs ${value <= level ? "bg-plum text-cream" : "bg-plum/10 text-plum/60 hover:bg-plum/20"}`}
                    >
                      {value}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

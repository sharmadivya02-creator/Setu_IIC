import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../api";
import { Empty, ErrorNote, Loading, Modal, SkillChip, useToast } from "../../components/ui";

const EMPTY_FORM = { title: "", kind: "internship", location: "", description: "", active: true, required_skills: [] };

function PostingForm({ initial, taxonomy, onSubmit, busy }) {
  const [form, setForm] = useState(initial);
  const [query, setQuery] = useState("");

  const suggestions = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return [];
    const chosen = new Set(form.required_skills.map((req) => req.skill_id));
    return taxonomy.filter((skill) => !chosen.has(skill.id) && skill.name.toLowerCase().includes(needle)).slice(0, 8);
  }, [query, taxonomy, form.required_skills]);

  function addSkill(skill) {
    setForm({ ...form, required_skills: [...form.required_skills, { skill_id: skill.id, name: skill.name, min_level: 3, importance: "must_have" }] });
    setQuery("");
  }

  function updateReq(index, patch) {
    setForm({ ...form, required_skills: form.required_skills.map((req, i) => (i === index ? { ...req, ...patch } : req)) });
  }

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(form);
      }}
      className="grid gap-3"
    >
      <input className="input" placeholder="title" required minLength={3} value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} />
      <div className="grid grid-cols-2 gap-3">
        <select className="input" value={form.kind} onChange={(event) => setForm({ ...form, kind: event.target.value })}>
          <option value="internship">Internship</option>
          <option value="job">Job</option>
        </select>
        <input className="input" placeholder="location" required value={form.location} onChange={(event) => setForm({ ...form, location: event.target.value })} />
      </div>
      <textarea className="input min-h-24" placeholder="description (10+ characters)" required minLength={10} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={form.active} onChange={(event) => setForm({ ...form, active: event.target.checked })} /> active (visible to students)
      </label>

      <div className="rounded-2xl bg-petal/50 p-3">
        <div className="label">required skills with minimum level</div>
        <div className="mt-2 grid gap-2">
          {form.required_skills.map((req, index) => (
            <div key={req.skill_id} className="flex flex-wrap items-center gap-2 rounded-xl bg-white/80 px-3 py-2 text-sm">
              <span className="flex-1 font-medium">{req.name}</span>
              <select className="input w-24 py-1" value={req.min_level} onChange={(event) => updateReq(index, { min_level: Number(event.target.value) })}>
                {[1, 2, 3, 4, 5].map((level) => (
                  <option key={level} value={level}>
                    L{level}+
                  </option>
                ))}
              </select>
              <select className="input w-32 py-1" value={req.importance} onChange={(event) => updateReq(index, { importance: event.target.value })}>
                <option value="must_have">must have</option>
                <option value="nice_to_have">nice to have</option>
              </select>
              <button type="button" className="font-mono text-xs text-signal" onClick={() => setForm({ ...form, required_skills: form.required_skills.filter((_, i) => i !== index) })}>
                remove
              </button>
            </div>
          ))}
        </div>
        <input className="input mt-2" placeholder="type to add a skill from the taxonomy" value={query} onChange={(event) => setQuery(event.target.value)} />
        {suggestions.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {suggestions.map((skill) => (
              <SkillChip key={skill.id} name={skill.name} tone="plum" onClick={() => addSkill(skill)} />
            ))}
          </div>
        )}
      </div>
      <button className="btn-primary" disabled={busy || form.required_skills.length === 0}>
        {busy ? "saving" : "Save posting"}
      </button>
    </form>
  );
}

export default function RecruiterPostings() {
  const [postings, setPostings] = useState(null);
  const [taxonomy, setTaxonomy] = useState([]);
  const [editing, setEditing] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [showToast, toast] = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([api.recruiterPostings(), api.skills()])
      .then(([postingData, skills]) => {
        setPostings(postingData);
        setTaxonomy(skills);
      })
      .catch((err) => setError(err.message));
  }, []);

  async function save(form) {
    setBusy(true);
    const body = { ...form, required_skills: form.required_skills.map(({ skill_id, min_level, importance }) => ({ skill_id, min_level, importance })) };
    try {
      if (editing.id) {
        const updated = await api.updatePosting(editing.id, body);
        setPostings((current) => current.map((posting) => (posting.id === updated.id ? updated : posting)));
      } else {
        const created = await api.createPosting(body);
        setPostings((current) => [created, ...current]);
      }
      setEditing(null);
      showToast("Posting saved. Candidates are ranked immediately.");
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      setBusy(false);
    }
  }

  if (error) return <ErrorNote error={error} />;
  if (!postings) return <Loading />;

  return (
    <div className="grid gap-6">
      {toast}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="label">{postings.length} postings under your company</div>
          <h1 className="font-display text-5xl">Postings</h1>
        </div>
        <button type="button" className="btn-primary" onClick={() => setEditing({ ...EMPTY_FORM })}>
          New posting
        </button>
      </div>

      {postings.length === 0 && <Empty title="No postings yet" body="Create one with required skills and minimum levels. Ranked candidates appear instantly." />}

      <div className="grid gap-4 md:grid-cols-2">
        {postings.map((posting) => (
          <div key={posting.id} className={`card ${posting.active ? "" : "opacity-60"}`}>
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="font-semibold">{posting.title}</div>
                <div className="text-xs text-plum/60">
                  {posting.location} · {posting.kind} · {posting.active ? "active" : "closed"}
                </div>
              </div>
              <button
                type="button"
                className="font-mono text-xs text-periwinkle underline"
                onClick={() =>
                  setEditing({
                    ...posting,
                    required_skills: posting.required_skills.map((req) => ({ skill_id: req.skill_id, name: req.skill, min_level: req.min_level, importance: req.importance })),
                  })
                }
              >
                edit
              </button>
            </div>
            <div className="mt-3 flex flex-wrap gap-1">
              {posting.required_skills.map((req) => (
                <SkillChip key={req.skill_id} name={`${req.skill} L${req.min_level}`} tone={req.importance === "must_have" ? "plum" : "petal"} />
              ))}
            </div>
            <div className="mt-4 flex gap-2">
              <button type="button" className="btn-primary" onClick={() => navigate(`/recruiter/postings/${posting.id}`)}>
                Ranked candidates
              </button>
              <button type="button" className="btn-secondary" onClick={() => navigate(`/recruiter/pipeline?posting=${posting.id}`)}>
                Pipeline
              </button>
            </div>
          </div>
        ))}
      </div>

      <Modal open={Boolean(editing)} onClose={() => setEditing(null)} title={editing?.id ? "Edit posting" : "New posting"} wide>
        {editing && <PostingForm initial={editing} taxonomy={taxonomy} onSubmit={save} busy={busy} />}
      </Modal>
    </div>
  );
}

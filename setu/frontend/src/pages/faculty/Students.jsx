import { useEffect, useMemo, useState } from "react";
import { api } from "../../api";
import { Empty, ErrorNote, Loading, Modal, Ring, SkillChip, scoreColor, useToast } from "../../components/ui";

function StudentDetail({ studentId, batches, onChanged }) {
  const [profile, setProfile] = useState(null);
  const [edit, setEdit] = useState(null);
  const [showToast, toast] = useToast();

  useEffect(() => {
    api.facultyStudent(studentId).then((data) => {
      setProfile(data);
      setEdit({ full_name: data.full_name, roll_number: data.roll_number, batch_id: String(data.batch_id), cgpa: data.cgpa });
    });
  }, [studentId]);

  async function toggleVerify(skill) {
    try {
      const updated = await api.verifySkill(studentId, skill.skill_id, !skill.verified);
      setProfile(updated);
      onChanged();
    } catch (err) {
      showToast(err.message, "error");
    }
  }

  async function saveEdit(event) {
    event.preventDefault();
    try {
      const updated = await api.editStudent(studentId, { ...edit, batch_id: Number(edit.batch_id), cgpa: Number(edit.cgpa) });
      setProfile(updated);
      onChanged();
      showToast("Student updated.");
    } catch (err) {
      showToast(err.message, "error");
    }
  }

  if (!profile || !edit) return <Loading />;

  return (
    <div className="grid gap-5">
      {toast}
      <form onSubmit={saveEdit} className="grid gap-3 md:grid-cols-[1fr_1fr_1fr_auto_auto]">
        <input className="input" value={edit.full_name} onChange={(event) => setEdit({ ...edit, full_name: event.target.value })} aria-label="full name" />
        <input className="input" value={edit.roll_number} onChange={(event) => setEdit({ ...edit, roll_number: event.target.value })} aria-label="roll number" />
        <select className="input" value={edit.batch_id} onChange={(event) => setEdit({ ...edit, batch_id: event.target.value })} aria-label="batch">
          {batches.map((batch) => (
            <option key={batch.id} value={batch.id}>
              {batch.name}
            </option>
          ))}
        </select>
        <input className="input w-24" type="number" step="0.01" min="0" max="10" value={edit.cgpa} onChange={(event) => setEdit({ ...edit, cgpa: event.target.value })} aria-label="cgpa" />
        <button className="btn-primary">Save</button>
      </form>
      <div className="font-mono text-xs text-plum/60">{profile.email}{profile.github_url ? ` · ${profile.github_url}` : ""}</div>
      <div>
        <div className="label">click a skill to verify or unverify it</div>
        <div className="mt-2 flex flex-wrap gap-2">
          {profile.skills.map((skill) => (
            <SkillChip key={skill.skill_id} name={skill.name} level={skill.level} verified={skill.verified} tone={skill.verified ? "teal" : "petal"} onClick={() => toggleVerify(skill)} />
          ))}
          {profile.skills.length === 0 && <div className="text-sm text-plum/60">This student has not added skills yet.</div>}
        </div>
      </div>
    </div>
  );
}

export default function FacultyStudents() {
  const [batches, setBatches] = useState([]);
  const [batchId, setBatchId] = useState("");
  const [rows, setRows] = useState(null);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(null);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ full_name: "", email: "", roll_number: "", batch_id: "", cgpa: "", password: "setu1234" });
  const [error, setError] = useState(null);
  const [showToast, toast] = useToast();

  function load() {
    api.facultyStudents(batchId || null).then(setRows).catch((err) => setError(err.message));
  }

  useEffect(() => {
    api.batches().then(setBatches).catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    setRows(null);
    load();
  }, [batchId]);

  const visible = useMemo(() => {
    if (!rows) return [];
    const needle = query.trim().toLowerCase();
    return needle ? rows.filter((row) => row.full_name.toLowerCase().includes(needle) || row.roll_number.toLowerCase().includes(needle)) : rows;
  }, [rows, query]);

  async function addStudent(event) {
    event.preventDefault();
    try {
      await api.addStudent({ ...form, batch_id: Number(form.batch_id), cgpa: Number(form.cgpa || 0) });
      setAdding(false);
      setForm({ full_name: "", email: "", roll_number: "", batch_id: "", cgpa: "", password: "setu1234" });
      showToast("Student added. They can log in with the password you set.");
      load();
    } catch (err) {
      showToast(err.message, "error");
    }
  }

  if (error) return <ErrorNote error={error} />;

  return (
    <div className="grid gap-6">
      {toast}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="label">manage, verify, endorse</div>
          <h1 className="font-display text-5xl">Students</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <input className="input w-48" placeholder="search name or roll" value={query} onChange={(event) => setQuery(event.target.value)} />
          <select className="input w-44" value={batchId} onChange={(event) => setBatchId(event.target.value)}>
            <option value="">All batches</option>
            {batches.map((batch) => (
              <option key={batch.id} value={batch.id}>
                {batch.name}
              </option>
            ))}
          </select>
          <button type="button" className="btn-primary" onClick={() => setAdding(true)}>
            Add student
          </button>
        </div>
      </div>

      {!rows ? (
        <Loading />
      ) : visible.length === 0 ? (
        <Empty title="No students" body="Add one, or widen the filter." />
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left font-mono text-[11px] uppercase tracking-wider text-violet">
                <th className="px-4 py-3">student</th>
                <th className="px-4 py-3">batch</th>
                <th className="px-4 py-3">cgpa</th>
                <th className="px-4 py-3">skills</th>
                <th className="px-4 py-3">verified</th>
                <th className="px-4 py-3">readiness</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((row) => (
                <tr key={row.id} className="cursor-pointer border-t border-petal/60 hover:bg-petal/30" onClick={() => setSelected(row)}>
                  <td className="px-4 py-3">
                    <div className="font-semibold">{row.full_name}</div>
                    <div className="font-mono text-[11px] text-plum/60">{row.roll_number}</div>
                  </td>
                  <td className="px-4 py-3">{row.batch}</td>
                  <td className="px-4 py-3 font-mono">{row.cgpa.toFixed(2)}</td>
                  <td className="px-4 py-3 font-mono">{row.skill_count}</td>
                  <td className="px-4 py-3 font-mono">{row.verified_count}</td>
                  <td className="px-4 py-3">
                    <Ring value={row.readiness} size={44} stroke={5} color={scoreColor(row.readiness)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={Boolean(selected)} onClose={() => setSelected(null)} title={selected?.full_name || ""} wide>
        {selected && <StudentDetail studentId={selected.id} batches={batches} onChanged={load} />}
      </Modal>

      <Modal open={adding} onClose={() => setAdding(false)} title="Add a student">
        <form onSubmit={addStudent} className="grid gap-3">
          <input className="input" placeholder="full name" required value={form.full_name} onChange={(event) => setForm({ ...form, full_name: event.target.value })} />
          <input className="input" placeholder="email" type="email" required value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
          <div className="grid grid-cols-2 gap-3">
            <input className="input" placeholder="roll number" required value={form.roll_number} onChange={(event) => setForm({ ...form, roll_number: event.target.value })} />
            <input className="input" placeholder="cgpa" type="number" step="0.01" min="0" max="10" value={form.cgpa} onChange={(event) => setForm({ ...form, cgpa: event.target.value })} />
          </div>
          <select className="input" required value={form.batch_id} onChange={(event) => setForm({ ...form, batch_id: event.target.value })}>
            <option value="">Choose a batch</option>
            {batches.map((batch) => (
              <option key={batch.id} value={batch.id}>
                {batch.name}
              </option>
            ))}
          </select>
          <input className="input" placeholder="initial password" required minLength={6} value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} />
          <button className="btn-primary">Create student account</button>
        </form>
      </Modal>
    </div>
  );
}

import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { homeFor, useAuth } from "../auth";
import { ErrorNote } from "../components/ui";

function AuthFrame({ title, subtitle, children }) {
  return (
    <div className="grid min-h-screen bg-cream md:grid-cols-[1fr_1.1fr]">
      <div className="relative hidden items-end overflow-hidden bg-periwinkle p-10 text-cream md:flex">
        <div className="absolute -right-20 -top-20 h-80 w-80 rounded-full bg-violet/50 blur-3xl" />
        <img src="/mascot.webp" alt="" className="absolute right-0 top-10 h-[70vh] w-auto drop-shadow-2xl" />
        <div className="relative">
          <Link to="/" className="font-display text-6xl">
            Setu
          </Link>
          <p className="mt-2 max-w-xs text-cream/85">Skill mapping and placement, with the reason behind every number.</p>
        </div>
      </div>
      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-md">
          <Link to="/" className="font-display text-4xl md:hidden">
            Setu
          </Link>
          <h1 className="mt-4 font-display text-4xl">{title}</h1>
          <p className="mt-1 text-sm text-plum/70">{subtitle}</p>
          <div className="mt-6">{children}</div>
        </div>
      </div>
    </div>
  );
}

const DEMO = [
  ["student@setu.demo", "Student"],
  ["faculty@setu.demo", "Faculty"],
  ["recruiter@setu.demo", "Recruiter"],
];

export function Login() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function submit(event, presetEmail) {
    event?.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const payload = await api.login(presetEmail || email, presetEmail ? "setu1234" : password);
      signIn(payload);
      navigate(homeFor(payload.user.role));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthFrame title="Welcome back" subtitle="Sign in to your space.">
      <form onSubmit={submit} className="grid gap-3">
        <label className="grid gap-1">
          <span className="label">email</span>
          <input className="input" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoComplete="email" />
        </label>
        <label className="grid gap-1">
          <span className="label">password</span>
          <input className="input" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required autoComplete="current-password" />
        </label>
        <ErrorNote error={error} />
        <button className="btn-primary mt-2" disabled={busy}>
          {busy ? "signing in" : "Sign in"}
        </button>
      </form>
      <div className="mt-6">
        <div className="label">demo accounts, password setu1234</div>
        <div className="mt-2 flex flex-wrap gap-2">
          {DEMO.map(([demoEmail, role]) => (
            <button key={demoEmail} type="button" className="btn-secondary" disabled={busy} onClick={(event) => submit(event, demoEmail)}>
              {role}
            </button>
          ))}
        </div>
      </div>
      <p className="mt-6 text-sm text-plum/70">
        New here?{" "}
        <Link to="/register" className="font-semibold text-periwinkle underline">
          Create an account
        </Link>
      </p>
    </AuthFrame>
  );
}

export function Register() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [batches, setBatches] = useState([]);
  const [form, setForm] = useState({ role: "student", full_name: "", email: "", password: "", batch_id: "", roll_number: "", company_name: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.batches().then(setBatches).catch(() => setBatches([]));
  }, []);

  const update = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }));

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const body = { ...form, batch_id: form.batch_id ? Number(form.batch_id) : null };
      const payload = await api.register(body);
      signIn(payload);
      navigate(homeFor(payload.user.role));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthFrame title="Create your account" subtitle="Pick a role. Permissions apply the moment you log in.">
      <form onSubmit={submit} className="grid gap-3">
        <label className="grid gap-1">
          <span className="label">I am a</span>
          <select className="input" value={form.role} onChange={update("role")}>
            <option value="student">Student</option>
            <option value="faculty">Faculty / college admin</option>
            <option value="recruiter">Recruiter / company</option>
          </select>
        </label>
        <label className="grid gap-1">
          <span className="label">full name</span>
          <input className="input" value={form.full_name} onChange={update("full_name")} required minLength={2} />
        </label>
        <label className="grid gap-1">
          <span className="label">email</span>
          <input className="input" type="email" value={form.email} onChange={update("email")} required />
        </label>
        <label className="grid gap-1">
          <span className="label">password (6+ characters)</span>
          <input className="input" type="password" value={form.password} onChange={update("password")} required minLength={6} />
        </label>
        {form.role === "student" && (
          <>
            <label className="grid gap-1">
              <span className="label">batch</span>
              <select className="input" value={form.batch_id} onChange={update("batch_id")} required>
                <option value="">Choose a batch</option>
                {batches.map((batch) => (
                  <option key={batch.id} value={batch.id}>
                    {batch.college} · {batch.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-1">
              <span className="label">roll number</span>
              <input className="input" value={form.roll_number} onChange={update("roll_number")} required />
            </label>
          </>
        )}
        {form.role === "recruiter" && (
          <label className="grid gap-1">
            <span className="label">company name</span>
            <input className="input" value={form.company_name} onChange={update("company_name")} required />
          </label>
        )}
        <ErrorNote error={error} />
        <button className="btn-primary mt-2" disabled={busy}>
          {busy ? "creating" : "Create account"}
        </button>
      </form>
      <p className="mt-6 text-sm text-plum/70">
        Already have one?{" "}
        <Link to="/login" className="font-semibold text-periwinkle underline">
          Sign in
        </Link>
      </p>
    </AuthFrame>
  );
}

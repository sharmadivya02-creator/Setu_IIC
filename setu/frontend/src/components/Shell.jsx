import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

const NAV = {
  student: [
    { to: "/student", label: "Dashboard", end: true },
    { to: "/student/skills", label: "My skills" },
    { to: "/student/openings", label: "Openings" },
    { to: "/student/applications", label: "Applications" },
  ],
  faculty: [
    { to: "/faculty", label: "Analytics", end: true },
    { to: "/faculty/students", label: "Students" },
    { to: "/faculty/market", label: "Market feed" },
  ],
  recruiter: [
    { to: "/recruiter", label: "Postings", end: true },
    { to: "/recruiter/pipeline", label: "Pipeline" },
  ],
};

const ROLE_TITLE = { student: "Student", faculty: "Placement Coordinator", recruiter: "Recruiter" };

export default function Shell() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const links = NAV[user.role];

  return (
    <div className="flex min-h-screen bg-cream">
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col justify-between border-r border-petal bg-petal/40 p-6 md:flex">
        <div>
          <div className="flex items-center gap-3">
            <img src="/mascot.webp" alt="" className="h-12 w-auto" />
            <div>
              <div className="font-display text-3xl leading-none text-plum">Setu</div>
              <div className="label">{ROLE_TITLE[user.role]} space</div>
            </div>
          </div>
          <nav className="mt-10 grid gap-1">
            {links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.end}
                className={({ isActive }) =>
                  `rounded-2xl px-4 py-2.5 text-sm font-medium transition-colors ${isActive ? "bg-white text-plum shadow-soft" : "text-plum/70 hover:bg-white/60"}`
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
        </div>
        <div className="card-mauve">
          <div className="text-sm font-semibold">{user.full_name}</div>
          <div className="truncate font-mono text-[11px] text-plum/60">{user.email}</div>
          <button
            type="button"
            className="btn-secondary mt-3 w-full"
            onClick={() => {
              signOut();
              navigate("/");
            }}
          >
            Log out
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-petal px-4 py-3 md:hidden">
          <div className="font-display text-2xl">Setu</div>
          <nav className="flex gap-2 overflow-x-auto">
            {links.map((link) => (
              <NavLink key={link.to} to={link.to} end={link.end} className={({ isActive }) => `chip ${isActive ? "bg-plum text-cream" : "bg-white"}`}>
                {link.label}
              </NavLink>
            ))}
          </nav>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 p-4 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

import { useEffect, useState } from "react";

export function Ring({ value, size = 96, stroke = 9, color = "#2F9599", label, sublabel }) {
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(100, value || 0));
  const offset = circumference * (1 - clamped / 100);
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={`${Math.round(clamped)} percent`}>
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#EBD2DA" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: "stroke-dashoffset 700ms cubic-bezier(.2,.8,.2,1)" }}
        />
        <text x="50%" y="50%" dominantBaseline="central" textAnchor="middle" className="fill-plum font-mono" fontSize={size * 0.22} fontWeight="500">
          {Math.round(clamped)}%
        </text>
      </svg>
      {label && <div className="text-sm font-semibold">{label}</div>}
      {sublabel && <div className="label">{sublabel}</div>}
    </div>
  );
}

export function scoreColor(score) {
  if (score >= 70) return "#2F9599";
  if (score >= 45) return "#C08010";
  return "#BC1F2B";
}

export function LevelDots({ level, max = 5 }) {
  return (
    <span className="inline-flex gap-0.5" aria-label={`level ${level} of ${max}`}>
      {Array.from({ length: max }, (_, index) => (
        <span key={index} className={`h-1.5 w-1.5 rounded-full ${index < level ? "bg-plum" : "bg-plum/15"}`} />
      ))}
    </span>
  );
}

export const LEVEL_NAMES = ["", "Aware", "Beginner", "Working", "Proficient", "Expert"];

export function SkillChip({ name, level, verified, tone = "petal", onClick }) {
  const tones = {
    petal: "bg-petal text-plum",
    teal: "bg-teal/15 text-teal",
    amber: "bg-amber/15 text-amber",
    red: "bg-signal/10 text-signal",
    plum: "bg-plum text-cream",
    periwinkle: "bg-periwinkle/15 text-periwinkle",
  };
  const Tag = onClick ? "button" : "span";
  return (
    <Tag type={onClick ? "button" : undefined} onClick={onClick} className={`chip ${tones[tone]} ${onClick ? "hover:ring-2 hover:ring-violet/40" : ""}`}>
      {name}
      {level ? <LevelDots level={level} /> : null}
      {verified ? <span title="verified by faculty" className="ml-0.5 font-mono text-[10px]">v</span> : null}
    </Tag>
  );
}

export function Bar({ value, color = "#7285C2", track = "#EBD2DA" }) {
  return (
    <div className="h-2 w-full overflow-hidden rounded-full" style={{ background: track }}>
      <div className="h-full rounded-full transition-[width] duration-700" style={{ width: `${Math.max(0, Math.min(100, value))}%`, background: color }} />
    </div>
  );
}

export function Stat({ label, value, hint, accent }) {
  return (
    <div className="card-mauve">
      <div className="label">{label}</div>
      <div className="mt-1 font-display text-4xl" style={{ color: accent || "#2E2136" }}>
        {value}
      </div>
      {hint && <div className="mt-1 text-xs text-plum/60">{hint}</div>}
    </div>
  );
}

export function Empty({ title, body }) {
  return (
    <div className="card flex flex-col items-center py-10 text-center">
      <img src="/mascot.webp" alt="" className="mb-3 h-28 w-auto opacity-90" loading="lazy" />
      <div className="font-display text-2xl">{title}</div>
      {body && <div className="mt-1 max-w-sm text-sm text-plum/70">{body}</div>}
    </div>
  );
}

export function Toast({ message, kind = "ok", onDone }) {
  useEffect(() => {
    if (!message) return undefined;
    const timer = setTimeout(onDone, 3200);
    return () => clearTimeout(timer);
  }, [message, onDone]);
  if (!message) return null;
  return (
    <div className={`fixed bottom-6 right-6 z-50 rounded-2xl px-4 py-3 text-sm shadow-soft ${kind === "error" ? "bg-signal text-white" : "bg-plum text-cream"}`} role="status">
      {message}
    </div>
  );
}

export function useToast() {
  const [toast, setToast] = useState(null);
  const show = (message, kind = "ok") => setToast({ message, kind });
  const element = <Toast message={toast?.message} kind={toast?.kind} onDone={() => setToast(null)} />;
  return [show, element];
}

const DOT_TONE = { matched: "bg-teal", below: "bg-amber", related: "bg-periwinkle", missing: "bg-signal" };

export function ScoreBreakdown({ match }) {
  const related = match.related || [];
  const rows = [
    ...match.matched.map((row) => ({ ...row, state: "matched" })),
    ...match.below_level.map((row) => ({ ...row, state: "below" })),
    ...related.map((row) => ({ ...row, state: "related" })),
    ...match.missing.map((row) => ({ ...row, state: "missing" })),
  ];
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="label">why this score</div>
        <div className="flex gap-3">
          {match.verified_bonus > 0 && <div className="font-mono text-xs text-teal">+{match.verified_bonus}% verified bonus</div>}
          {match.related_credit > 0 && <div className="font-mono text-xs text-periwinkle">+{match.related_credit}% transferable skills</div>}
        </div>
      </div>
      <div className="grid gap-1.5">
        {rows.map((row) => (
          <div key={row.skill_id} className="rounded-xl bg-white/70 px-3 py-2 text-sm">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className={`h-2 w-2 shrink-0 rounded-full ${DOT_TONE[row.state]}`} />
                <span className="font-medium">{row.skill}</span>
                <span className="font-mono text-[10px] uppercase tracking-wider text-violet">{row.importance === "must_have" ? "must" : "nice"}</span>
                {row.verified && <span className="font-mono text-[10px] text-teal">verified</span>}
              </div>
              <div className="shrink-0 font-mono text-xs text-plum/70">
                {row.state === "missing" && `missing, needs L${row.needed}`}
                {row.state === "related" && `${row.credit} credit of 1`}
                {(row.state === "matched" || row.state === "below") && `L${row.level} of L${row.needed}${row.state === "below" ? " (below)" : ""}`}
              </div>
            </div>
            {row.state === "related" && (
              <div className="mt-1 pl-4 font-mono text-[10px] text-periwinkle">
                you do not have this, but you know {row.via_skill} at L{row.via_level} — similarity {row.similarity}
              </div>
            )}
          </div>
        ))}
      </div>
      <p className="text-xs text-plum/60">
        Score = weighted credit / total weight. Must-have skills weigh 3, nice-to-have weigh 1. Credit per skill = min(1, your level / needed level), times 1.1 if faculty verified it.
        {related.length > 0 && " A skill you do not have can earn up to 0.4 credit if you know a semantically similar one — measured by embedding similarity, and only the single closest skill counts."}
      </p>
    </div>
  );
}

export function Modal({ open, onClose, title, children, wide }) {
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (event) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-plum/40 p-4" onClick={onClose}>
      <div className={`max-h-[90vh] w-full ${wide ? "max-w-3xl" : "max-w-xl"} overflow-y-auto rounded-card bg-cream p-6 shadow-soft`} onClick={(event) => event.stopPropagation()} role="dialog" aria-modal="true">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-display text-2xl">{title}</h2>
          <button type="button" className="btn-secondary px-3 py-1" onClick={onClose} aria-label="close">
            close
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Loading({ text = "loading" }) {
  return <div className="py-10 text-center font-mono text-sm text-violet">{text}</div>;
}

export function ErrorNote({ error }) {
  if (!error) return null;
  return <div className="rounded-2xl border border-signal/30 bg-signal/10 px-4 py-3 text-sm text-signal">{error}</div>;
}

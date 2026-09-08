import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api";
import { Empty, ErrorNote, Loading } from "../../components/ui";

const STEPS = ["applied", "shortlisted", "interview", "offered"];

function Timeline({ status }) {
  if (status === "rejected") {
    return <div className="font-mono text-xs text-signal">rejected</div>;
  }
  const reached = STEPS.indexOf(status);
  return (
    <div className="flex items-center gap-1">
      {STEPS.map((step, index) => (
        <div key={step} className="flex items-center gap-1">
          <div className={`h-2.5 w-2.5 rounded-full ${index <= reached ? "bg-teal" : "bg-plum/15"}`} title={step} />
          {index < STEPS.length - 1 && <div className={`h-0.5 w-8 ${index < reached ? "bg-teal" : "bg-plum/15"}`} />}
        </div>
      ))}
      <span className="ml-2 font-mono text-xs text-plum/70">{status}</span>
    </div>
  );
}

export default function StudentApplications() {
  const [applications, setApplications] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.studentApplications().then(setApplications).catch((err) => setError(err.message));
  }, []);

  if (error) return <ErrorNote error={error} />;
  if (!applications) return <Loading />;

  return (
    <div className="grid gap-6">
      <div>
        <div className="label">{applications.length} applications</div>
        <h1 className="font-display text-5xl">Applications</h1>
      </div>
      {applications.length === 0 ? (
        <Empty title="No applications yet" body="Open a matched posting and hit Apply." />
      ) : (
        <div className="grid gap-3">
          {applications.map((application) => (
            <div key={application.id} className="card flex flex-wrap items-center justify-between gap-3">
              <div>
                <Link to={`/student/openings?open=${application.posting_id}`} className="font-semibold hover:underline">
                  {application.title}
                </Link>
                <div className="text-xs text-plum/60">
                  {application.company} · updated {new Date(application.updated_at).toLocaleDateString()}
                </div>
              </div>
              <Timeline status={application.status} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

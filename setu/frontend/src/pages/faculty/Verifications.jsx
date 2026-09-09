import { useEffect, useMemo, useState } from "react";
import { api } from "../../api";
import { Empty, ErrorNote, LEVEL_NAMES, LevelDots, Loading, Modal, useToast } from "../../components/ui";

export default function FacultyVerifications() {
  const [requests, setRequests] = useState(null);
  const [tab, setTab] = useState("pending");
  const [error, setError] = useState(null);
  const [reviewingId, setReviewingId] = useState(null);
  const [rejectModalItem, setRejectModalItem] = useState(null);
  const [rejectFeedback, setRejectFeedback] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [showToast, toast] = useToast();

  function loadQueue() {
    api
      .facultyVerificationRequests()
      .then((data) => setRequests(data))
      .catch((err) => setError(err.message));
  }

  useEffect(() => {
    loadQueue();
  }, []);

  const counts = useMemo(() => {
    if (!requests) return { pending: 0, approved: 0, rejected: 0, all: 0 };
    return {
      pending: requests.filter((r) => r.status === "pending").length,
      approved: requests.filter((r) => r.status === "approved").length,
      rejected: requests.filter((r) => r.status === "rejected").length,
      all: requests.length,
    };
  }, [requests]);

  const visible = useMemo(() => {
    if (!requests) return [];
    if (tab === "all") return requests;
    return requests.filter((r) => r.status === tab);
  }, [requests, tab]);

  async function handleApprove(item) {
    setReviewingId(item.id);
    try {
      const updated = await api.reviewVerificationRequest(item.id, { action: "approve" });
      setRequests((prev) => prev.map((r) => (r.id === item.id ? updated : r)));
      showToast(`Verified ${item.skill_name} for ${item.student_name}.`);
    } catch (err) {
      showToast(err.message || "Failed to approve skill", "error");
    } finally {
      setReviewingId(null);
    }
  }

  function openRejectModal(item) {
    setRejectModalItem(item);
    setRejectFeedback("");
  }

  async function handleRejectSubmit(e) {
    e.preventDefault();
    if (!rejectModalItem) return;

    setSubmitting(true);
    try {
      const updated = await api.reviewVerificationRequest(rejectModalItem.id, {
        action: "reject",
        feedback: rejectFeedback.trim() || undefined,
      });
      setRequests((prev) => prev.map((r) => (r.id === rejectModalItem.id ? updated : r)));
      showToast(`Rejected request for ${rejectModalItem.skill_name}. Feedback logged.`);
      setRejectModalItem(null);
    } catch (err) {
      showToast(err.message || "Failed to reject skill", "error");
    } finally {
      setSubmitting(false);
    }
  }

  if (error) return <ErrorNote error={error} />;
  if (!requests) return <Loading />;

  return (
    <div className="grid gap-6">
      {toast}

      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="label">Institutional Trust & Competency Validation</div>
          <h1 className="font-display text-5xl">Skill Verifications</h1>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {[
            { id: "pending", label: "Pending", count: counts.pending },
            { id: "approved", label: "Approved", count: counts.approved },
            { id: "rejected", label: "Rejected", count: counts.rejected },
            { id: "all", label: "All Records", count: counts.all },
          ].map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`chip transition-colors ${
                tab === t.id ? "bg-plum text-cream shadow-xs" : "bg-white/80 text-plum/70 hover:bg-white"
              }`}
            >
              <span>{t.label}</span>
              <span
                className={`ml-1 rounded-full px-1.5 py-0.2 font-mono text-[10px] ${
                  tab === t.id ? "bg-white/20 text-cream" : "bg-petal/80 text-plum"
                }`}
              >
                {t.count}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="card-mauve flex flex-wrap items-center justify-between gap-3 text-xs text-plum/80">
        <div>
          <strong>Faculty Placement Assurance:</strong> Verifying a student's skill endorses their practical competency to recruiters, increasing their match score in candidate pipelines.
        </div>
        <div className="font-mono text-[11px] text-plum/60">
          {counts.pending} pending requests requiring coordinator review
        </div>
      </div>

      {visible.length === 0 ? (
        <Empty
          title={tab === "pending" ? "All caught up!" : `No ${tab} verifications`}
          body={
            tab === "pending"
              ? "There are no pending skill verification requests from students at this time."
              : `No verification records found under the '${tab}' filter.`
          }
        />
      ) : (
        <div className="grid gap-4">
          {visible.map((item) => {
            const isProcessing = reviewingId === item.id;
            return (
              <div
                key={item.id}
                className="card flex flex-col justify-between gap-4 transition-all hover:shadow-soft"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-display text-2xl text-plum">{item.student_name}</span>
                      <span className="font-mono text-xs text-plum/60">({item.student_roll})</span>
                      <span className="chip bg-petal/60 text-plum text-xs">{item.batch_name}</span>
                      <span className="font-mono text-xs text-violet font-semibold">CGPA: {item.student_cgpa}</span>
                    </div>
                    <div className="mt-1 font-mono text-xs text-plum/60">{item.student_email}</div>
                  </div>

                  <div className="flex items-center gap-2">
                    {item.status === "pending" && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-amber/15 px-3 py-1 font-mono text-xs font-semibold text-amber">
                        <span className="animate-pulse">●</span> Pending Review
                      </span>
                    )}
                    {item.status === "approved" && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-teal/15 px-3 py-1 font-mono text-xs font-semibold text-teal">
                        ✓ Verified by {item.reviewer_name || "Faculty"}
                      </span>
                    )}
                    {item.status === "rejected" && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-signal/15 px-3 py-1 font-mono text-xs font-semibold text-signal">
                        ✕ Rejected
                      </span>
                    )}
                  </div>
                </div>

                <div className="grid gap-3 rounded-2xl border border-plum/10 bg-petal/20 p-4 sm:grid-cols-[1fr_2fr]">
                  <div className="space-y-1.5 border-b border-plum/10 pb-3 sm:border-b-0 sm:border-r sm:pb-0 sm:pr-4">
                    <div className="label">Requested Skill & Level</div>
                    <div className="text-base font-semibold text-plum">{item.skill_name}</div>
                    <div className="font-mono text-xs text-violet">{item.skill_category}</div>
                    <div className="flex items-center gap-1.5 pt-1">
                      <LevelDots level={item.level} />
                      <span className="font-mono text-xs text-plum/70">
                        Level {item.level} ({LEVEL_NAMES[item.level]})
                      </span>
                    </div>
                  </div>

                  <div className="space-y-2">
                    {item.course_name && (
                      <div>
                        <span className="label">Coursework / Lab: </span>
                        <span className="text-xs font-medium text-plum">{item.course_name}</span>
                      </div>
                    )}

                    {item.evidence_url && (
                      <div>
                        <span className="label">Repository / Evidence: </span>
                        <a
                          href={item.evidence_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-mono text-xs text-violet underline hover:text-plum inline-flex items-center gap-1"
                        >
                          {item.evidence_url}
                          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                          </svg>
                        </a>
                      </div>
                    )}

                    {item.notes && (
                      <div>
                        <span className="label">Student Implementation Notes: </span>
                        <p className="mt-0.5 text-xs text-plum/80 leading-relaxed italic">
                          "{item.notes}"
                        </p>
                      </div>
                    )}

                    {item.review_feedback && (
                      <div className="rounded-xl border border-signal/20 bg-signal/5 p-2 text-xs text-signal">
                        <strong>Faculty Feedback:</strong> {item.review_feedback}
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                  <div className="font-mono text-[11px] text-plum/50">
                    Submitted: {new Date(item.created_at).toLocaleDateString()} at{" "}
                    {new Date(item.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </div>

                  {item.status === "pending" ? (
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        className="btn-secondary text-xs text-signal hover:border-signal/40"
                        onClick={() => openRejectModal(item)}
                        disabled={isProcessing}
                      >
                        Reject...
                      </button>
                      <button
                        type="button"
                        className="btn-primary text-xs"
                        onClick={() => handleApprove(item)}
                        disabled={isProcessing}
                      >
                        {isProcessing ? "Verifying..." : "Approve & Verify"}
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        className="btn-secondary text-xs"
                        onClick={() => (item.status === "approved" ? openRejectModal(item) : handleApprove(item))}
                        disabled={isProcessing}
                      >
                        {item.status === "approved" ? "Revoke Verification" : "Re-Approve"}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Modal
        open={Boolean(rejectModalItem)}
        onClose={() => setRejectModalItem(null)}
        title={`Reject Verification: ${rejectModalItem?.skill_name || ""}`}
      >
        {rejectModalItem && (
          <form onSubmit={handleRejectSubmit} className="space-y-4">
            <div className="text-xs text-plum/80">
              Provide feedback for <strong>{rejectModalItem.student_name}</strong> explaining what is missing (e.g. required test coverage, capstone project depth, or classroom lab signoff).
            </div>

            <div>
              <label className="label">Feedback Note (Optional)</label>
              <textarea
                rows={3}
                className="input w-full mt-1"
                placeholder="e.g. Need code sample demonstrating Level 3 concurrency or unit tests with pytest..."
                value={rejectFeedback}
                onChange={(e) => setRejectFeedback(e.target.value)}
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-petal/60">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setRejectModalItem(null)}
                disabled={submitting}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn-primary bg-signal hover:bg-signal/90"
                disabled={submitting}
              >
                {submitting ? "Rejecting..." : "Confirm Rejection"}
              </button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
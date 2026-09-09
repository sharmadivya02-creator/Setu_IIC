import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../../api";
import { ErrorNote, LEVEL_NAMES, LevelDots, Loading, Modal, SkillChip, useToast } from "../../components/ui";
import { getCachedSampleResume } from "../../utils/sampleResume";

export default function StudentSkills() {
  const [taxonomy, setTaxonomy] = useState(null);
  const [profile, setProfile] = useState(null);
  const [levels, setLevels] = useState({});
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("all");
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [uploadingResume, setUploadingResume] = useState(false);
  const [resumeModalOpen, setResumeModalOpen] = useState(false);
  const [parsedResult, setParsedResult] = useState(null);
  const [selectedForApply, setSelectedForApply] = useState({});
  const [mergeMode, setMergeMode] = useState(true);
  const [modalCategory, setModalCategory] = useState("all");
  const [modalQuery, setModalQuery] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [showToast, toast] = useToast();
  const fileInputRef = useRef(null);

  const [verificationRequests, setVerificationRequests] = useState([]);
  const [verifyModalSkill, setVerifyModalSkill] = useState(null);
  const [verifyForm, setVerifyForm] = useState({ course_name: "", evidence_url: "", notes: "" });
  const [submittingVerify, setSubmittingVerify] = useState(false);

  useEffect(() => {
    // Pre-warm cached sample resume in memory on mount for instantaneous zero-delay access
    getCachedSampleResume();

    Promise.all([api.skills(), api.studentProfile(), api.myVerificationRequests().catch(() => [])])
      .then(([skills, profileData, vRequests]) => {
        setTaxonomy(skills);
        setProfile(profileData);
        setLevels(Object.fromEntries(profileData.skills.map((skill) => [skill.skill_id, skill.level])));
        setVerificationRequests(vRequests || []);
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

  const pendingRequestMap = useMemo(() => {
    const map = new Map();
    for (const req of verificationRequests) {
      if (req.status === "pending") {
        map.set(req.skill_id, req);
      }
    }
    return map;
  }, [verificationRequests]);

  function openVerifyModal(skill) {
    setVerifyModalSkill(skill);
    setVerifyForm({ course_name: "", evidence_url: "", notes: "" });
  }

  async function handleVerificationSubmit(e) {
    e.preventDefault();
    if (!verifyModalSkill) return;

    setSubmittingVerify(true);
    try {
      const created = await api.submitVerificationRequest({
        skill_id: verifyModalSkill.id,
        course_name: verifyForm.course_name.trim() || undefined,
        evidence_url: verifyForm.evidence_url.trim() || undefined,
        notes: verifyForm.notes.trim() || undefined,
      });
      setVerificationRequests((prev) => [created, ...prev.filter((r) => r.skill_id !== verifyModalSkill.id)]);
      showToast(`Verification requested for ${verifyModalSkill.name}. Faculty notified.`);
      setVerifyModalSkill(null);
    } catch (err) {
      showToast(err.message || "Failed to submit verification request", "error");
    } finally {
      setSubmittingVerify(false);
    }
  }

  function setLevel(skillId, level) {
    setLevels((current) => {
      const next = { ...current };
      if (level === 0) delete next[skillId];
      else next[skillId] = level;
      return next;
    });
  }

  async function processResumeFile(file) {
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      showToast("Please upload a PDF file (.pdf)", "error");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      showToast("File is too large (max 10 MB)", "error");
      return;
    }

    setUploadingResume(true);
    showToast("Analyzing resume with Groq AI... extracting skills.");

    try {
      const data = await api.parseResume(file);
      setParsedResult(data);
      const initialSelected = {};
      (data.skills || []).forEach((item) => {
        initialSelected[item.skill_id] = { selected: true, level: item.suggested_level };
      });
      setSelectedForApply(initialSelected);
      setModalCategory("all");
      setModalQuery("");
      setResumeModalOpen(true);
      showToast(`Analyzed resume! Found ${data.total_detected} matching skills.`);
    } catch (err) {
      showToast(err.message || "Failed to analyze resume", "error");
    } finally {
      setUploadingResume(false);
    }
  }

  function handleFileUpload(event) {
    const file = event.target.files?.[0];
    if (file) {
      event.target.value = "";
      processResumeFile(file);
    }
  }

  async function handleAutoUploadSample() {
    if (uploadingResume || saving) return;
    const sampleFile = getCachedSampleResume();
    if (!sampleFile) {
      showToast("Sample resume could not be prepared", "error");
      return;
    }
    showToast("Loaded pre-cached sample resume (Aarav Sharma) · Sending to AI parser...");
    await processResumeFile(sampleFile);
  }

  function handleDragOver(event) {
    event.preventDefault();
    if (!isDragging) setIsDragging(true);
  }

  function handleDragLeave(event) {
    event.preventDefault();
    setIsDragging(false);
  }

  function handleDrop(event) {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer?.files?.[0];
    if (file) {
      processResumeFile(file);
    }
  }

  function toggleSkillSelection(skillId) {
    setSelectedForApply((current) => ({
      ...current,
      [skillId]: {
        ...current[skillId],
        selected: !current[skillId]?.selected,
      },
    }));
  }

  function setExtractedLevel(skillId, level) {
    setSelectedForApply((current) => ({
      ...current,
      [skillId]: {
        ...current[skillId],
        level,
        selected: true,
      },
    }));
  }

  function setAllSelected(state) {
    setSelectedForApply((current) => {
      const next = { ...current };
      (parsedResult?.skills || []).forEach((s) => {
        if (next[s.skill_id]) {
          next[s.skill_id] = { ...next[s.skill_id], selected: state };
        } else {
          next[s.skill_id] = { selected: state, level: s.suggested_level };
        }
      });
      return next;
    });
  }

  async function applyExtractedSkills(autoSave = false) {
    if (!parsedResult) return;
    const nextLevels = mergeMode ? { ...levels } : {};
    let appliedCount = 0;
    for (const skill of parsedResult.skills) {
      const item = selectedForApply[skill.skill_id];
      if (item?.selected) {
        nextLevels[skill.skill_id] = item.level;
        appliedCount++;
      }
    }
    setLevels(nextLevels);

    if (autoSave) {
      setSaving(true);
      try {
        const payload = Object.entries(nextLevels).map(([skill_id, level]) => ({
          skill_id: Number(skill_id),
          level,
        }));
        const updated = await api.saveStudentSkills(payload);
        setProfile(updated);
        setResumeModalOpen(false);
        showToast(`Saved ${appliedCount} skills to your profile! Matches recalculated.`);
      } catch (err) {
        showToast(err.message || "Failed to save skills", "error");
      } finally {
        setSaving(false);
      }
    } else {
      setResumeModalOpen(false);
      showToast(`Applied ${appliedCount} skills to draft! Click Save to confirm.`);
    }
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

  const modalCategories = useMemo(() => {
    if (!parsedResult?.skills) return [];
    return ["all", ...new Set(parsedResult.skills.map((s) => s.category))];
  }, [parsedResult]);

  const filteredModalSkills = useMemo(() => {
    if (!parsedResult?.skills) return [];
    const q = modalQuery.trim().toLowerCase();
    return parsedResult.skills.filter((s) => {
      const matchCat = modalCategory === "all" || s.category === modalCategory;
      const matchText = !q || s.name.toLowerCase().includes(q) || s.category.toLowerCase().includes(q) || (s.evidence && s.evidence.toLowerCase().includes(q));
      return matchCat && matchText;
    });
  }, [parsedResult, modalCategory, modalQuery]);

  if (error) return <ErrorNote error={error} />;
  if (!taxonomy || !profile) return <Loading />;

  const selected = taxonomy.filter((skill) => levels[skill.id]);
  const selectedSkillsCount = Object.values(selectedForApply).filter((item) => item.selected).length;

  return (
    <div
      className="grid gap-6"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {toast}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="label">structured profile, no free text</div>
          <h1 className="font-display text-5xl">My skills</h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            className="hidden"
            onChange={handleFileUpload}
          />
          <button
            type="button"
            className="btn-secondary"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadingResume || saving}
          >
            {uploadingResume ? (
              <span className="inline-flex items-center gap-2">
                <svg className="h-4 w-4 animate-spin text-plum" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Analyzing Resume...
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5">
                <span></span> Auto-fill from Resume (PDF)
              </span>
            )}
          </button>
          <button
            type="button"
            className="btn-secondary border-plum/30 bg-plum/5 hover:bg-plum/10 text-plum font-medium shadow-xs"
            onClick={handleAutoUploadSample}
            disabled={uploadingResume || saving}
            title="Auto-upload pre-loaded sample resume (Aarav Sharma) to demonstrate instant Groq AI extraction"
          >
            <span>Try Sample Resume</span>
          </button>
          <button type="button" className="btn-primary" onClick={save} disabled={saving || uploadingResume}>
            {saving ? "saving" : `Save ${selected.length} skills`}
          </button>
        </div>
      </div>

      {uploadingResume && (
        <div className="card-mauve flex items-center gap-3 animate-pulse text-sm text-plum">
          <svg className="h-5 w-5 animate-spin text-plum" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
          <div>
            <div className="font-semibold">Extracting text & matching skills with Groq AI...</div>
            <div className="text-xs opacity-75">Reading PDF structure, categorizing experience, and mapping to Setu verified taxonomy.</div>
          </div>
        </div>
      )}

      <section
        className={`card transition-colors ${isDragging ? "border-2 border-dashed border-plum bg-petal/40" : ""
          }`}
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-display text-2xl">Selected ({selected.length})</h2>
          <div className="font-mono text-xs text-plum/60">changing a verified skill's level removes its verification</div>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {selected.length === 0 && (
            <div
              className={`w-full rounded-2xl border-2 border-dashed p-6 text-center transition-colors ${isDragging
                ? "border-plum bg-white/90"
                : "border-violet/30 bg-petal/20"
                }`}
            >
              <div className="text-sm font-medium text-plum">No skills selected yet.</div>
              <p className="mt-1 text-xs text-plum/60">
                Drag and drop your PDF resume here, or pick skills from the taxonomy below.
              </p>
              <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
                <button
                  type="button"
                  className="btn-secondary text-xs"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploadingResume}
                >
                  Upload Resume PDF
                </button>
                <button
                  type="button"
                  className="btn-secondary border-plum/30 bg-plum/5 text-xs hover:bg-plum/10 font-medium"
                  onClick={handleAutoUploadSample}
                  disabled={uploadingResume}
                  title="Auto-fill with sample resume for instant demonstration"
                >
                  Try Sample Resume
                </button>
              </div>
            </div>
          )}
          {selected.map((skill) => {
            const currentLevel = levels[skill.id];
            const isVerified = verifiedIds.has(skill.id) && currentLevel === profile.skills.find((item) => item.skill_id === skill.id)?.level;
            const pendingRequest = pendingRequestMap.get(skill.id);

            return (
              <div
                key={skill.id}
                className="inline-flex items-center gap-2 rounded-2xl border border-plum/15 bg-white/90 px-3 py-1.5 shadow-xs transition-all hover:border-plum/30"
              >
                <div className="flex items-center gap-1.5">
                  <span className="font-medium text-sm text-plum">{skill.name}</span>
                  <LevelDots level={currentLevel} />
                </div>

                {isVerified ? (
                  <span
                    title="Verified by faculty coordinator"
                    className="inline-flex items-center gap-0.5 rounded-full bg-teal/15 px-2 py-0.5 font-mono text-[10px] font-semibold text-teal"
                  >
                    Verified
                  </span>
                ) : pendingRequest ? (
                  <span
                    title={`Verification pending review (Course: ${pendingRequest.course_name || "Coursework"})`}
                    className="inline-flex items-center gap-1 rounded-full bg-amber/15 px-2 py-0.5 font-mono text-[10px] font-semibold text-amber"
                  >
                    <span className="animate-pulse"></span> Pending Review
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={() => openVerifyModal(skill)}
                    title="Request faculty verification with coursework or project link"
                    className="rounded-full border border-plum/20 bg-plum/5 px-2 py-0.5 text-[11px] font-medium text-plum hover:bg-plum hover:text-cream transition-colors"
                  >
                    Request Verify
                  </button>
                )}

                <button
                  type="button"
                  onClick={() => setLevel(skill.id, 0)}
                  title={`Remove ${skill.name}`}
                  className="ml-0.5 text-xs text-plum/40 hover:text-signal transition-colors"
                  aria-label={`Remove ${skill.name}`}
                >
                  ✕
                </button>
              </div>
            );
          })}
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

      <Modal
        open={resumeModalOpen}
        onClose={() => setResumeModalOpen(false)}
        title="Resume Skill Analysis"
        wide
      >
        {parsedResult && (
          <div className="space-y-4">
            <div className="rounded-2xl border border-violet/20 bg-petal/40 p-4">
              <div className="label mb-1">Profile Overview</div>
              <div className="text-sm font-medium text-plum">{parsedResult.summary}</div>
              <div className="mt-2 font-mono text-xs text-violet">
                Found {parsedResult.total_detected} skills matching Setu's verified taxonomy. Review, adjust levels, and apply below.
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-petal/60 pb-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold text-plum">Mode:</span>
                <button
                  type="button"
                  onClick={() => setMergeMode(true)}
                  className={`chip transition-colors ${mergeMode ? "bg-plum text-cream" : "bg-petal/60 text-plum hover:bg-petal"}`}
                >
                  Merge with current
                </button>
                <button
                  type="button"
                  onClick={() => setMergeMode(false)}
                  className={`chip transition-colors ${!mergeMode ? "bg-plum text-cream" : "bg-petal/60 text-plum hover:bg-petal"}`}
                >
                  Replace current
                </button>
              </div>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setAllSelected(selectedSkillsCount !== parsedResult.skills.length)}
                  className="font-mono text-xs text-periwinkle hover:underline"
                >
                  {selectedSkillsCount === parsedResult.skills.length ? "Deselect All" : "Select All"}
                </button>
                <div className="font-mono text-xs text-plum/70 font-medium">
                  {selectedSkillsCount} of {parsedResult.skills.length} selected
                </div>
              </div>
            </div>

            <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
              <input
                className="input py-1.5 text-xs"
                placeholder="filter extracted skills..."
                value={modalQuery}
                onChange={(e) => setModalQuery(e.target.value)}
              />
              <div className="flex flex-wrap gap-1">
                {modalCategories.map((cat) => (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => setModalCategory(cat)}
                    className={`chip text-xs ${modalCategory === cat ? "bg-plum text-cream" : "bg-petal/60"}`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            <div className="max-h-[46vh] space-y-2 overflow-y-auto pr-1">
              {filteredModalSkills.length === 0 ? (
                <div className="p-4 text-center text-xs text-plum/60">No skills match the current filter.</div>
              ) : (
                filteredModalSkills.map((skill) => {
                  const item = selectedForApply[skill.skill_id] || { selected: false, level: skill.suggested_level };
                  return (
                    <div
                      key={skill.skill_id}
                      className={`flex flex-col gap-2 rounded-2xl border p-3 transition-colors sm:flex-row sm:items-center sm:justify-between ${item.selected ? "border-violet/40 bg-white/90 shadow-sm" : "border-transparent bg-white/40 opacity-60"
                        }`}
                    >
                      <div className="flex items-start gap-3">
                        <input
                          type="checkbox"
                          checked={item.selected}
                          onChange={() => toggleSkillSelection(skill.skill_id)}
                          className="mt-1 h-4 w-4 rounded border-violet/40 text-plum focus:ring-periwinkle cursor-pointer"
                        />
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-semibold text-plum">{skill.name}</span>
                            <span className="font-mono text-[10px] text-violet bg-petal/60 px-1.5 py-0.5 rounded">
                              {skill.category}
                            </span>
                            <span className="font-mono text-[11px] text-plum/70">
                              Level {item.level} ({LEVEL_NAMES[item.level]})
                            </span>
                          </div>
                          {skill.evidence && (
                            <div className="mt-0.5 text-xs text-plum/70 italic">
                              "{skill.evidence}"
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-1 self-end sm:self-auto">
                        {[1, 2, 3, 4, 5].map((value) => (
                          <button
                            key={value}
                            type="button"
                            title={LEVEL_NAMES[value]}
                            onClick={() => setExtractedLevel(skill.skill_id, value)}
                            className={`h-7 w-7 rounded-full font-mono text-xs transition-colors ${value <= item.level
                              ? "bg-plum text-cream"
                              : "bg-plum/10 text-plum/60 hover:bg-plum/20"
                              }`}
                          >
                            {value}
                          </button>
                        ))}
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-petal/60 pt-4">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setResumeModalOpen(false)}
                disabled={saving}
              >
                Cancel
              </button>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => applyExtractedSkills(false)}
                  disabled={saving || selectedSkillsCount === 0}
                  title="Apply skills to the form to review manually before saving"
                >
                  Apply to Draft
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => applyExtractedSkills(true)}
                  disabled={saving || selectedSkillsCount === 0}
                >
                  {saving ? "Saving..." : `Apply & Save ${selectedSkillsCount} Skills`}
                </button>
              </div>
            </div>
          </div>
        )}
      </Modal>

      <Modal
        open={Boolean(verifyModalSkill)}
        onClose={() => setVerifyModalSkill(null)}
        title={`Request Faculty Verification: ${verifyModalSkill?.name || ""}`}
      >
        {verifyModalSkill && (
          <form onSubmit={handleVerificationSubmit} className="space-y-4">
            <div className="rounded-2xl border border-violet/20 bg-petal/30 p-3 text-xs text-plum/80">
              <div className="font-semibold text-plum mb-0.5">
                Claimed Proficiency: Level {levels[verifyModalSkill.id]} ({LEVEL_NAMES[levels[verifyModalSkill.id]]})
              </div>
              <div>
                Faculty placement coordinators will review your coursework, lab repository, or practical project evidence before validating the skill. Verified credentials carry bonus weight in recruiter candidate search.
              </div>
            </div>

            <div>
              <label className="label">Course / Lab Context</label>
              <input
                type="text"
                className="input w-full mt-1"
                placeholder="e.g. CS-302 Web Architectures or Minor Capstone"
                value={verifyForm.course_name}
                onChange={(e) => setVerifyForm({ ...verifyForm, course_name: e.target.value })}
              />
            </div>

            <div>
              <label className="label">Evidence / Repository URL</label>
              <input
                type="url"
                className="input w-full mt-1"
                placeholder="https://github.com/your-username/project-repo"
                value={verifyForm.evidence_url}
                onChange={(e) => setVerifyForm({ ...verifyForm, evidence_url: e.target.value })}
              />
            </div>

            <div>
              <label className="label">Implementation Notes & Practical Experience</label>
              <textarea
                rows={3}
                className="input w-full mt-1"
                placeholder="Briefly describe what you built (architecture, features implemented, APIs integrated)..."
                value={verifyForm.notes}
                onChange={(e) => setVerifyForm({ ...verifyForm, notes: e.target.value })}
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-petal/60">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setVerifyModalSkill(null)}
                disabled={submittingVerify}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn-primary"
                disabled={submittingVerify}
              >
                {submittingVerify ? "Submitting..." : "Submit for Faculty Review"}
              </button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
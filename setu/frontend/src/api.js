const BASE = (import.meta.env.VITE_API_URL || "") + "/api";

let token = null;
try {
  token = localStorage.getItem("setu_token");
} catch {
  token = null;
}

export function setToken(value) {
  token = value;
  try {
    if (value) localStorage.setItem("setu_token", value);
    else localStorage.removeItem("setu_token");
  } catch {
    return;
  }
}

export function hasToken() {
  return Boolean(token);
}

async function request(method, path, body) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(BASE + path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (response.status === 204) return null;
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail || payload);
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }
  return payload;
}

const get = (path) => request("GET", path);
const post = (path, body) => request("POST", path, body);
const put = (path, body) => request("PUT", path, body);
const del = (path) => request("DELETE", path);

async function upload(path, formData) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(BASE + path, {
    method: "POST",
    headers,
    body: formData,
  });
  if (response.status === 204) return null;
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail || payload);
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }
  return payload;
}

export const api = {
  login: (email, password) => post("/auth/login", { email, password }),
  register: (form) => post("/auth/register", form),
  me: () => get("/auth/me"),
  skills: () => get("/skills"),
  relatedSkills: (skillId) => get(`/skills/${skillId}/related`),
  batches: () => get("/batches"),

  studentProfile: () => get("/students/me"),
  updateStudentProfile: (form) => put("/students/me", form),
  saveStudentSkills: (skills) => put("/students/me/skills", skills),
  parseResume: (file) => {
    const form = new FormData();
    form.append("file", file);
    return upload("/students/me/parse-resume", form);
  },
  studentMatches: () => get("/students/me/matches"),
  studentGaps: () => get("/students/me/gaps"),
  apply: (postingId) => post(`/students/me/apply/${postingId}`),
  studentApplications: () => get("/students/me/applications"),
  submitVerificationRequest: (form) => post("/students/me/verification-requests", form),
  myVerificationRequests: () => get("/students/me/verification-requests"),

  analytics: (batchId) => get(`/faculty/analytics${batchId ? `?batch_id=${batchId}` : ""}`),
  facultyStudents: (batchId) => get(`/faculty/students${batchId ? `?batch_id=${batchId}` : ""}`),
  facultyStudent: (id) => get(`/faculty/students/${id}`),
  addStudent: (form) => post("/faculty/students", form),
  editStudent: (id, form) => put(`/faculty/students/${id}`, form),
  verifySkill: (studentId, skillId, verified) => post(`/faculty/students/${studentId}/skills/${skillId}/verify?verified=${verified}`),
  facultyVerificationRequests: (status) => get(`/faculty/verification-requests${status ? `?status=${status}` : ""}`),
  facultyPendingVerificationsCount: () => get("/faculty/verification-requests/count"),
  reviewVerificationRequest: (requestId, form) => post(`/faculty/verification-requests/${requestId}/review`, form),
  refreshMarket: () => post("/faculty/market/refresh"),

  recruiterPostings: () => get("/recruiters/postings"),
  createPosting: (form) => post("/recruiters/postings", form),
  updatePosting: (id, form) => put(`/recruiters/postings/${id}`, form),
  candidates: (postingId) => get(`/recruiters/postings/${postingId}/candidates`),
  shortlist: (postingId, studentId) => post(`/recruiters/postings/${postingId}/shortlist/${studentId}`),
  postingApplications: (postingId) => get(`/recruiters/postings/${postingId}/applications`),
  setStatus: (applicationId, status) => put(`/recruiters/applications/${applicationId}/status`, { status }),

  uploadPolicyDocument: (file) => {
    const form = new FormData();
    form.append("file", file);
    return upload("/recruiters/company/documents", form);
  },
  listPolicyDocuments: () => get("/recruiters/company/documents"),
  deletePolicyDocument: (documentId) => del(`/recruiters/company/documents/${documentId}`),
  policyCheck: (postingId, studentId) => get(`/recruiters/postings/${postingId}/candidates/${studentId}/policy-check`),
};
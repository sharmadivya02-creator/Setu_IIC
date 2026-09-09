import { StrictMode, Suspense, lazy } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import "./index.css";
import { AuthProvider, RequireRole } from "./auth";
import Shell from "./components/Shell";
import { Login, Register } from "./pages/Auth";
import StudentDashboard from "./pages/student/Dashboard";
import StudentSkills from "./pages/student/Skills";
import StudentOpenings from "./pages/student/Openings";
import StudentApplications from "./pages/student/Applications";
import FacultyAnalytics from "./pages/faculty/Analytics";
import FacultyStudents from "./pages/faculty/Students";
import FacultyMarket from "./pages/faculty/Market";
import FacultyVerifications from "./pages/faculty/Verifications";
import RecruiterPostings from "./pages/recruiter/Postings";
import RecruiterCandidates from "./pages/recruiter/Candidates";
import RecruiterPipeline from "./pages/recruiter/Pipeline";

const Landing = lazy(() => import("./pages/Landing"));

function App() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <Suspense fallback={<div className="h-screen bg-periwinkle" />}>
            <Landing />
          </Suspense>
        }
      />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route
        path="/student"
        element={
          <RequireRole role="student">
            <Shell />
          </RequireRole>
        }
      >
        <Route index element={<StudentDashboard />} />
        <Route path="skills" element={<StudentSkills />} />
        <Route path="openings" element={<StudentOpenings />} />
        <Route path="applications" element={<StudentApplications />} />
      </Route>

      <Route
        path="/faculty"
        element={
          <RequireRole role="faculty">
            <Shell />
          </RequireRole>
        }
      >
        <Route index element={<FacultyAnalytics />} />
        <Route path="verifications" element={<FacultyVerifications />} />
        <Route path="students" element={<FacultyStudents />} />
        <Route path="market" element={<FacultyMarket />} />
      </Route>

      <Route
        path="/recruiter"
        element={
          <RequireRole role="recruiter">
            <Shell />
          </RequireRole>
        }
      >
        <Route index element={<RecruiterPostings />} />
        <Route path="postings/:postingId" element={<RecruiterCandidates />} />
        <Route path="pipeline" element={<RecruiterPipeline />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
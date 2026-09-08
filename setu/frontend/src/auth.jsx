import { createContext, useContext, useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { api, hasToken, setToken } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(hasToken());

  useEffect(() => {
    if (!hasToken()) return;
    api
      .me()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, []);

  function signIn(payload) {
    setToken(payload.access_token);
    setUser(payload.user);
  }

  function signOut() {
    setToken(null);
    setUser(null);
  }

  return <AuthContext.Provider value={{ user, loading, signIn, signOut }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}

export function homeFor(role) {
  return `/${role}`;
}

export function RequireRole({ role, children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return <div className="flex h-screen items-center justify-center font-mono text-sm text-violet">loading session</div>;
  }
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== role) return <Navigate to={homeFor(user.role)} replace />;
  return children;
}

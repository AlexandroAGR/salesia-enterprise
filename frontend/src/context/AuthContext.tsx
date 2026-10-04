import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, TOKEN_KEY } from "../lib/api";
import type { SessionUser } from "../types";
import { AuthContext, type AuthContextValue } from "./auth-context";

const hasStoredToken = () => localStorage.getItem(TOKEN_KEY) !== null;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(() => null);
  const [loading, setLoading] = useState(hasStoredToken);

  useEffect(() => {
    if (!hasStoredToken()) {
      return;
    }

    api
      .get<SessionUser>("/auth/me")
      .then((sessionUser) => setUser(sessionUser))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const response = await api.post<{ access_token: string }>("/auth/login", {
      email,
      password,
    });

    localStorage.setItem(TOKEN_KEY, response.access_token);
    setLoading(true);

    try {
      const sessionUser = await api.get<SessionUser>("/auth/me");
      setUser(sessionUser);
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
    setLoading(false);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, loading, login, logout }),
    [user, loading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

import { createContext, useContext } from "react";
import type { SessionUser } from "../types";

export type AuthContextValue = {
  user: SessionUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (context === null) {
    throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  }

  return context;
}

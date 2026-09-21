"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, MeResponse } from "./api";

interface AuthState {
  me: MeResponse | null;
  loading: boolean;
  orgId: string | null;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthState>({ me: null, loading: true, orgId: null, refresh: async () => {} });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    try {
      const data = await api.get<MeResponse>("/api/v1/auth/me");
      setMe(data);
    } catch {
      setMe(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const orgId = me?.memberships[0]?.organization_id ?? null;

  return <AuthContext.Provider value={{ me, loading, orgId, refresh }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}

/** Wraps a page's content, redirecting to /login if the session isn't
 * valid. Every protected page uses this rather than re-implementing the
 * check — the actual enforcement still lives server-side (this is UX,
 * not the security boundary). */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { me, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !me) {
      router.replace("/login");
    }
  }, [loading, me, router]);

  if (loading) return <div className="p-8 text-sm text-neutral-500">Loading...</div>;
  if (!me) return null;
  return <>{children}</>;
}

export function isApiError(err: unknown): err is ApiError {
  return err instanceof ApiError;
}

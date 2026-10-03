"use client";

import { useCallback, useEffect, useState } from "react";
import { RequireAuth, useAuth } from "@/lib/auth";
import { NavShell } from "@/components/NavShell";
import { StatusBadge } from "@/components/StatusBadge";
import { api, ApiError, ConnectionOut, SyncResultOut } from "@/lib/api";

function AddConnectionForm({ orgId, onAdded }: { orgId: string; onAdded: () => void }) {
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [open, setOpen] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.post(`/api/v1/orgs/${orgId}/connections`, { provider: "GITHUB", token });
      setToken("");
      setOpen(false);
      onAdded();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not connect to GitHub");
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-500">
        Connect GitHub
      </button>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="mb-6 space-y-3 rounded-lg border border-neutral-200 bg-white p-5">
      {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
      <div>
        <label className="mb-1 block text-xs font-medium text-neutral-700">Personal access token</label>
        <input
          type="password"
          required
          value={token}
          onChange={(e) => setToken(e.target.value)}
          placeholder="ghp_..."
          className="w-full rounded-md border border-neutral-300 px-3 py-1.5 text-sm font-mono focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
        <p className="mt-1 text-xs text-neutral-400">
          Needs <code className="rounded bg-neutral-100 px-1">repo</code> and <code className="rounded bg-neutral-100 px-1">read:org</code> scopes.
          Stored encrypted at rest — never shown again after saving.
        </p>
      </div>
      <div className="flex gap-2">
        <button type="submit" disabled={submitting} className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50">
          {submitting ? "Validating..." : "Connect"}
        </button>
        <button type="button" onClick={() => setOpen(false)} className="rounded-md px-3 py-2 text-sm font-medium text-neutral-500 hover:text-neutral-800">
          Cancel
        </button>
      </div>
    </form>
  );
}

function IntegrationsContent() {
  const { orgId, me } = useAuth();
  const [connections, setConnections] = useState<ConnectionOut[] | null>(null);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [syncResult, setSyncResult] = useState<SyncResultOut | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);

  const role = me?.memberships.find((m) => m.organization_id === orgId)?.role;
  const canManage = role === "OWNER" || role === "ADMIN";

  const load = useCallback(() => {
    if (!orgId) return;
    api.get<ConnectionOut[]>(`/api/v1/orgs/${orgId}/connections`).then(setConnections);
  }, [orgId]);

  useEffect(load, [load]);

  const handleSync = async (connectionId: string) => {
    if (!orgId) return;
    setSyncing(connectionId);
    setSyncError(null);
    setSyncResult(null);
    try {
      const result = await api.post<SyncResultOut>(`/api/v1/orgs/${orgId}/connections/${connectionId}/sync`);
      setSyncResult(result);
      load();
    } catch (err) {
      setSyncError(err instanceof ApiError ? err.message : "Sync failed");
    } finally {
      setSyncing(null);
    }
  };

  const handleDelete = async (connectionId: string) => {
    if (!orgId) return;
    await api.delete(`/api/v1/orgs/${orgId}/connections/${connectionId}`);
    load();
  };

  return (
    <div className="mx-auto max-w-3xl p-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-neutral-900">Integrations</h1>
          <p className="mt-1 text-sm text-neutral-500">
            Connect a real account so NetraSee can evaluate controls automatically — no manual evidence upload.
          </p>
        </div>
        {canManage && <AddConnectionForm orgId={orgId!} onAdded={load} />}
      </div>

      {!connections ? (
        <div className="mt-8 text-sm text-neutral-500">Loading...</div>
      ) : (
        <div className="mt-6 divide-y divide-neutral-200 rounded-lg border border-neutral-200 bg-white">
          {connections.map((c) => (
            <div key={c.id} className="flex items-center justify-between px-5 py-4">
              <div>
                <div className="text-sm font-medium text-neutral-800">GitHub — {c.account_login}</div>
                <div className="text-xs text-neutral-500">
                  {c.last_synced_at ? `Last synced ${new Date(c.last_synced_at).toLocaleString()}` : "Never synced"}
                </div>
              </div>
              {canManage && (
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => handleSync(c.id)}
                    disabled={syncing === c.id}
                    className="rounded-md border border-neutral-300 px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-50 disabled:opacity-50"
                  >
                    {syncing === c.id ? "Syncing..." : "Sync now"}
                  </button>
                  <button onClick={() => handleDelete(c.id)} className="text-xs font-medium text-red-500 hover:text-red-700">
                    Disconnect
                  </button>
                </div>
              )}
            </div>
          ))}
          {connections.length === 0 && (
            <div className="px-5 py-6 text-center text-sm text-neutral-500">
              No connections yet. Connect GitHub, then bind a control to an automated check from its detail page.
            </div>
          )}
        </div>
      )}

      {syncError && <div className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{syncError}</div>}

      {syncResult && (
        <div className="mt-6">
          <h2 className="mb-2 text-sm font-semibold text-neutral-700">
            Sync results — {new Date(syncResult.synced_at).toLocaleString()}
          </h2>
          <div className="divide-y divide-neutral-200 rounded-lg border border-neutral-200 bg-white">
            {syncResult.results.map((r) => (
              <div key={r.control_id} className="flex items-start justify-between gap-4 px-5 py-3 text-sm">
                <div>
                  <div className="font-medium text-neutral-800">{r.control_key}</div>
                  <div className="text-xs text-neutral-500">{r.summary}</div>
                </div>
                <StatusBadge status={r.status} />
              </div>
            ))}
            {syncResult.results.length === 0 && (
              <div className="px-5 py-4 text-sm text-neutral-500">
                No controls are bound to this connection yet — bind one from a control&apos;s detail page.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function IntegrationsPage() {
  return (
    <RequireAuth>
      <NavShell>
        <IntegrationsContent />
      </NavShell>
    </RequireAuth>
  );
}

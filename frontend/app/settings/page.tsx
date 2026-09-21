"use client";

import { useCallback, useEffect, useState } from "react";
import { RequireAuth, useAuth } from "@/lib/auth";
import { NavShell } from "@/components/NavShell";
import { api, ApiError, MemberOut } from "@/lib/api";

const ROLE_OPTIONS = ["VIEWER", "ADMIN", "OWNER"] as const;

function AddMemberForm({ orgId, maxRole, onAdded }: { orgId: string; maxRole: string; onAdded: () => void }) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<string>("VIEWER");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [open, setOpen] = useState(false);

  const allowedRoles = ROLE_OPTIONS.filter(
    (r) => ROLE_OPTIONS.indexOf(r) <= ROLE_OPTIONS.indexOf(maxRole as (typeof ROLE_OPTIONS)[number])
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.post(`/api/v1/orgs/${orgId}/members`, { email, name, password, role });
      setEmail("");
      setName("");
      setPassword("");
      setRole("VIEWER");
      setOpen(false);
      onAdded();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not add member");
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-500">
        Add member
      </button>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="mb-6 space-y-3 rounded-lg border border-neutral-200 bg-white p-5">
      {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-neutral-700">Name</label>
          <input required value={name} onChange={(e) => setName(e.target.value)} className="w-full rounded-md border border-neutral-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500" />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-neutral-700">Email</label>
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="w-full rounded-md border border-neutral-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500" />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-neutral-700">Initial password</label>
          <input type="password" required minLength={10} value={password} onChange={(e) => setPassword(e.target.value)} className="w-full rounded-md border border-neutral-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500" />
          <p className="mt-1 text-xs text-neutral-400">No invite-email flow in v1 — share this with them directly.</p>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-neutral-700">Role</label>
          <select value={role} onChange={(e) => setRole(e.target.value)} className="w-full rounded-md border border-neutral-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500">
            {allowedRoles.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </div>
      </div>
      <div className="flex gap-2">
        <button type="submit" disabled={submitting} className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50">
          {submitting ? "Adding..." : "Add member"}
        </button>
        <button type="button" onClick={() => setOpen(false)} className="rounded-md px-3 py-2 text-sm font-medium text-neutral-500 hover:text-neutral-800">
          Cancel
        </button>
      </div>
    </form>
  );
}

function SettingsContent() {
  const { orgId, me } = useAuth();
  const [members, setMembers] = useState<MemberOut[] | null>(null);

  const role = me?.memberships.find((m) => m.organization_id === orgId)?.role;
  const orgName = me?.memberships.find((m) => m.organization_id === orgId)?.organization_name;
  const canManage = role === "OWNER" || role === "ADMIN";

  const load = useCallback(() => {
    if (!orgId) return;
    api.get<MemberOut[]>(`/api/v1/orgs/${orgId}/members`).then(setMembers);
  }, [orgId]);

  useEffect(load, [load]);

  return (
    <div className="mx-auto max-w-3xl p-8">
      <h1 className="text-xl font-semibold text-neutral-900">Settings</h1>

      <h2 className="mt-8 mb-2 text-sm font-semibold text-neutral-700">Organization</h2>
      <div className="rounded-lg border border-neutral-200 bg-white px-5 py-4 text-sm text-neutral-700">{orgName}</div>

      <div className="mt-8 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-neutral-700">Members</h2>
        {canManage && role && <AddMemberForm orgId={orgId!} maxRole={role} onAdded={load} />}
      </div>

      {!members ? (
        <div className="mt-3 text-sm text-neutral-500">Loading...</div>
      ) : (
        <div className="mt-3 divide-y divide-neutral-200 rounded-lg border border-neutral-200 bg-white">
          {members.map((m) => (
            <div key={m.user_id} className="flex items-center justify-between px-5 py-3 text-sm">
              <div>
                <div className="font-medium text-neutral-800">{m.name}</div>
                <div className="text-xs text-neutral-500">{m.email}</div>
              </div>
              <span className="text-xs font-medium text-neutral-500">{m.role}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function SettingsPage() {
  return (
    <RequireAuth>
      <NavShell>
        <SettingsContent />
      </NavShell>
    </RequireAuth>
  );
}

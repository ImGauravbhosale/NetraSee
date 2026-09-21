"use client";

import { useEffect, useState } from "react";
import { RequireAuth, useAuth } from "@/lib/auth";
import { NavShell } from "@/components/NavShell";
import { api, ApiError, AuditEventOut } from "@/lib/api";

function ActivityContent() {
  const { orgId } = useAuth();
  const [events, setEvents] = useState<AuditEventOut[] | null>(null);
  const [forbidden, setForbidden] = useState(false);

  useEffect(() => {
    if (!orgId) return;
    api
      .get<AuditEventOut[]>(`/api/v1/orgs/${orgId}/audit-log`)
      .then(setEvents)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) setForbidden(true);
      });
  }, [orgId]);

  if (forbidden) {
    return (
      <div className="mx-auto max-w-4xl p-8">
        <h1 className="text-xl font-semibold text-neutral-900">Activity Log</h1>
        <p className="mt-4 text-sm text-neutral-500">Only Owners and Admins can view the audit log.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl p-8">
      <h1 className="text-xl font-semibold text-neutral-900">Activity Log</h1>
      <p className="mt-1 text-sm text-neutral-500">Every mutating action taken in this organization — append-only.</p>

      {!events ? (
        <div className="mt-8 text-sm text-neutral-500">Loading...</div>
      ) : (
        <div className="mt-6 divide-y divide-neutral-200 rounded-lg border border-neutral-200 bg-white">
          {events.map((e) => (
            <div key={e.id} className="px-5 py-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-medium text-neutral-800">{e.action}</span>
                <span className="text-xs text-neutral-400">{new Date(e.created_at).toLocaleString()}</span>
              </div>
              <div className="mt-0.5 text-xs text-neutral-500">
                {e.resource_type} · {e.resource_id}
              </div>
            </div>
          ))}
          {events.length === 0 && <div className="px-5 py-6 text-center text-sm text-neutral-500">No activity recorded yet.</div>}
        </div>
      )}
    </div>
  );
}

export default function ActivityPage() {
  return (
    <RequireAuth>
      <NavShell>
        <ActivityContent />
      </NavShell>
    </RequireAuth>
  );
}

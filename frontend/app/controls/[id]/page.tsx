"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { RequireAuth, useAuth } from "@/lib/auth";
import { NavShell } from "@/components/NavShell";
import { StatusBadge } from "@/components/StatusBadge";
import { api, ApiError, ControlDetail } from "@/lib/api";

const STATUS_OPTIONS = ["PASS", "FAIL", "NEEDS_REVIEW", "NOT_APPLICABLE", "NOT_TESTED"] as const;

function ControlDetailContent() {
  const { id } = useParams<{ id: string }>();
  const { orgId, me } = useAuth();
  const [control, setControl] = useState<ControlDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const role = me?.memberships.find((m) => m.organization_id === orgId)?.role;
  const canEdit = role === "OWNER" || role === "ADMIN";

  const load = useCallback(() => {
    if (!orgId) return;
    api.get<ControlDetail>(`/api/v1/orgs/${orgId}/controls/${id}`).then(setControl);
  }, [orgId, id]);

  useEffect(load, [load]);

  const handleStatusChange = async (status: string) => {
    if (!orgId) return;
    setSaving(true);
    setError(null);
    try {
      await api.patch(`/api/v1/orgs/${orgId}/controls/${id}`, { status });
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update status");
    } finally {
      setSaving(false);
    }
  };

  if (!control) return <div className="p-8 text-sm text-neutral-500">Loading...</div>;

  const whyFailing =
    control.status === "FAIL"
      ? control.evidence.length === 0
        ? "No evidence is attached to this control."
        : control.evidence.every((e) => e.status === "EXPIRED")
          ? "All attached evidence has expired."
          : "Attached evidence exists but the control has not been marked passing — review the evidence below."
      : null;

  return (
    <div className="mx-auto max-w-3xl p-8">
      <Link href="/controls" className="text-xs font-medium text-neutral-400 hover:text-neutral-600">
        ← All controls
      </Link>

      <div className="mt-2 flex items-start justify-between gap-4">
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-neutral-400">{control.control_key}</div>
          <h1 className="text-xl font-semibold text-neutral-900">{control.name}</h1>
        </div>
        <StatusBadge status={control.status} />
      </div>

      <p className="mt-3 text-sm text-neutral-600">{control.description}</p>

      {whyFailing && (
        <div className="mt-5 rounded-lg border border-red-200 bg-red-50 p-4">
          <div className="text-sm font-semibold text-red-800">Why this control is failing</div>
          <p className="mt-1 text-sm text-red-700">{whyFailing}</p>
        </div>
      )}

      <div className="mt-6 grid grid-cols-2 gap-6 text-sm">
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-neutral-400">Objective</div>
          <div className="mt-1 text-neutral-700">{control.objective}</div>
        </div>
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-neutral-400">Testing frequency</div>
          <div className="mt-1 text-neutral-700">{control.testing_frequency}</div>
        </div>
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-neutral-400">Automation</div>
          <div className="mt-1 text-neutral-700">{control.automation_status}</div>
        </div>
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-neutral-400">Last tested</div>
          <div className="mt-1 text-neutral-700">{control.last_tested_at ? new Date(control.last_tested_at).toLocaleDateString() : "Never"}</div>
        </div>
      </div>

      {canEdit && (
        <div className="mt-6">
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-neutral-400">Change status</label>
          <div className="flex items-center gap-2">
            <select
              value={control.status}
              disabled={saving}
              onChange={(e) => handleStatusChange(e.target.value)}
              className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s.replaceAll("_", " ")}
                </option>
              ))}
            </select>
            {saving && <span className="text-xs text-neutral-400">Saving...</span>}
          </div>
          {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
        </div>
      )}

      <h2 className="mt-8 mb-3 text-sm font-semibold text-neutral-700">Mapped requirements</h2>
      <div className="divide-y divide-neutral-200 rounded-lg border border-neutral-200 bg-white">
        {control.requirements.map((req) => (
          <div key={req.requirement_id} className="px-4 py-3 text-sm">
            <span className="font-medium text-neutral-800">{req.framework_name}</span>
            <span className="text-neutral-400"> — {req.requirement_key} {req.requirement_name}</span>
          </div>
        ))}
        {control.requirements.length === 0 && (
          <div className="px-4 py-3 text-sm text-neutral-500">Not mapped to any framework requirement.</div>
        )}
      </div>

      <h2 className="mt-8 mb-3 text-sm font-semibold text-neutral-700">Evidence</h2>
      <div className="divide-y divide-neutral-200 rounded-lg border border-neutral-200 bg-white">
        {control.evidence.map((e) => (
          <Link
            key={e.id}
            href="/evidence"
            className="flex items-center justify-between px-4 py-3 text-sm hover:bg-neutral-50"
          >
            <span className="font-medium text-neutral-800">{e.name}</span>
            <StatusBadge status={e.status} />
          </Link>
        ))}
        {control.evidence.length === 0 && (
          <div className="px-4 py-3 text-sm text-neutral-500">No evidence attached — this is likely why the control is failing.</div>
        )}
      </div>
    </div>
  );
}

export default function ControlDetailPage() {
  return (
    <RequireAuth>
      <NavShell>
        <ControlDetailContent />
      </NavShell>
    </RequireAuth>
  );
}

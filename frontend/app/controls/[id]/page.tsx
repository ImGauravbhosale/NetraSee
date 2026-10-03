"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { RequireAuth, useAuth } from "@/lib/auth";
import { NavShell } from "@/components/NavShell";
import { StatusBadge } from "@/components/StatusBadge";
import { api, ApiError, AvailableCheck, ConnectionOut, ControlDetail } from "@/lib/api";

const STATUS_OPTIONS = ["PASS", "FAIL", "NEEDS_REVIEW", "NOT_APPLICABLE", "NOT_TESTED"] as const;

function AutomationPanel({
  control,
  orgId,
  onChanged,
}: {
  control: ControlDetail;
  orgId: string;
  onChanged: () => void;
}) {
  const [connections, setConnections] = useState<ConnectionOut[]>([]);
  const [checks, setChecks] = useState<AvailableCheck[]>([]);
  const [connectionId, setConnectionId] = useState("");
  const [checkKey, setCheckKey] = useState("");
  const [target, setTarget] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.get<ConnectionOut[]>(`/api/v1/orgs/${orgId}/connections`).then((list) => {
      setConnections(list);
      if (list.length > 0) setConnectionId(list[0].id);
    });
    api.get<AvailableCheck[]>(`/api/v1/orgs/${orgId}/connections/available-checks`).then((list) => {
      setChecks(list);
      if (list.length > 0) setCheckKey(list[0].key);
    });
  }, [orgId]);

  if (control.automation_connection_id) {
    const providerLabel = control.automation_check_key?.startsWith("aws.") ? "AWS" : "GitHub";
    const handleUnbind = async () => {
      setSubmitting(true);
      setError(null);
      try {
        await api.delete(`/api/v1/orgs/${orgId}/controls/${control.id}/automation`);
        onChanged();
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Could not unbind automation");
      } finally {
        setSubmitting(false);
      }
    };
    return (
      <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4 text-sm">
        <div className="font-semibold text-indigo-900">Automated by {providerLabel}</div>
        <p className="mt-1 text-indigo-800">
          Status is set by <span className="font-mono">{control.automation_check_key}</span> against{" "}
          <span className="font-mono">{control.automation_target}</span>. Re-sync from{" "}
          <Link href="/integrations" className="underline">Integrations</Link>.
        </p>
        <button
          onClick={handleUnbind}
          disabled={submitting}
          className="mt-3 rounded-md border border-indigo-300 bg-white px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 disabled:opacity-50"
        >
          {submitting ? "Unbinding..." : "Unbind — make manual again"}
        </button>
        {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
      </div>
    );
  }

  if (connections.length === 0) {
    return (
      <p className="text-sm text-neutral-500">
        No connections available —{" "}
        <Link href="/integrations" className="text-indigo-600 hover:text-indigo-500">connect GitHub or AWS</Link> first.
      </p>
    );
  }

  const handleBind = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.post(`/api/v1/orgs/${orgId}/controls/${control.id}/automation`, {
        connection_id: connectionId,
        check_key: checkKey,
        target,
      });
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not bind automation");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleBind} className="space-y-3 rounded-lg border border-neutral-200 bg-white p-4">
      {error && <div className="rounded-md bg-red-50 px-3 py-2 text-xs text-red-700">{error}</div>}
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-neutral-700">Connection</label>
          <select value={connectionId} onChange={(e) => setConnectionId(e.target.value)} className="w-full rounded-md border border-neutral-300 px-2 py-1.5 text-sm">
            {connections.map((c) => (
              <option key={c.id} value={c.id}>{c.provider === "GITHUB" ? "GitHub" : "AWS"} — {c.account_login}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-neutral-700">Check</label>
          <select value={checkKey} onChange={(e) => setCheckKey(e.target.value)} className="w-full rounded-md border border-neutral-300 px-2 py-1.5 text-sm">
            {checks.map((c) => (
              <option key={c.key} value={c.key}>{c.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-neutral-700">Target</label>
          <input
            required
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            placeholder="owner/repo or org"
            className="w-full rounded-md border border-neutral-300 px-2 py-1.5 text-sm font-mono"
          />
        </div>
      </div>
      <button type="submit" disabled={submitting} className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-50">
        {submitting ? "Binding..." : "Bind automation"}
      </button>
    </form>
  );
}

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
        : control.automation_connection_id
          ? control.evidence[control.evidence.length - 1].description
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

      {canEdit && !control.automation_connection_id && (
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

      {canEdit && (
        <div className="mt-6">
          <h2 className="mb-3 text-sm font-semibold text-neutral-700">Automation</h2>
          <AutomationPanel control={control} orgId={orgId!} onChanged={load} />
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
            className="flex items-center justify-between gap-4 px-4 py-3 text-sm hover:bg-neutral-50"
          >
            <div>
              <div className="font-medium text-neutral-800">{e.name}</div>
              {e.description && <div className="text-xs text-neutral-500">{e.description}</div>}
            </div>
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

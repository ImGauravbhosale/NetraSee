"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { RequireAuth, useAuth } from "@/lib/auth";
import { NavShell } from "@/components/NavShell";
import { StatusBadge } from "@/components/StatusBadge";
import { api, ControlListItem } from "@/lib/api";

const STATUS_OPTIONS = ["", "PASS", "FAIL", "NEEDS_REVIEW", "NOT_APPLICABLE", "NOT_TESTED"] as const;

function ControlsContent() {
  const { orgId } = useAuth();
  const searchParams = useSearchParams();
  const initialFilter = searchParams.get("status_filter") || "";
  const [statusFilter, setStatusFilter] = useState(initialFilter);
  const [controls, setControls] = useState<ControlListItem[] | null>(null);

  useEffect(() => {
    if (!orgId) return;
    setControls(null);
    const qs = statusFilter ? `?status_filter=${statusFilter}` : "";
    api.get<ControlListItem[]>(`/api/v1/orgs/${orgId}/controls${qs}`).then(setControls);
  }, [orgId, statusFilter]);

  return (
    <div className="mx-auto max-w-5xl p-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-neutral-900">Controls</h1>
          <p className="mt-1 text-sm text-neutral-500">Every control mapped to one or more frameworks.</p>
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s ? s.replaceAll("_", " ") : "All statuses"}
            </option>
          ))}
        </select>
      </div>

      {!controls ? (
        <div className="mt-8 text-sm text-neutral-500">Loading...</div>
      ) : (
        <div className="mt-6 overflow-hidden rounded-lg border border-neutral-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neutral-200 bg-neutral-50 text-left text-xs font-medium uppercase tracking-wide text-neutral-500">
                <th className="px-4 py-3">Control</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Automation</th>
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {controls.map((c) => (
                <tr key={c.id} className="hover:bg-neutral-50">
                  <td className="px-4 py-3">
                    <Link href={`/controls/${c.id}`} className="font-medium text-neutral-800 hover:text-indigo-600">
                      {c.control_key} — {c.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-neutral-500">{c.category}</td>
                  <td className="px-4 py-3 text-neutral-500">{c.automation_status}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={c.status} />
                  </td>
                </tr>
              ))}
              {controls.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-neutral-500">
                    No controls match this filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function ControlsPage() {
  return (
    <RequireAuth>
      <NavShell>
        <Suspense fallback={<div className="p-8 text-sm text-neutral-500">Loading...</div>}>
          <ControlsContent />
        </Suspense>
      </NavShell>
    </RequireAuth>
  );
}

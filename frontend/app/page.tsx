"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RequireAuth, useAuth } from "@/lib/auth";
import { NavShell } from "@/components/NavShell";
import { api, DashboardOut } from "@/lib/api";

function Stat({ label, value, tone }: { label: string; value: number; tone: "default" | "good" | "bad" | "warn" }) {
  const toneClass = {
    default: "text-neutral-900",
    good: "text-emerald-600",
    bad: "text-red-600",
    warn: "text-amber-600",
  }[tone];
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4">
      <div className={`text-2xl font-semibold ${toneClass}`}>{value}</div>
      <div className="mt-0.5 text-xs font-medium text-neutral-500">{label}</div>
    </div>
  );
}

function DashboardContent() {
  const { orgId } = useAuth();
  const [data, setData] = useState<DashboardOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!orgId) return;
    api
      .get<DashboardOut>(`/api/v1/orgs/${orgId}/dashboard`)
      .then(setData)
      .catch(() => setError("Could not load dashboard"));
  }, [orgId]);

  if (error) return <div className="p-8 text-sm text-red-600">{error}</div>;
  if (!data) return <div className="p-8 text-sm text-neutral-500">Loading...</div>;

  return (
    <div className="mx-auto max-w-5xl p-8">
      <h1 className="text-xl font-semibold text-neutral-900">Compliance Posture</h1>
      <p className="mt-1 text-sm text-neutral-500">Real-time, computed from your controls and evidence — not a snapshot from your last audit.</p>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        {data.frameworks.map((fw) => (
          <Link
            key={fw.framework_key}
            href={`/frameworks/${fw.framework_key}`}
            className="block rounded-lg border border-neutral-200 bg-white p-5 transition-shadow hover:shadow-sm"
          >
            <div className="mb-2 flex items-baseline justify-between">
              <span className="font-medium text-neutral-800">{fw.framework_name}</span>
              <span className="text-sm font-semibold text-neutral-700">{fw.progress_percent}%</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-neutral-100">
              <div
                className={`h-full rounded-full ${fw.progress_percent >= 80 ? "bg-emerald-500" : fw.progress_percent >= 50 ? "bg-amber-500" : "bg-red-500"}`}
                style={{ width: `${fw.progress_percent}%` }}
              />
            </div>
            <div className="mt-2 text-xs text-neutral-500">
              {fw.passing_count} of {fw.control_count} controls passing
            </div>
          </Link>
        ))}
        {data.frameworks.length === 0 && (
          <div className="rounded-lg border border-dashed border-neutral-300 p-5 text-sm text-neutral-500 sm:col-span-2">
            No frameworks adopted yet.
          </div>
        )}
      </div>

      <h2 className="mt-8 mb-3 text-sm font-semibold text-neutral-700">Controls</h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <Stat label="Passing" value={data.controls.passing} tone="good" />
        <Stat label="Failing" value={data.controls.failing} tone="bad" />
        <Stat label="Needs review" value={data.controls.needs_review} tone="warn" />
        <Stat label="Not applicable" value={data.controls.not_applicable} tone="default" />
        <Stat label="Not tested" value={data.controls.not_tested} tone="default" />
      </div>

      <h2 className="mt-8 mb-3 text-sm font-semibold text-neutral-700">Evidence</h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Valid" value={data.evidence.valid} tone="good" />
        <Stat label="Expiring soon" value={data.evidence.expiring} tone="warn" />
        <Stat label="Expired" value={data.evidence.expired} tone="bad" />
        <Stat label="Under review" value={data.evidence.under_review} tone="default" />
      </div>

      <div className="mt-8">
        <Link href="/controls?status_filter=FAIL" className="text-sm font-medium text-indigo-600 hover:text-indigo-500">
          See failing controls →
        </Link>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <RequireAuth>
      <NavShell>
        <DashboardContent />
      </NavShell>
    </RequireAuth>
  );
}

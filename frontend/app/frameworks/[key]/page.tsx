"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { RequireAuth, useAuth } from "@/lib/auth";
import { NavShell } from "@/components/NavShell";
import { ProgressBar } from "@/components/ProgressBar";
import { api, AdoptedFramework } from "@/lib/api";

function FrameworkDetailContent() {
  const { key } = useParams<{ key: string }>();
  const { orgId } = useAuth();
  const [framework, setFramework] = useState<AdoptedFramework | null | undefined>(undefined);

  useEffect(() => {
    if (!orgId) return;
    api.get<AdoptedFramework[]>(`/api/v1/orgs/${orgId}/frameworks`).then((all) => {
      setFramework(all.find((f) => f.framework.key === key) ?? null);
    });
  }, [orgId, key]);

  if (framework === undefined) return <div className="p-8 text-sm text-neutral-500">Loading...</div>;
  if (framework === null) return <div className="p-8 text-sm text-neutral-500">Framework not adopted.</div>;

  return (
    <div className="mx-auto max-w-4xl p-8">
      <Link href="/frameworks" className="text-xs font-medium text-neutral-400 hover:text-neutral-600">
        ← All frameworks
      </Link>
      <h1 className="mt-2 text-xl font-semibold text-neutral-900">{framework.framework.name}</h1>
      <p className="mt-1 text-sm text-neutral-500">{framework.framework.description}</p>

      <div className="mt-4 flex items-center gap-3">
        <div className="flex-1">
          <ProgressBar percent={framework.progress_percent} />
        </div>
        <span className="text-sm font-semibold text-neutral-700">{framework.progress_percent}%</span>
      </div>

      <h2 className="mt-8 mb-3 text-sm font-semibold text-neutral-700">Requirements</h2>
      <div className="divide-y divide-neutral-200 rounded-lg border border-neutral-200 bg-white">
        {framework.requirements.map((req) => (
          <div key={req.id} className="flex items-center justify-between px-5 py-4">
            <div>
              <div className="text-sm font-medium text-neutral-800">
                {req.key} — {req.name}
              </div>
              <div className="text-xs text-neutral-500">{req.description}</div>
            </div>
            <div className="flex-none text-right">
              <div className="text-sm font-semibold text-neutral-700">
                {req.passing_count}/{req.control_count}
              </div>
              <div className="text-xs text-neutral-400">controls passing</div>
            </div>
          </div>
        ))}
        {framework.requirements.length === 0 && (
          <div className="px-5 py-4 text-sm text-neutral-500">No requirements defined for this framework yet.</div>
        )}
      </div>

      <div className="mt-6">
        <Link href="/controls" className="text-sm font-medium text-indigo-600 hover:text-indigo-500">
          View all controls →
        </Link>
      </div>
    </div>
  );
}

export default function FrameworkDetailPage() {
  return (
    <RequireAuth>
      <NavShell>
        <FrameworkDetailContent />
      </NavShell>
    </RequireAuth>
  );
}

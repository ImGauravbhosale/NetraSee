"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RequireAuth, useAuth } from "@/lib/auth";
import { NavShell } from "@/components/NavShell";
import { ProgressBar } from "@/components/ProgressBar";
import { api, AdoptedFramework } from "@/lib/api";

function FrameworksContent() {
  const { orgId } = useAuth();
  const [frameworks, setFrameworks] = useState<AdoptedFramework[] | null>(null);

  useEffect(() => {
    if (!orgId) return;
    api.get<AdoptedFramework[]>(`/api/v1/orgs/${orgId}/frameworks`).then(setFrameworks);
  }, [orgId]);

  if (!frameworks) return <div className="p-8 text-sm text-neutral-500">Loading...</div>;

  return (
    <div className="mx-auto max-w-4xl p-8">
      <h1 className="text-xl font-semibold text-neutral-900">Frameworks</h1>
      <p className="mt-1 text-sm text-neutral-500">Adopted compliance frameworks and their current progress.</p>

      <div className="mt-6 space-y-3">
        {frameworks.map((fw) => (
          <Link
            key={fw.framework.key}
            href={`/frameworks/${fw.framework.key}`}
            className="block rounded-lg border border-neutral-200 bg-white p-5 hover:shadow-sm"
          >
            <div className="mb-2 flex items-baseline justify-between">
              <div>
                <div className="font-medium text-neutral-800">{fw.framework.name}</div>
                <div className="text-xs text-neutral-500">{fw.framework.description}</div>
              </div>
              <span className="text-sm font-semibold text-neutral-700">{fw.progress_percent}%</span>
            </div>
            <ProgressBar percent={fw.progress_percent} />
          </Link>
        ))}
        {frameworks.length === 0 && (
          <div className="rounded-lg border border-dashed border-neutral-300 p-5 text-sm text-neutral-500">
            No frameworks adopted yet.
          </div>
        )}
      </div>
    </div>
  );
}

export default function FrameworksPage() {
  return (
    <RequireAuth>
      <NavShell>
        <FrameworksContent />
      </NavShell>
    </RequireAuth>
  );
}

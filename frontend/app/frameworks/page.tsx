"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { RequireAuth, useAuth } from "@/lib/auth";
import { NavShell } from "@/components/NavShell";
import { ProgressBar } from "@/components/ProgressBar";
import { api, AdoptedFramework, ApiError, FrameworkOut } from "@/lib/api";

function AdoptFrameworkPanel({
  orgId,
  adoptedKeys,
  onAdopted,
}: {
  orgId: string;
  adoptedKeys: Set<string>;
  onAdopted: () => void;
}) {
  const [catalog, setCatalog] = useState<FrameworkOut[] | null>(null);
  const [adopting, setAdopting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<FrameworkOut[]>("/api/v1/frameworks").then(setCatalog);
  }, []);

  const available = (catalog ?? []).filter((f) => !adoptedKeys.has(f.key));

  const handleAdopt = async (framework: FrameworkOut) => {
    setAdopting(framework.id);
    setError(null);
    try {
      await api.post(`/api/v1/orgs/${orgId}/frameworks/${framework.id}/adopt`);
      onAdopted();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `Could not adopt ${framework.name}`);
    } finally {
      setAdopting(null);
    }
  };

  if (catalog === null) return null;
  if (available.length === 0) return null;

  return (
    <div className="mt-8">
      <h2 className="mb-3 text-sm font-semibold text-neutral-700">Adopt a framework</h2>
      {error && <div className="mb-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {available.map((f) => (
          <div key={f.id} className="flex items-start justify-between gap-3 rounded-lg border border-dashed border-neutral-300 p-4">
            <div>
              <div className="text-sm font-medium text-neutral-800">{f.name}</div>
              <div className="text-xs text-neutral-500">{f.description}</div>
            </div>
            <button
              onClick={() => handleAdopt(f)}
              disabled={adopting === f.id}
              className="flex-none rounded-md border border-neutral-300 px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-50 disabled:opacity-50"
            >
              {adopting === f.id ? "Adopting..." : "Adopt"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

function FrameworksContent() {
  const { orgId, me } = useAuth();
  const [frameworks, setFrameworks] = useState<AdoptedFramework[] | null>(null);

  const role = me?.memberships.find((m) => m.organization_id === orgId)?.role;
  const canAdopt = role === "OWNER" || role === "ADMIN";

  const load = useCallback(() => {
    if (!orgId) return;
    api.get<AdoptedFramework[]>(`/api/v1/orgs/${orgId}/frameworks`).then(setFrameworks);
  }, [orgId]);

  useEffect(load, [load]);

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

      {canAdopt && (
        <AdoptFrameworkPanel
          orgId={orgId!}
          adoptedKeys={new Set(frameworks.map((f) => f.framework.key))}
          onAdopted={load}
        />
      )}
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

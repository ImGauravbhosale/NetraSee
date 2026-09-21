"use client";

import { useCallback, useEffect, useState } from "react";
import { RequireAuth, useAuth } from "@/lib/auth";
import { NavShell } from "@/components/NavShell";
import { StatusBadge } from "@/components/StatusBadge";
import { api, ApiError, ControlListItem, EvidenceOut } from "@/lib/api";

function UploadForm({ orgId, controls, onUploaded }: { orgId: string; controls: ControlListItem[]; onUploaded: () => void }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [selectedControls, setSelectedControls] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [open, setOpen] = useState(false);

  const toggleControl = (id: string) => {
    setSelectedControls((prev) => (prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Choose a file");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("name", name);
      formData.append("description", description);
      if (expiresAt) formData.append("expires_at", new Date(expiresAt).toISOString());
      formData.append("control_ids", JSON.stringify(selectedControls));
      formData.append("file", file);
      await api.postForm(`/api/v1/orgs/${orgId}/evidence`, formData);
      setName("");
      setDescription("");
      setExpiresAt("");
      setFile(null);
      setSelectedControls([]);
      setOpen(false);
      onUploaded();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-500"
      >
        Upload evidence
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
          <label className="mb-1 block text-xs font-medium text-neutral-700">Expires</label>
          <input type="date" value={expiresAt} onChange={(e) => setExpiresAt(e.target.value)} className="w-full rounded-md border border-neutral-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500" />
        </div>
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-neutral-700">Description</label>
        <input value={description} onChange={(e) => setDescription(e.target.value)} className="w-full rounded-md border border-neutral-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500" />
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-neutral-700">File (pdf, png, jpg, txt, json, csv, zip)</label>
        <input
          type="file"
          required
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="w-full text-sm text-neutral-600"
        />
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-neutral-700">Link to controls</label>
        <div className="max-h-32 space-y-1 overflow-y-auto rounded-md border border-neutral-200 p-2">
          {controls.map((c) => (
            <label key={c.id} className="flex items-center gap-2 text-sm text-neutral-700">
              <input type="checkbox" checked={selectedControls.includes(c.id)} onChange={() => toggleControl(c.id)} />
              {c.control_key} — {c.name}
            </label>
          ))}
        </div>
      </div>
      <div className="flex gap-2">
        <button type="submit" disabled={submitting} className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50">
          {submitting ? "Uploading..." : "Upload"}
        </button>
        <button type="button" onClick={() => setOpen(false)} className="rounded-md px-3 py-2 text-sm font-medium text-neutral-500 hover:text-neutral-800">
          Cancel
        </button>
      </div>
    </form>
  );
}

function EvidenceContent() {
  const { orgId, me } = useAuth();
  const [evidence, setEvidence] = useState<EvidenceOut[] | null>(null);
  const [controls, setControls] = useState<ControlListItem[]>([]);

  const role = me?.memberships.find((m) => m.organization_id === orgId)?.role;
  const canManage = role === "OWNER" || role === "ADMIN";

  const load = useCallback(() => {
    if (!orgId) return;
    api.get<EvidenceOut[]>(`/api/v1/orgs/${orgId}/evidence`).then(setEvidence);
    api.get<ControlListItem[]>(`/api/v1/orgs/${orgId}/controls`).then(setControls);
  }, [orgId]);

  useEffect(load, [load]);

  const handleDelete = async (id: string) => {
    if (!orgId) return;
    await api.delete(`/api/v1/orgs/${orgId}/evidence/${id}`);
    load();
  };

  return (
    <div className="mx-auto max-w-4xl p-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-neutral-900">Evidence</h1>
          <p className="mt-1 text-sm text-neutral-500">Documents proving your controls are actually working.</p>
        </div>
        {canManage && <UploadForm orgId={orgId!} controls={controls} onUploaded={load} />}
      </div>

      {!evidence ? (
        <div className="mt-8 text-sm text-neutral-500">Loading...</div>
      ) : (
        <div className="mt-6 divide-y divide-neutral-200 rounded-lg border border-neutral-200 bg-white">
          {evidence.map((e) => (
            <div key={e.id} className="flex items-start justify-between gap-4 px-5 py-4">
              <div>
                <div className="text-sm font-medium text-neutral-800">{e.name}</div>
                <div className="text-xs text-neutral-500">{e.description || "No description"}</div>
                <div className="mt-1 text-xs text-neutral-400">
                  {e.controls.length > 0
                    ? `Linked to ${e.controls.map((c) => c.control_key).join(", ")}`
                    : "Not linked to any control"}
                  {e.expires_at && ` · expires ${new Date(e.expires_at).toLocaleDateString()}`}
                </div>
              </div>
              <div className="flex flex-none items-center gap-3">
                <StatusBadge status={e.status} />
                {canManage && (
                  <button onClick={() => handleDelete(e.id)} className="text-xs font-medium text-red-500 hover:text-red-700">
                    Delete
                  </button>
                )}
              </div>
            </div>
          ))}
          {evidence.length === 0 && <div className="px-5 py-6 text-center text-sm text-neutral-500">No evidence uploaded yet.</div>}
        </div>
      )}
    </div>
  );
}

export default function EvidencePage() {
  return (
    <RequireAuth>
      <NavShell>
        <EvidenceContent />
      </NavShell>
    </RequireAuth>
  );
}

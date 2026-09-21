"use client";

import { RequireAuth } from "@/lib/auth";
import { NavShell, ComingSoon } from "@/components/NavShell";

export default function AuditsPage() {
  return (
    <RequireAuth>
      <NavShell>
        <ComingSoon title="Audit Center" />
      </NavShell>
    </RequireAuth>
  );
}

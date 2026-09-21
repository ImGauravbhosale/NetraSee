"use client";

import { RequireAuth } from "@/lib/auth";
import { NavShell, ComingSoon } from "@/components/NavShell";

export default function IntegrationsPage() {
  return (
    <RequireAuth>
      <NavShell>
        <ComingSoon title="Integrations" />
      </NavShell>
    </RequireAuth>
  );
}

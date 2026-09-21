"use client";

import { RequireAuth } from "@/lib/auth";
import { NavShell, ComingSoon } from "@/components/NavShell";

export default function PoliciesPage() {
  return (
    <RequireAuth>
      <NavShell>
        <ComingSoon title="Policies" />
      </NavShell>
    </RequireAuth>
  );
}

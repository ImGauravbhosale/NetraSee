"use client";

import { RequireAuth } from "@/lib/auth";
import { NavShell, ComingSoon } from "@/components/NavShell";

export default function RisksPage() {
  return (
    <RequireAuth>
      <NavShell>
        <ComingSoon title="Risks" />
      </NavShell>
    </RequireAuth>
  );
}

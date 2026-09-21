"use client";

import { RequireAuth } from "@/lib/auth";
import { NavShell, ComingSoon } from "@/components/NavShell";

export default function ReportsPage() {
  return (
    <RequireAuth>
      <NavShell>
        <ComingSoon title="Reports" />
      </NavShell>
    </RequireAuth>
  );
}

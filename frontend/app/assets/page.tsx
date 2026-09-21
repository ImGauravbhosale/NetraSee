"use client";

import { RequireAuth } from "@/lib/auth";
import { NavShell, ComingSoon } from "@/components/NavShell";

export default function AssetsPage() {
  return (
    <RequireAuth>
      <NavShell>
        <ComingSoon title="Assets" />
      </NavShell>
    </RequireAuth>
  );
}

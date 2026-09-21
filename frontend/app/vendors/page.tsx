"use client";

import { RequireAuth } from "@/lib/auth";
import { NavShell, ComingSoon } from "@/components/NavShell";

export default function VendorsPage() {
  return (
    <RequireAuth>
      <NavShell>
        <ComingSoon title="Vendors" />
      </NavShell>
    </RequireAuth>
  );
}

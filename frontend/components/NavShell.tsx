"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", built: true },
  { href: "/frameworks", label: "Frameworks", built: true },
  { href: "/controls", label: "Controls", built: true },
  { href: "/evidence", label: "Evidence", built: true },
  { href: "/activity", label: "Activity Log", built: true },
  { href: "/policies", label: "Policies", built: false },
  { href: "/risks", label: "Risks", built: false },
  { href: "/assets", label: "Assets", built: false },
  { href: "/vendors", label: "Vendors", built: false },
  { href: "/integrations", label: "Integrations", built: false },
  { href: "/audits", label: "Audit Center", built: false },
  { href: "/reports", label: "Reports", built: false },
  { href: "/settings", label: "Settings", built: true },
];

export function NavShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { me, orgId } = useAuth();

  const handleLogout = async () => {
    await api.post("/api/v1/auth/logout");
    router.replace("/login");
  };

  return (
    <div className="flex min-h-screen bg-neutral-50">
      <aside className="flex w-60 flex-none flex-col border-r border-neutral-200 bg-white">
        <div className="flex items-center gap-2 px-5 py-5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-indigo-600 text-sm font-bold text-white">
            N
          </div>
          <span className="text-[15px] font-semibold tracking-tight text-neutral-900">NetraSee</span>
        </div>
        <nav className="flex-1 space-y-0.5 px-3">
          {NAV_ITEMS.map((item) => {
            const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center justify-between rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  active ? "bg-indigo-50 text-indigo-700" : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900"
                }`}
              >
                <span>{item.label}</span>
                {!item.built && <span className="text-[10px] font-normal text-neutral-400">soon</span>}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-neutral-200 px-4 py-3">
          <div className="truncate text-xs text-neutral-500">{me?.memberships.find((m) => m.organization_id === orgId)?.organization_name}</div>
          <div className="truncate text-sm font-medium text-neutral-800">{me?.user.email}</div>
          <button onClick={handleLogout} className="mt-2 text-xs font-medium text-neutral-500 hover:text-neutral-800">
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}

export function ComingSoon({ title }: { title: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center p-16 text-center">
      <div className="mb-3 text-lg font-semibold text-neutral-800">{title}</div>
      <p className="max-w-md text-sm text-neutral-500">
        Not built yet in this v1 — see the README roadmap. Dashboard, Frameworks, Controls, Evidence, Activity Log,
        and Settings are real and backed by the live API.
      </p>
    </div>
  );
}

const STYLES: Record<string, string> = {
  PASS: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  VALID: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  FAIL: "bg-red-50 text-red-700 ring-red-600/20",
  EXPIRED: "bg-red-50 text-red-700 ring-red-600/20",
  NEEDS_REVIEW: "bg-amber-50 text-amber-700 ring-amber-600/20",
  EXPIRING: "bg-amber-50 text-amber-700 ring-amber-600/20",
  NOT_TESTED: "bg-neutral-100 text-neutral-600 ring-neutral-500/20",
  NOT_APPLICABLE: "bg-neutral-100 text-neutral-500 ring-neutral-500/20",
  UNDER_REVIEW: "bg-sky-50 text-sky-700 ring-sky-600/20",
};

export function StatusBadge({ status }: { status: string }) {
  const style = STYLES[status] || "bg-neutral-100 text-neutral-600 ring-neutral-500/20";
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${style}`}>
      {status.replaceAll("_", " ")}
    </span>
  );
}

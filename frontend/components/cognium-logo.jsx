import { cn } from "@/lib/utils";

export function CogniumLogo({ className }) {
  return (
    <svg viewBox="0 0 28 28" className={cn("size-7", className)} aria-hidden="true">
      <rect width="28" height="28" rx="6" fill="#000000" />
      <path
        d="M18.95 9.05 A7 7 0 1 0 18.95 18.95"
        stroke="#FFFFFF"
        strokeWidth="4.5"
        fill="none"
        strokeLinecap="round"
      />
    </svg>
  );
}

import { Check } from "lucide-react";
import { sections } from "@/constants/constants";
import { CogniumLogo } from "@/components/cognium-logo";
import { cn } from "@/lib/utils";

export function AssessmentSidebar({ current }) {
  return (
    <aside className="flex flex-none flex-col gap-7 bg-[#15211E] px-5 py-5 text-[#E9EEEB] lg:w-[260px] lg:py-7">
      <div className="flex items-center gap-2.5 px-2 text-lg font-extrabold text-white">
        <CogniumLogo />
        Cognium
      </div>

      <nav aria-label="Assessment steps" className="hidden lg:block">
        <ol className="flex flex-col gap-1">
          {sections.map(([title, sub], i) => (
            <li
              key={title}
              aria-current={i === current ? "step" : undefined}
              className={cn(
                "flex min-h-11 items-center gap-3 rounded-[10px] px-3 text-sm font-semibold",
                i === current
                  ? "bg-[#2A3F38] font-bold text-white"
                  : "text-[#9AABA5]",
                i < current && "text-[#C8D3CF]",
              )}
            >
              {i < current ? (
                <span className="flex size-5 items-center justify-center rounded-full bg-[#2E7D68]">
                  <Check className="size-3 text-white" strokeWidth={3} />
                </span>
              ) : (
                <span
                  className={cn(
                    "flex size-5 items-center justify-center rounded-full border-2",
                    i === current ? "border-[#9FD3C3]" : "border-[#4A5D57]",
                  )}
                >
                  {i === current && (
                    <span className="size-2 rounded-full bg-[#9FD3C3]" />
                  )}
                </span>
              )}
              <span className="flex flex-col">
                {title}
                {sub && (
                  <span
                    className={cn(
                      "text-xs font-medium",
                      i === current && "text-[#9FD3C3]",
                    )}
                  >
                    {sub}
                  </span>
                )}
              </span>
            </li>
          ))}
        </ol>
      </nav>

      <p className="mx-2 mt-auto hidden text-xs leading-relaxed text-[#9AABA5] lg:block">
        Practice exercise · not investment advice
      </p>
    </aside>
  );
}

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AssessmentSidebar } from "@/components/assessment-sidebar";
import { Button } from "@/components/ui/button";
import {
  capLabels,
  levels,
  reasonLabels,
  USER_ID_KEY,
} from "@/constants/constants";
import { createRecommendation, getAssessmentResult } from "@/lib/api";
import { cn } from "@/lib/utils";

const scoreColors = ["bg-primary", "bg-[#C2620F]"];

// Each reason is { <field>: <answer code>, points }
const reasonText = ({ points, ...answer }) => {
  const [field, value] = Object.entries(answer)[0];
  return field === "age"
    ? `Age ${value}`
    : (reasonLabels[field]?.[value] ?? `${field}: ${value}`);
};

const recordOf = ({ record }) => [
  ["Assessment", record.assessment.slice(0, 8)],
  [
    "Submitted",
    new Date(record.submitted_at).toLocaleString("en-GB", {
      dateStyle: "medium",
      timeStyle: "short",
    }),
  ],

  ["Scoring rules", `v${record.scoring_rules}`],
];

const card = "flex flex-col gap-3 rounded-2xl border bg-card p-6";

export default function Scoring() {
  const [userId, setUserId] = useState(null);
  useEffect(() => setUserId(localStorage.getItem(USER_ID_KEY)), []);

  const { data: result, isPending } = useQuery({
    queryKey: ["assessment-result", userId],
    queryFn: () => getAssessmentResult(userId),
    enabled: !!userId,
  });

  const router = useRouter();
  const queryClient = useQueryClient();
  const { mutate: buildPortfolio, isPending: isBuilding } = useMutation({
    // Builds (or returns the already locked) portfolio, then hands it to the next page
    mutationFn: () => createRecommendation(userId),
    onSuccess: (data) => {
      queryClient.setQueryData(["recommendation", userId], data);
      router.push("/risk-assessment/recommendations");
    },
  });

  return (
    <div className="flex min-h-dvh flex-col lg:h-dvh lg:flex-row lg:overflow-hidden">
      <AssessmentSidebar current={4} />

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b bg-card px-4 py-5 sm:px-12 sm:py-6">
          <div className="flex flex-col gap-1">
            <span className="text-[13px] font-bold tracking-[0.08em] text-primary uppercase">
              Assessment result
            </span>
            <h1 className="text-2xl font-extrabold sm:text-[28px]">
              Your risk profile
            </h1>
          </div>
          <span className="font-mono text-sm text-muted-foreground">
            Step 5 of 6
          </span>
        </header>

        {!result ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 px-4 py-16 text-center text-muted-foreground">
            {userId && isPending ? (
              <Loader2 className="size-8 animate-spin text-primary" />
            ) : (
              <p className="text-base">
                No assessment result found. Complete the assessment to see your
                profile.
              </p>
            )}
          </div>
        ) : (
          <div className="flex flex-1 flex-col gap-6 px-4 py-6 sm:px-12 sm:py-8 lg:overflow-y-auto">
            <section className="flex flex-col gap-[22px] rounded-[20px] border bg-card p-5 sm:p-8">
              <div className="flex flex-col gap-2.5">
                <p className="text-[15px] text-muted-foreground">
                  {result.user_id}, your profile is
                </p>
                <h2 className="text-3xl font-extrabold tracking-[-0.02em] sm:text-[40px]">
                  {result.label}
                </h2>
              </div>

              <div
                role="img"
                aria-label={`Five-step risk scale. Your profile is step ${result.level} of 5, ${result.label.toLowerCase()}.`}
                className="flex flex-col gap-2.5"
              >
                <div className="grid grid-cols-5 gap-1.5">
                  {levels.map((l, i) => (
                    <span
                      key={l}
                      className={cn(
                        "h-3.5 rounded-[3px] bg-[#E6EAE7] first:rounded-l-[7px] last:rounded-r-[7px]",
                        i < result.level - 1 && "bg-[#C5D9D2]",
                        i === result.level - 1 &&
                          "bg-primary outline-3 outline-[#E3EEEA]",
                      )}
                    />
                  ))}
                </div>
                <div className="hidden grid-cols-5 gap-1.5 text-[13px] text-muted-foreground sm:grid">
                  {levels.map((l, i) => (
                    <span
                      key={l}
                      className={cn(
                        i === result.level - 1 &&
                          "font-extrabold text-[#133F34]",
                      )}
                    >
                      {l}
                    </span>
                  ))}
                </div>
              </div>
            </section>

            <section
              className={cn(
                "grid gap-4",
                result.level === 5 ? "lg:grid-cols-2" : "lg:grid-cols-3",
              )}
            >
              {result.scores.map((s, i) => (
                <div key={s.title} className={card}>
                  <span className="text-sm font-bold text-muted-foreground">
                    {s.title}
                  </span>
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-[22px] font-extrabold">
                      {s.label}
                    </span>
                    <span className="font-mono text-[15px] font-medium whitespace-nowrap text-muted-foreground">
                      {s.score} / 100
                    </span>
                  </div>
                  <div className="h-2 rounded bg-[#E6EAE7]">
                    <div
                      className={cn("h-2 rounded", scoreColors[i])}
                      style={{ width: `${s.score}%` }}
                    />
                  </div>
                  <ul className="list-disc pl-[18px] text-sm leading-[1.7] text-[#3C4945]">
                    {s.reasons.map((r) => (
                      <li key={reasonText(r)}>{reasonText(r)}</li>
                    ))}
                  </ul>
                </div>
              ))}

              {result.level !== 5 && (
                <div
                  className={cn(
                    card,
                    "border-2 border-primary bg-[#E3EEEA] p-[23px] text-[#133F34]",
                  )}
                >
                  <span className="text-sm font-bold">What decided it</span>
                  <span className="text-[22px] font-extrabold">
                    {result.caps.length
                      ? "A limit from your answers"
                      : "The more cautious side"}
                  </span>
                  <p className="text-sm leading-relaxed">
                    {result.caps.length
                      ? `We capped your profile for the safest investment according to your input. This keeps you at ${result.label}.`
                      : "We never go above either score, and we choose most cautious profile for your investment"}
                  </p>
                  {result.caps.map((id) => (
                    <p
                      key={id}
                      className="rounded-[10px] bg-white px-3 py-2.5 text-sm leading-relaxed"
                    >
                      <strong>Ceiling applied:</strong> {capLabels[id] ?? id}
                    </p>
                  ))}
                </div>
              )}
            </section>

            <section
              aria-label="Assessment record"
              className="flex flex-wrap items-center justify-between gap-6 rounded-2xl bg-[#15211E] px-6 py-5 text-[#E9EEEB]"
            >
              <span className="font-bold">Locked record</span>
              <dl className="flex flex-wrap gap-7 font-mono text-[13px]">
                {recordOf(result).map(([k, v]) => (
                  <div key={k}>
                    <dt className="text-[#9AABA5]">{k}</dt>
                    <dd>{v}</dd>
                  </div>
                ))}
              </dl>
            </section>
          </div>
        )}

        <footer className="sticky bottom-0 flex items-center justify-between gap-3 border-t bg-card px-4 py-4 sm:px-12 sm:py-5">
          <Button
            asChild
            variant="outline"
            className="h-12 rounded-xl bg-white px-[22px] text-base font-semibold"
          >
            <Link href="/risk-assessment/section1">
              <span className="sm:hidden">Start again</span>
              <span className="hidden sm:inline">Start a new assessment</span>
            </Link>
          </Button>
          {result && (
            <Button
              onClick={() => buildPortfolio()}
              disabled={isBuilding}
              className="h-12 rounded-xl px-7 text-base font-bold"
            >
              {isBuilding && <Loader2 className="animate-spin" />}
              See my portfolio
            </Button>
          )}
        </footer>
      </main>
    </div>
  );
}

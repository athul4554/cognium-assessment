"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { TOLERANCE_KEY, USER_ID_KEY } from "@/constants/constants";
import { getRiskAssessment } from "@/lib/api";
import { cn } from "@/lib/utils";

const choice = z.string().min(1, "Pick one");

const schema = z.object({
  portfolio: choice,
  drop: choice,
  maxLoss: choice,
  goal: choice,
  experience: choice,
});

const portfolios = [
  ["A", "20/80", 5, 19, 23, 42],
  ["B", "60/40", 10, 22, 47, 48],
  ["C", "90/10", 15, 32, 70, 70],
];

const questions = [
  [
    "drop",
    "A bad stretch",
    <>
      Over three months your <span className="font-mono">$50,000</span> falls to{" "}
      <span className="font-mono">$40,000</span>. What do you do?
    </>,
    [
      ["sell_all", "Sell everything"],
      ["sell_some", "Sell some"],
      ["hold", "Hold and wait"],
      ["buy_more", "Buy more"],
    ],
  ],
  [
    "maxLoss",
    "Your limit",
    "The most you could lose in one year and stay invested?",
    [
      ["0", "Nothing"],
      ["5", "5%", "−$2,500"],
      ["15", "15%", "−$7,500"],
      ["30_plus", "30%+", "−$15,000"],
    ],
  ],
  [
    "goal",
    "Your goal",
    "What matters most for this money?",
    [
      ["capital_preservation", "Keep it safe"],
      ["income", "Regular income"],
      ["balanced_growth", "Steady growth"],
      ["aggressive_growth", "Maximum growth"],
    ],
  ],
  [
    "experience",
    "Experience",
    "What have you invested in before?",
    [
      ["none", "Nothing yet"],
      ["funds_only", "Funds"],
      ["stocks_etfs", "Stocks and ETFs"],
      ["derivatives_leverage", "Derivatives / leverage"],
    ],
  ],
];

// Form values <-> API "tolerance" payload
const toTolerance = ({ maxLoss, ...rest }) => ({ ...rest, max_loss: maxLoss });
const fromTolerance = ({ max_loss, ...rest }) => ({
  ...rest,
  maxLoss: max_loss,
});

const fieldset =
  "flex min-w-0 flex-col gap-3 rounded-2xl border bg-card p-5 sm:p-6";
const legend =
  "px-2 text-[13px] font-extrabold tracking-[0.08em] text-primary uppercase";
const selected =
  "border-2 border-primary bg-[#E3EEEA] font-bold text-[#133F34]";
const error = (err) =>
  err && <span className="text-[13px] text-destructive">{err.message}</span>;

export function RiskToleranceForm() {
  const router = useRouter();
  const [userId, setUserId] = useState(null);
  const {
    control,
    watch,
    reset,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
    mode: "onChange",
    defaultValues: {
      portfolio: "",
      drop: "",
      maxLoss: "",
      goal: "",
      experience: "",
    },
  });

  // Prefer this session's unsent answers, otherwise prefill from the last submission
  useEffect(() => {
    const draft = sessionStorage.getItem(TOLERANCE_KEY);
    if (draft) reset(fromTolerance(JSON.parse(draft)));
    else setUserId(localStorage.getItem(USER_ID_KEY));
  }, [reset]);

  const { data, isFetching } = useQuery({
    queryKey: ["risk-assessment", userId],
    queryFn: () => getRiskAssessment(userId),
    enabled: !!userId,
  });

  useEffect(() => {
    if (data) reset(fromTolerance(data.tolerance));
  }, [data, reset]);

  const values = watch();
  const picked = portfolios.find(([name]) => name === values.portfolio);
  // The $50,000 → $40,000 question is a 20% fall
  const conflict = picked && picked[3] > 20 && values.drop === "sell_all";

  // Saved until Section C, which submits the whole assessment in one request
  const onSubmit = (data) => {
    sessionStorage.setItem(TOLERANCE_KEY, JSON.stringify(toTolerance(data)));
    router.push("/risk-assessment/section3");
  };

  const portfolioGroup = (
    <Controller
      name="portfolio"
      control={control}
      render={({ field }) => (
        <div
          role="radiogroup"
          aria-label="Portfolio preference"
          className="grid gap-4 md:grid-cols-3"
        >
          {portfolios.map(([name, mix, gain, fall, gainBar, fallBar]) => (
            <button
              key={name}
              type="button"
              role="radio"
              aria-checked={field.value === name}
              onClick={() => field.onChange(name)}
              className={cn(
                "flex flex-col gap-3 rounded-[14px] border border-input bg-white p-5 text-left transition-colors hover:border-ring",
                field.value === name && selected,
              )}
            >
              <span className="flex justify-between">
                <span className="text-[19px] font-extrabold">
                  Portfolio {name}
                </span>
                <span className="text-[13px] font-normal text-muted-foreground">
                  {mix}
                </span>
              </span>
              <span className="flex flex-col gap-1.5 text-[13px] font-normal text-muted-foreground">
                Average gain a year
                <span className="flex items-center gap-2.5">
                  <span
                    className="h-2.5 rounded-[3px] bg-primary"
                    style={{ width: `${gainBar}%` }}
                  />
                  <span className="font-mono text-[15px] font-medium text-foreground">
                    +{gain}%
                  </span>
                </span>
                <span className="mt-1">Worst fall from a peak</span>
                <span className="flex items-center gap-2.5">
                  <span
                    className="h-2.5 rounded-[3px] bg-[#C2620F]"
                    style={{ width: `${fallBar}%` }}
                  />
                  <span className="font-mono text-[15px] font-medium text-foreground">
                    −{fall}%
                  </span>
                </span>
              </span>
            </button>
          ))}
        </div>
      )}
    />
  );

  const choiceGroup = ([name, title, question, options]) => (
    <fieldset key={name} className={fieldset}>
      <legend className={legend}>{title}</legend>
      <p id={name} className="text-[15px] leading-snug font-bold">
        {question}
      </p>
      <Controller
        name={name}
        control={control}
        render={({ field }) => (
          <div
            role="radiogroup"
            aria-labelledby={name}
            className="grid grid-cols-2 gap-2"
          >
            {options.map(([value, text, extra]) => (
              <button
                key={value}
                type="button"
                role="radio"
                aria-checked={field.value === value}
                onClick={() => field.onChange(value)}
                className={cn(
                  "min-h-12 rounded-[10px] border border-input bg-white px-2 text-sm font-semibold transition-colors hover:border-ring",
                  field.value === value && selected,
                )}
              >
                {text}
                {extra && (
                  <span
                    className={cn(
                      "ml-1 font-mono",
                      field.value !== value && "text-muted-foreground",
                    )}
                  >
                    {extra}
                  </span>
                )}
              </button>
            ))}
          </div>
        )}
      />
      {error(errors[name])}
    </fieldset>
  );

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      noValidate
      className="flex min-h-0 flex-1 flex-col"
    >
      <div className="flex flex-1 flex-col gap-6 px-4 py-6 sm:px-12 sm:py-8 lg:overflow-y-auto">
        <p className="text-base leading-relaxed text-[#3C4945]">
          There are no right answers. We're asking how you'd actually feel,
          which matters as much as what you can afford.
        </p>

        <fieldset className={cn(fieldset, "gap-3.5 sm:p-7")}>
          <legend className={legend}>Which of these would you pick?</legend>
          <p className="text-[15px] leading-relaxed text-[#3C4945]">
            Three real stock and bond mixes over the last ten years, rebalanced
            yearly. <strong>This is what happened, not a forecast.</strong>
          </p>
          {portfolioGroup}
          {error(errors.portfolio)}
        </fieldset>

        <div className="grid gap-5 md:grid-cols-2">
          {questions.map(choiceGroup)}
        </div>

        {conflict && (
          <div
            role="status"
            className="flex items-start gap-3 rounded-xl border border-[#EBCFAE] bg-[#FBF0E2] px-[18px] py-4 text-[15px] leading-relaxed text-[#5C2F07]"
          >
            <svg
              viewBox="0 0 20 20"
              className="mt-0.5 size-5 flex-none"
              aria-hidden="true"
            >
              <circle
                cx="10"
                cy="10"
                r="8.5"
                stroke="#9A520F"
                strokeWidth="1.8"
                fill="none"
              />
              <path
                d="M10 9v5M10 6v.5"
                stroke="#9A520F"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
            </svg>
            <span>
              You picked Portfolio {picked[0]}, but said you'd sell everything
              after a 20% fall. {picked[0]} fell {picked[3]}% at its worst.
              That's fine to keep. We'll follow your more cautious answer.
            </span>
          </div>
        )}
      </div>

      <footer className="sticky bottom-0 flex items-center justify-between gap-3 border-t bg-card px-4 py-4 sm:px-12 sm:py-5">
        <Button
          asChild
          variant="outline"
          className="h-12 rounded-xl bg-white px-[22px] text-base font-semibold"
        >
          <Link href="/risk-assessment/section1">Back</Link>
        </Button>
        <Button
          type="submit"
          disabled={isFetching}
          className="h-12 rounded-xl px-7 text-base font-bold"
        >
          {isFetching && <Loader2 className="animate-spin" />}
          Continue<span className="hidden sm:inline">&nbsp;to Section C</span>
        </Button>
      </footer>
    </form>
  );
}

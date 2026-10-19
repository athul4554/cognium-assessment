"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CAPACITY_KEY, currencies, USER_ID_KEY } from "@/constants/constants";
import { getRiskAssessment } from "@/lib/api";
import { cn } from "@/lib/utils";

const thisYear = new Date().getFullYear();

const FX_NOTE =
  "All the funds we choose from are priced in US dollars. With AED, EUR or GBP, exchange rates also move what your money is worth to you. The dirham is pegged to the dollar, so that effect is small for AED.";

const amount = (min, msg) =>
  z
    .string()
    .transform((v) => Number(v.replace(/,/g, "")))
    .pipe(z.number({ error: "Enter a number" }).min(min, msg));

const choice = z.string().min(1, "Pick one");

const schema = z.object({
  birthYear: z
    .string()
    .regex(/^\d{4}$/, "Enter a 4-digit year")
    .refine((y) => +y >= 1920 && +y <= thisYear, "Enter a real birth year"),
  investCurrency: z.enum(currencies),
  investAmount: amount(1, "Enter an amount above zero"),
  monthlyCurrency: z.enum(currencies),
  monthlyAmount: amount(0, "Can't be negative"),
  horizon: choice,
  bigWithdrawal: choice,
  emergencyFund: choice,
  income: choice,
  shareOfWealth: choice,
});

const questions = [
  [
    "horizon",
    "When might you need this money?",
    [
      ["under_2", "Within 2 years"],
      ["2_5", "2–5 years"],
      ["5_10", "5–10 years"],
      ["10_plus", "10+ years"],
    ],
  ],
  [
    "bigWithdrawal",
    "Will you take out more than a quarter of it in the next 3 years?",
    [
      ["yes", "Yes"],
      ["no", "No"],
    ],
  ],
  [
    "emergencyFund",
    "If your income stopped, how long could savings cover your expenses?",
    [
      ["none", "Not at all"],
      ["under_3_months", "Under 3 months"],
      ["3_6_months", "3–6 months"],
      ["6_plus_months", "6+ months"],
    ],
  ],
  [
    "income",
    "How do you earn your income?",
    [
      ["salaried", "Salary"],
      ["variable", "Variable / commission"],
      ["self_employed", "Self-employed"],
      ["none", "No earned income"],
    ],
  ],
  [
    "shareOfWealth",
    "Roughly what share of your savings and investments is this?",
    [
      ["under_10", "Under 10%"],
      ["10_25", "10–25%"],
      ["25_50", "25–50%"],
      ["over_50", "Over 50%"],
    ],
  ],
];

const toCapacity = (d) => ({
  birth_year: Number(d.birthYear),
  currency: d.investCurrency,
  invest_amount: d.investAmount,
  monthly_amount: d.monthlyAmount,
  horizon: d.horizon,
  big_withdrawal: d.bigWithdrawal === "yes",
  emergency_fund: d.emergencyFund,
  income: d.income,
  share_of_wealth: d.shareOfWealth,
});

const fromCapacity = (c) => ({
  birthYear: String(c.birth_year),
  investCurrency: c.currency,
  investAmount: String(c.invest_amount),
  monthlyCurrency: c.currency,
  monthlyAmount: String(c.monthly_amount),
  horizon: c.horizon,
  bigWithdrawal: c.big_withdrawal ? "yes" : "no",
  emergencyFund: c.emergency_fund,
  income: c.income,
  shareOfWealth: c.share_of_wealth,
});

const fieldset =
  "flex flex-col gap-5 rounded-2xl border bg-card p-5 sm:gap-[22px] sm:p-7";
const legend =
  "px-2 text-[13px] font-extrabold tracking-[0.08em] text-primary uppercase";
const labelCls = "text-[15px] font-bold";
const hint = (err) =>
  cn("text-[13px]", err ? "text-destructive" : "text-muted-foreground");

export function SituationForm() {
  const router = useRouter();
  const [userId, setUserId] = useState(null);

  const {
    register,
    control,
    watch,
    setValue,
    reset,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
    mode: "onChange",
    defaultValues: {
      birthYear: "",
      investCurrency: "USD",
      investAmount: "",
      monthlyCurrency: "USD",
      monthlyAmount: "",
      horizon: "",
      bigWithdrawal: "",
      emergencyFund: "",
      income: "",
      shareOfWealth: "",
    },
  });

  // Prefer this session's unsent answers, otherwise prefill from the last submission
  useEffect(() => {
    const draft = sessionStorage.getItem(CAPACITY_KEY);
    if (draft) reset(fromCapacity(JSON.parse(draft)));
    else setUserId(localStorage.getItem(USER_ID_KEY));
  }, [reset]);

  const { data, isFetching } = useQuery({
    queryKey: ["risk-assessment", userId],
    queryFn: () => getRiskAssessment(userId),
    enabled: !!userId,
  });

  useEffect(() => {
    if (data) reset(fromCapacity(data.capacity));
  }, [data, reset]);

  const values = watch();
  const age = /^\d{4}$/.test(values.birthYear)
    ? thisYear - values.birthYear
    : null;
  const answered = [
    "birthYear",
    "investAmount",
    "monthlyAmount",
    ...questions.map(([name]) => name),
  ].filter((name) => values[name] !== "").length;

  // Both amounts share one currency, so changing either select updates the other
  const changeCurrency = (currency) => {
    setValue("investCurrency", currency);
    setValue("monthlyCurrency", currency);
    if (currency !== "USD") toast(FX_NOTE, { id: "fx", duration: 8000 });
  };

  // Saved until Section C, which submits the whole assessment in one request
  const onSubmit = (data) => {
    sessionStorage.setItem(CAPACITY_KEY, JSON.stringify(toCapacity(data)));
    router.push("/risk-assessment/section2");
  };

  const moneyField = (id, label, currencyName, amountName, help) => (
    <div className="flex flex-col gap-2">
      <Label htmlFor={id} className={labelCls}>
        {label}
      </Label>
      <div
        aria-invalid={!!errors[amountName]}
        className="flex h-12 overflow-hidden rounded-[10px] border border-input bg-white focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50 aria-invalid:border-destructive"
      >
        <select
          aria-label={`${label} currency`}
          className="border-r border-input bg-muted px-2.5 text-sm font-bold text-muted-foreground outline-none"
          {...register(currencyName, {
            onChange: (e) => changeCurrency(e.target.value),
          })}
        >
          {currencies.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
        <input
          id={id}
          inputMode="decimal"
          placeholder="0"
          className="min-w-0 flex-1 px-3 font-mono text-base font-medium outline-none"
          {...register(amountName)}
        />
      </div>
      {(errors[amountName] || help) && (
        <span className={hint(errors[amountName])}>
          {errors[amountName]?.message ?? help}
        </span>
      )}
    </div>
  );

  const choiceGroup = ([name, label, options]) => (
    <Controller
      key={name}
      name={name}
      control={control}
      render={({ field }) => (
        <div
          role="radiogroup"
          aria-labelledby={name}
          className="flex flex-col gap-2.5"
        >
          <span id={name} className={labelCls}>
            {label}
          </span>
          <div
            className={cn(
              "grid gap-2.5",
              options.length === 2
                ? "max-w-[320px] grid-cols-2"
                : "grid-cols-2 md:grid-cols-4",
            )}
          >
            {options.map(([value, text]) => (
              <button
                key={value}
                type="button"
                role="radio"
                aria-checked={field.value === value}
                onClick={() => field.onChange(value)}
                className={cn(
                  "min-h-12 rounded-[10px] border border-input bg-white px-2 text-[15px] font-semibold transition-colors hover:border-ring",
                  field.value === value &&
                    "border-2 border-primary bg-[#E3EEEA] font-bold text-[#133F34]",
                )}
              >
                {text}
              </button>
            ))}
          </div>
          {errors[name] && (
            <span className={hint(true)}>{errors[name].message}</span>
          )}
        </div>
      )}
    />
  );

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      noValidate
      className="flex min-h-0 flex-1 flex-col"
    >
      <div className="flex flex-1 flex-wrap items-start gap-7 px-4 py-6 sm:px-12 sm:py-8 lg:overflow-y-auto">
        <div className="flex min-w-0 flex-[999_1_560px] flex-col gap-6">
          <p className="text-base leading-relaxed text-[#3C4945]">
            These answers tell us how much risk you can afford, whatever you
            feel about it.
          </p>

          <fieldset className={fieldset}>
            <legend className={legend}>Time and money</legend>
            <div className="grid gap-5 md:grid-cols-3">
              <div className="flex flex-col gap-2">
                <Label htmlFor="yob" className={labelCls}>
                  Year of birth
                </Label>
                <Input
                  id="yob"
                  inputMode="numeric"
                  maxLength={4}
                  placeholder="1990"
                  aria-invalid={!!errors.birthYear}
                  className="h-12 rounded-[10px] bg-white px-3.5 font-mono text-base font-medium md:text-base"
                  {...register("birthYear")}
                />
                {(errors.birthYear || age !== null) && (
                  <span className={hint(errors.birthYear)}>
                    {errors.birthYear?.message ?? `You're ${age}.`}
                  </span>
                )}
              </div>
              {moneyField(
                "amt",
                "Investing now",
                "investCurrency",
                "investAmount",
              )}
              {moneyField(
                "monthly",
                "Each month after",
                "monthlyCurrency",
                "monthlyAmount",
                "Zero is fine.",
              )}
            </div>
            {questions.slice(0, 2).map(choiceGroup)}
          </fieldset>

          <fieldset className={fieldset}>
            <legend className={legend}>Your safety net</legend>
            {questions.slice(2).map(choiceGroup)}
          </fieldset>
        </div>

        <aside className="flex min-w-0 flex-[1_1_260px] flex-col gap-4">
          <div className="flex flex-col gap-2.5 rounded-2xl border bg-card p-[22px]">
            <h2 className="text-[15px] font-extrabold">Why we ask</h2>
            <p className="text-sm leading-relaxed text-[#3C4945]">
              Some answers limit your profile on their own. Needing the money
              within 2 years, planning a large withdrawal soon, or having no
              emergency fund keeps the result cautious however the rest scores.
            </p>
          </div>
          <div className="flex flex-col gap-1.5 rounded-2xl bg-[#E3EEEA] p-[22px] text-[#133F34]">
            <span className="text-[13px] font-extrabold tracking-[0.06em] text-primary uppercase">
              Section A
            </span>
            <span className="font-mono text-2xl font-medium">
              {answered} of 8
            </span>
            <span className="text-sm">questions answered</span>
          </div>
        </aside>
      </div>

      <footer className="sticky bottom-0 flex items-center justify-between gap-3 border-t bg-card px-4 py-4 sm:px-12 sm:py-5">
        <Button
          asChild
          variant="outline"
          className="h-12 rounded-xl bg-white px-[22px] text-base font-semibold"
        >
          <Link href="/">Back</Link>
        </Button>
        <Button
          type="submit"
          disabled={isFetching}
          className="h-12 rounded-xl px-7 text-base font-bold"
        >
          {isFetching && <Loader2 className="animate-spin" />}
          Continue<span className="hidden sm:inline">&nbsp;to Section B</span>
        </Button>
      </footer>
    </form>
  );
}

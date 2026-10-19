"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  CAPACITY_KEY,
  TOLERANCE_KEY,
  USER_ID_KEY,
} from "@/constants/constants";
import {
  createAssessmentResult,
  createRiskAssessment,
  getRiskAssessment,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const schema = z.object({
  exclusions: z.array(z.string()).min(1, "Choose at least one"),
  notes: z.string().max(1000, "Keep it under 1000 characters"),
});

const NONE = "No restrictions";
const SHARIA = "Sharia-compliant only";

const exclusions = [
  [NONE, "Use the full range of funds."],
  ["No crypto", "No bitcoin, ether or blockchain-company funds.", "no_crypto"],
  [
    SHARIA,
    "Only funds screened for Islamic finance rules.",
    "sharia_compliant",
  ],
  [
    "Prefer ESG funds",
    "Pick screened funds where one exists.",
    "esg_preference",
  ],
];

const codeOf = Object.fromEntries(
  exclusions.map(([label, , code]) => [label, code]),
);
const labelOf = Object.fromEntries(
  exclusions.map(([label, , code]) => [code, label]),
);

const fieldset =
  "flex min-w-0 flex-col gap-3.5 rounded-2xl border bg-card p-5 sm:p-7";
const legend =
  "px-2 text-[13px] font-extrabold tracking-[0.08em] text-primary uppercase";

export function PreferencesForm() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [userId, setUserId] = useState(null);
  const {
    control,
    register,
    watch,
    reset,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
    mode: "onChange",
    defaultValues: { exclusions: [], notes: "" },
  });

  useEffect(() => setUserId(localStorage.getItem(USER_ID_KEY)), []);

  const { data, isFetching } = useQuery({
    queryKey: ["risk-assessment", userId],
    queryFn: () => getRiskAssessment(userId),
    enabled: !!userId,
  });

  useEffect(() => {
    if (!data) return;
    reset({
      exclusions: data.exclusions.length
        ? data.exclusions.map((code) => labelOf[code])
        : [NONE],
      notes: data.notes ?? "",
    });
  }, [data, reset]);

  const picked = watch("exclusions");
  const notes = watch("notes");

  // "No restrictions" can't be combined with any other choice
  const toggle = (list, item, checked) => {
    if (!checked) return list.filter((x) => x !== item);
    if (item === NONE) return [NONE];
    return [...list.filter((x) => x !== NONE), item];
  };

  const { mutate, isPending } = useMutation({
    // Store the answers, then generate the result the scoring page reads
    mutationFn: async (payload) => {
      await createRiskAssessment(payload);
      return createAssessmentResult(payload.user_id);
    },
    onSuccess: () => {
      // The stored latest assessment changed, so refetch it next time
      queryClient.invalidateQueries({ queryKey: ["risk-assessment"] });
      sessionStorage.removeItem(CAPACITY_KEY);
      sessionStorage.removeItem(TOLERANCE_KEY);
      router.push("/risk-assessment/scoring");
    },
  });

  // Earlier sections are kept in browser storage, send everything in one request
  const onSubmit = (data) => {
    const userId = localStorage.getItem(USER_ID_KEY);
    const capacity = sessionStorage.getItem(CAPACITY_KEY);
    const tolerance = sessionStorage.getItem(TOLERANCE_KEY);
    const missing = [
      [userId, "your username", "/"],
      [capacity, "Section A", "/risk-assessment/section1"],
      [tolerance, "Section B", "/risk-assessment/section2"],
    ].find(([value]) => !value);
    if (missing) {
      toast.error(`Please complete ${missing[1]} first`);
      return router.push(missing[2]);
    }

    mutate({
      user_id: userId,
      capacity: JSON.parse(capacity),
      tolerance: JSON.parse(tolerance),
      exclusions: data.exclusions
        .filter((x) => x !== NONE)
        .map((x) => codeOf[x]),
      notes: data.notes,
    });
  };

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      noValidate
      className="flex min-h-0 flex-1 flex-col"
    >
      <div className="flex flex-1 flex-col gap-7 px-4 py-6 sm:px-12 sm:py-8 lg:flex-row lg:items-start lg:overflow-y-auto">
        <div className="flex min-w-0 flex-1 flex-col gap-6">
          <p className="text-base leading-relaxed text-[#3C4945]">
            These don't change your risk profile. They decide which funds we're
            allowed to pick for you.
          </p>

          <fieldset className={fieldset}>
            <legend className={legend}>Exclusions</legend>
            <p className="text-[15px] font-bold">
              Anything to avoid? Choose any that apply.
            </p>
            <Controller
              name="exclusions"
              control={control}
              render={({ field }) => (
                <div className="grid gap-2.5 sm:grid-cols-2">
                  {exclusions.map(([label, desc]) => {
                    const on = field.value.includes(label);
                    return (
                      <label
                        key={label}
                        className={cn(
                          "flex cursor-pointer items-start gap-3 rounded-xl border border-input p-4 transition-colors hover:border-ring",
                          on && "border-2 border-primary bg-[#E3EEEA] p-[15px]",
                        )}
                      >
                        <Checkbox
                          checked={on}
                          onCheckedChange={(c) =>
                            field.onChange(
                              toggle(field.value, label, c === true),
                            )
                          }
                          onBlur={field.onBlur}
                          className="mt-px size-5 bg-white"
                        />
                        <span className="flex flex-col gap-0.5">
                          <span
                            className={cn(
                              "text-[15px] font-bold",
                              on && "text-[#133F34]",
                            )}
                          >
                            {label}
                          </span>
                          <span
                            className={cn(
                              "text-[13px] text-muted-foreground",
                              on && "text-[#2A4C43]",
                            )}
                          >
                            {desc}
                          </span>
                        </span>
                      </label>
                    );
                  })}
                </div>
              )}
            />
            {errors.exclusions && (
              <span className="text-[13px] text-destructive">
                {errors.exclusions.message}
              </span>
            )}

            {picked.includes(SHARIA) && (
              <div
                role="status"
                className="flex items-start gap-3 rounded-xl border border-[#EBCFAE] bg-[#FBF0E2] px-4 py-3.5 text-sm leading-relaxed text-[#5C2F07]"
              >
                <svg
                  viewBox="0 0 20 20"
                  className="mt-px size-5 flex-none"
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
                  <strong>Sharia-compliant</strong> narrows the choice to 7
                  funds, with one sukuk fund for bonds and no sharia cash fund.
                </span>
              </div>
            )}
          </fieldset>

          <fieldset className={cn(fieldset, "gap-2.5")}>
            <legend className={legend}>Optional</legend>
            <label htmlFor="notes" className="text-[15px] font-bold">
              Anything else about your circumstances we should know?
            </label>
            <textarea
              id="notes"
              rows={3}
              maxLength={1000}
              placeholder="For example a house purchase or a change of job. Leave blank if nothing comes to mind."
              className="resize-y rounded-[10px] border border-input bg-white px-3.5 py-3 text-[15px] outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
              {...register("notes")}
            />
            <span className="self-end font-mono text-xs text-muted-foreground">
              {notes.length} / 1000
            </span>
            {errors.notes && (
              <span className="text-[13px] text-destructive">
                {errors.notes.message}
              </span>
            )}
          </fieldset>
        </div>

        <aside className="flex flex-col gap-2.5 rounded-2xl border bg-card p-[22px] lg:w-[300px]">
          <h2 className="text-[15px] font-extrabold">Before you submit</h2>
          <p className="text-sm leading-relaxed text-[#3C4945]">
            Submitting creates a locked record of your answers and result. You
            can always start a new assessment, but this one won't change.
          </p>
        </aside>
      </div>

      <footer className="sticky bottom-0 flex items-center justify-between gap-3 border-t bg-card px-4 py-4 sm:px-12 sm:py-5">
        <Button
          asChild
          variant="outline"
          className="h-12 rounded-xl bg-white px-[22px] text-base font-semibold"
        >
          <Link href="/risk-assessment/section2">Back</Link>
        </Button>
        <Button
          type="submit"
          disabled={isPending || isFetching}
          className="h-12 rounded-xl px-7 text-base font-bold"
        >
          {(isPending || isFetching) && <Loader2 className="animate-spin" />}
          Submit
          <span className="hidden sm:inline">&nbsp;and see my profile</span>
        </Button>
      </footer>
    </form>
  );
}

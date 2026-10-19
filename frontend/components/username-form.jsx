"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { USER_ID_KEY } from "@/constants/constants";

const EXAMPLE = "e.g. john@123 or #mary07";

const schema = z.object({
  username: z
    .string()
    .regex(
      /^[!-@[-~]*$/,
      `Spaces and capital letters aren't allowed, ${EXAMPLE}`,
    )
    .min(3, `Use at least 3 characters, ${EXAMPLE}`)
    .max(30, "Use 30 characters or fewer"),
  agreed: z.literal(true, { error: "Please confirm to continue" }),
});

export function UsernameForm() {
  const router = useRouter();
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
    mode: "onChange",
    defaultValues: { username: "", agreed: false },
  });

  const onSubmit = ({ username }) => {
    localStorage.setItem(USER_ID_KEY, username);
    router.push("/risk-assessment/section1");
  };

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      noValidate
      className="flex w-full max-w-[440px] flex-col gap-5 rounded-[20px] border bg-card p-5 shadow-[0_24px_60px_-20px_rgba(21,33,30,0.25)] sm:gap-6 sm:p-10"
    >
      <div className="flex flex-col gap-1.5 sm:gap-2">
        <h2 className="text-[22px] font-extrabold sm:text-[26px]">
          Let's get started
        </h2>
        <p className="text-[15px] leading-relaxed text-muted-foreground">
          Choose a username so we can label your assessment and you can find it
          again.
        </p>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="username" className="text-[15px] font-bold">
          Username
        </Label>
        <Input
          id="username"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          placeholder="e.g. john@123"
          aria-invalid={!!errors.username}
          aria-describedby="username-help"
          className="h-[50px] rounded-[10px] bg-white px-3.5 text-base font-medium md:text-base"
          {...register("username")}
        />
        <p
          id="username-help"
          className={
            errors.username
              ? "text-[13px] text-destructive"
              : "text-[13px] text-muted-foreground"
          }
        >
          {errors.username?.message ??
            "3–30 characters: lowercase letters, numbers or symbols. No spaces or capitals."}
        </p>
      </div>

      <div className="flex flex-col gap-2">
        <Controller
          name="agreed"
          control={control}
          render={({ field }) => (
            <label className="flex cursor-pointer items-start gap-3 rounded-xl bg-muted p-3.5 text-sm leading-normal">
              <Checkbox
                checked={field.value}
                onCheckedChange={(checked) => field.onChange(checked === true)}
                onBlur={field.onBlur}
                aria-invalid={!!errors.agreed}
                className="mt-0.5 size-5 bg-white"
              />
              I understand this is a practice exercise and not personal
              investment advice.
            </label>
          )}
        />
        {errors.agreed && (
          <p className="text-[13px] text-destructive">
            {errors.agreed.message}
          </p>
        )}
      </div>

      <Button type="submit" className="h-[52px] rounded-xl text-base font-bold">
        Continue
      </Button>
    </form>
  );
}

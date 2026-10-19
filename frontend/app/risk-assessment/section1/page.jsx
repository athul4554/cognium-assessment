import { AssessmentSidebar } from "@/components/assessment-sidebar";
import { SituationForm } from "@/components/situation-form";

export default function Section1() {
  return (
    <div className="flex min-h-dvh flex-col lg:h-dvh lg:flex-row lg:overflow-hidden">
      <AssessmentSidebar current={1} />

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b bg-card px-4 py-5 sm:px-12 sm:py-6">
          <div className="flex flex-col gap-1">
            <span className="text-[13px] font-bold tracking-[0.08em] text-primary uppercase">
              Section A · Risk capacity
            </span>
            <h1 className="text-2xl font-extrabold sm:text-[28px]">Your situation</h1>
          </div>
          <span className="font-mono text-sm text-muted-foreground">Step 2 of 6</span>
        </header>

        <SituationForm />
      </main>
    </div>
  );
}

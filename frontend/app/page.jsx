import { CogniumLogo } from "@/components/cognium-logo";
import { UsernameForm } from "@/components/username-form";
import { steps } from "@/constants/constants";

export default function Home() {
  return (
    <main className="flex min-h-dvh flex-col lg:h-dvh lg:flex-row lg:overflow-hidden">
      <section className="relative isolate flex flex-col gap-6 overflow-hidden bg-[#15211E] px-5 pt-7 pb-12 text-[#E9EEEB] lg:flex-[1.15] lg:gap-10 lg:overflow-y-auto lg:px-16 lg:py-14">
        <div className="absolute -top-32 -left-24 -z-10 size-[420px] rounded-full bg-[#2E7D68]/40 blur-3xl" />
        <div className="absolute -right-32 bottom-0 -z-10 size-[380px] rounded-full bg-[#9FD3C3]/15 blur-3xl" />

        <div className="flex items-center gap-3">
          <CogniumLogo className="size-8 drop-shadow-[0_4px_12px_rgba(46,125,104,0.6)]" />
          <span className="bg-linear-to-r from-white via-[#C8F0E2] to-[#5FB89E] bg-clip-text text-xl font-extrabold tracking-tight text-transparent lg:text-2xl">
            Cognium
          </span>
        </div>

        <div className="flex max-w-[560px] flex-col gap-3 lg:gap-5">
          <p className="text-xs font-bold tracking-[0.1em] text-[#9FD3C3] uppercase lg:text-sm">
            Risk profiling &amp; portfolio planning
          </p>
          <h1 className="text-[30px] leading-[1.15] font-extrabold tracking-tight text-white lg:text-[46px] lg:leading-[1.1]">
            From your circumstances to a portfolio you can stick with.
          </h1>
          <p className="text-base leading-relaxed text-[#C8D3CF] lg:text-lg">
            You tell us about your situation and how you feel about risk. We
            work out a risk profile, a target mix across stocks, bonds, cash and
            more, and the named funds that could fill it.
          </p>
        </div>

        <ol className="flex max-w-[520px] flex-col gap-3 lg:gap-3.5">
          {steps.map(([title, text], i) => (
            <li key={title} className="flex items-start gap-3 lg:gap-4">
              <span className="flex size-7 flex-none items-center justify-center rounded-full border border-white/10 bg-[#23362F] font-mono text-[13px] font-medium text-[#9FD3C3] lg:size-8 lg:text-sm">
                {i + 1}
              </span>
              <span className="flex flex-col gap-0.5">
                <strong className="text-[15px] text-white lg:text-base">
                  {title}
                </strong>
                <span className="text-sm text-[#B5C2BD] lg:text-[15px]">
                  {text}
                </span>
              </span>
            </li>
          ))}
        </ol>
      </section>

      <section className="relative z-10 -mt-4 flex flex-1 justify-center px-4 pb-7 lg:mt-0 lg:items-center lg:overflow-y-auto lg:px-16 lg:py-14">
        <UsernameForm />
      </section>
    </main>
  );
}

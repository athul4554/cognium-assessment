"use client";

import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { AssessmentSidebar } from "@/components/assessment-sidebar";
import { Button } from "@/components/ui/button";
import { assetGroups, USER_ID_KEY } from "@/constants/constants";
import { getRecommendation } from "@/lib/api";
import { cn } from "@/lib/utils";

const columns = ["Weight", "Amount", "Price", "1y", "3y / yr", "Volatility", "Worst fall", "Fee"];
const stats = ["1y", "Volatility", "Worst fall", "Fee"];

const card = "flex flex-col gap-3 rounded-2xl border bg-card px-5 py-5 sm:px-6 sm:py-[22px]";

const money = (value, currency) =>
  new Intl.NumberFormat("en-GB", { style: "currency", currency, maximumFractionDigits: 2 }).format(value);

// Signed percent with a real minus sign, "—" when there's no figure
const pct = (value, signed = true) => {
  if (value == null) return "—";
  const sign = !signed ? "" : value > 0 ? "+" : value < 0 ? "−" : "";
  return `${sign}${Math.abs(value).toFixed(1)}%`;
};

const fee = (value) => (value == null ? "—" : `${value.toFixed(2)}%`);

// Table cells for one holding, in `columns` order
const fundValues = (h, currency) => {
  const m = h.metrics;
  return [
    `${h.weight}%`,
    money(h.amount, currency),
    m ? m.last_close.toFixed(2) : "—",
    pct(m?.return_1y_pct),
    pct(m?.return_3y_annualised_pct),
    pct(m?.volatility_1y_pct, false),
    pct(m?.max_drawdown_3y_pct),
    fee(h.expense_ratio_pct),
  ];
};

function Swatch({ color }) {
  return <span className={cn("size-3 flex-none rounded-[3px]", color)} />;
}

function GroupTitle({ group }) {
  const g = assetGroups[group.group];
  return (
    <h3 className="flex items-center gap-2.5 text-[17px] font-extrabold">
      <Swatch color={g.color} />
      {g.name} · {group.weight}%
    </h3>
  );
}

function FundName({ holding }) {
  // Uninvested cash has no ticker, only a name
  return holding.ticker ? (
    <>
      <strong>{holding.ticker}</strong>{" "}
      <span className="text-sm text-muted-foreground">{holding.name}</span>
    </>
  ) : (
    <strong>{holding.name}</strong>
  );
}

function FundTable({ group, holdings, currency }) {
  return (
    <section className={card}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <GroupTitle group={group} />
        <span className="text-sm text-muted-foreground">{assetGroups[group.group].note}</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] border-collapse text-sm">
          <thead>
            <tr className="text-right text-xs text-muted-foreground">
              <th scope="col" className="border-b p-2 text-left font-bold">Fund</th>
              {columns.map((c) => (
                <th key={c} scope="col" className="border-b p-2 font-bold">{c}</th>
              ))}
            </tr>
          </thead>
          <tbody className="text-right font-mono">
            {holdings.map((h) => (
              <tr key={h.ticker ?? h.name} className="border-b border-[#EEF1EF] last:border-0">
                <td className="px-2 py-2.5 text-left font-sans">
                  <FundName holding={h} />
                </td>
                {fundValues(h, currency).map((v, i) => (
                  <td key={columns[i]} className={cn("px-2 py-2.5", i === 6 && "text-[#8A3B0A]")}>{v}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function FundCard({ group, holding, currency }) {
  const m = holding.metrics;
  const values = [
    pct(m?.return_1y_pct),
    pct(m?.volatility_1y_pct, false),
    pct(m?.max_drawdown_3y_pct),
    fee(holding.expense_ratio_pct),
  ];
  return (
    <section className={card}>
      <div className="flex flex-col gap-1">
        <GroupTitle group={group} />
        <span className="text-sm text-muted-foreground">{assetGroups[group.group].note}</span>
      </div>
      <div className="flex items-baseline justify-between gap-2">
        <span>
          <FundName holding={holding} />
        </span>
        <span className="font-mono text-[15px] font-medium">{money(holding.amount, currency)}</span>
      </div>
      <dl className="grid grid-cols-2 gap-2 font-mono text-[13px] sm:grid-cols-4">
        {stats.map((s, i) => (
          <div key={s}>
            <dt className="font-sans text-xs font-semibold text-muted-foreground">{s}</dt>
            <dd className={cn(i === 2 && "text-[#8A3B0A]")}>{values[i]}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export default function Recommendations() {
  const [userId, setUserId] = useState(null);
  useEffect(() => setUserId(localStorage.getItem(USER_ID_KEY)), []);

  const { data: rec, isPending } = useQuery({
    queryKey: ["recommendation", userId],
    queryFn: () => getRecommendation(userId),
    enabled: !!userId,
  });

  // Groups with several funds read best as a table, single-fund groups as cards
  const holdingsOf = (group) => rec.holdings.filter((h) => h.group === group.group);
  const tables = rec?.groups.filter((g) => holdingsOf(g).length > 1) ?? [];
  const cards = rec?.groups.filter((g) => holdingsOf(g).length === 1) ?? [];

  const snapshotDate = rec?.holdings.find((h) => h.metrics?.source === "snapshot")?.metrics.last_close_date;

  return (
    <div className="flex min-h-dvh flex-col lg:h-dvh lg:flex-row lg:overflow-hidden">
      <AssessmentSidebar current={5} />

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b bg-card px-4 py-5 sm:px-12 sm:py-6">
          <div className="flex flex-col gap-1">
            <span className="text-[13px] font-bold tracking-[0.08em] text-primary uppercase">
              Recommendation{rec && ` · ${rec.label}`}
            </span>
            <h1 className="text-2xl font-extrabold sm:text-[28px]">Your portfolio</h1>
          </div>
          <span className="font-mono text-sm text-muted-foreground">Step 6 of 6</span>
        </header>

        {!rec ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 px-4 py-16 text-center text-muted-foreground">
            {userId && isPending ? (
              <Loader2 className="size-8 animate-spin text-primary" />
            ) : (
              <p className="text-base">
                No portfolio yet. Open your risk profile and choose “See my portfolio”.
              </p>
            )}
          </div>
        ) : (
          <div className="flex flex-1 flex-col gap-4 px-4 py-6 sm:gap-[22px] sm:px-12 sm:py-7 lg:overflow-y-auto">
            <section
              aria-labelledby="mix"
              className="flex flex-col gap-[18px] rounded-[20px] border bg-card p-5 sm:p-7"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 id="mix" className="text-xl font-extrabold">Target allocation</h2>
                <span className="font-mono text-sm text-muted-foreground">
                  {money(rec.invest_amount, rec.currency)}
                  {rec.monthly_amount > 0 && ` + ${money(rec.monthly_amount, rec.currency)} / month`}
                </span>
              </div>
              <div
                role="img"
                aria-label={rec.groups.map((g) => `${assetGroups[g.group].name} ${g.weight}%`).join(", ")}
                className="flex h-9 gap-[3px] overflow-hidden rounded-[10px]"
              >
                {rec.groups.map((g) => (
                  <span key={g.group} className={assetGroups[g.group].color} style={{ flex: g.weight }} />
                ))}
              </div>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
                {rec.groups.map((g) => (
                  <div key={g.group} className="flex flex-col gap-0.5">
                    <span className="flex items-center gap-2 font-bold">
                      <Swatch color={assetGroups[g.group].color} />
                      {assetGroups[g.group].name}
                    </span>
                    <span className="font-mono text-2xl font-medium">{g.weight}%</span>
                    <span className="font-mono text-[13px] text-muted-foreground">{money(g.amount, rec.currency)}</span>
                  </div>
                ))}
              </div>
              {rec.ceiling && (
                <p className="rounded-[10px] bg-[#E3EEEA] px-3 py-2.5 text-sm leading-relaxed text-[#133F34]">
                  <strong>Why this mix:</strong> {rec.ceiling}
                </p>
              )}
            </section>

            {tables.map((g) => (
              <FundTable key={g.group} group={g} holdings={holdingsOf(g)} currency={rec.currency} />
            ))}

            <div className="grid gap-4 md:grid-cols-2">
              {cards.map((g) => (
                <FundCard key={g.group} group={g} holding={holdingsOf(g)[0]} currency={rec.currency} />
              ))}
            </div>

            <p className="text-[13px] leading-relaxed text-muted-foreground">
              Returns, volatility and worst fall are history from the last one to three years, not a forecast.
              “—” means the fund is too new for that figure.
              {snapshotDate && ` Some prices are from our saved snapshot of ${snapshotDate}.`} Rules v{rec.record.rules},
              fund list as of{" "}
              {rec.record.universe_as_of}. Practice exercise, not investment advice.
            </p>
          </div>
        )}

        <footer className="sticky bottom-0 flex items-center justify-between gap-3 border-t bg-card px-4 py-4 sm:px-12 sm:py-5">
          <Button asChild variant="outline" className="h-12 rounded-xl bg-white px-[22px] text-base font-semibold">
            <Link href="/risk-assessment/scoring">Back to my profile</Link>
          </Button>
        </footer>
      </main>
    </div>
  );
}

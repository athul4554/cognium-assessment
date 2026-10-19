# Technical Assignment — Full-Stack Engineer

**Cognium Inc.**

---

Thanks for making time for this.

This is a small version of something we build for real. A customer tells us about their circumstances and their appetite for risk, and the system works out what they should hold. You'll build the whole path, from the questionnaire through to the named instruments.

If anything here is ambiguous, ask us and we'll get back to you quickly. There's no penalty for asking. Our hunch is that this is around six hours of work, though that's only a hunch and people work at different speeds.

---

## The brief

Build a risk profiling and portfolio recommendation application. A customer completes a suitability questionnaire; the system scores their risk profile, maps that profile to a target asset allocation, and recommends specific instruments to fill it.

Three stages:

1. **Intake** — the customer completes the questionnaire
2. **Assessment** — the system computes a risk profile from their answers
3. **Recommendation** — the system produces a target allocation and the instruments to implement it

You're welcome to use an LLM anywhere in the system where you think it adds value.

---

## A few notes before you start

**AI is welcome.** We expect you'll use it, and it won't count against you. What we care about are the decisions you made, so we'll likely dig into a few parts of the codebase when we meet.

**Component libraries are welcome too.** shadcn/ui, Tailwind, whatever you reach for. Sensible defaults are fine with us.

**A working app beats a beautiful partial one.** If you run short on time, cut scope and keep the logic correct. A complete three-stage flow with two asset sleeves is worth more to us than a polished form that never produces a recommendation.

**Assume around 50 concurrent users.** No need to engineer for scale you don't have. We'd rather see the simple version done well.

**The scoring logic should be right, and worth trusting.** It's the core of the system, so it's the one place we'd expect tests. Our main worry is a recommendation that looks plausible and doesn't follow from the inputs.

**This is an exercise. It isn't production advice software.** The output looks like investment advice and it isn't. We'd like you to handle that in the interface as you see fit.

---

## Stage 1 — Intake form

We've fixed the fields below so we can compare submissions fairly. The wording is yours, so feel free to rewrite any question you think you can ask better.

### Section A — Risk capacity

| Field | Options |
|---|---|
| Year of birth | free entry |
| Investment horizon | under 2 years / 2–5 / 5–10 / 10+ |
| Initial investment amount | free entry |
| Planned monthly contribution | free entry, may be zero |
| Emergency fund | none / under 3 months / 3–6 months / 6+ months of expenses |
| Income stability | salaried / variable or commission / self-employed / no earned income |
| Share of liquid net worth | under 10% / 10–25% / 25–50% / over 50% |
| Withdrawal expectation | expects to withdraw more than 25% within 3 years — yes/no |

### Section B — Risk tolerance

| Field | Options |
|---|---|
| Primary goal | capital preservation / income / balanced growth / aggressive growth |
| Reaction to a 20% drop over three months | sell everything / sell some / hold / buy more |
| Maximum acceptable one-year loss | 0% / −5% / −15% / −30% or more |
| Portfolio preference | choose one of the three below |
| Investment experience | none / funds only / individual stocks and ETFs / derivatives or leverage |

Portfolio preference options, which we'd like presented as given:

- **A** — 5% a year, worst fall from peak −19%
- **B** — 10% a year, worst fall from peak −22%
- **C** — 15% a year, worst fall from peak −32%

Rounded from historical figures for annually rebalanced 20/80, 60/40 and 90/10 stock-bond blends over the last ten years. The loss figure is the deepest peak-to-trough fall in that period. Worth showing the customer as history, not as a forecast.

### Section C — Constraints

| Field | Options |
|---|---|
| Base currency | USD / AED / EUR / GBP |
| Exclusions | none / no crypto / sharia-compliant only / ESG preference (multi-select) |

### Optional

A free-text field: *anything else about your circumstances we should know.* Plenty of customers will leave it blank, so the system has to produce a full recommendation without it.

---

## Stage 2 — Risk assessment

Score **capacity** (Section A) and **tolerance** (Section B) separately, then combine them into a single profile. How you combine them is your call.

Some answers should be able to constrain the outcome on their own, whatever the rest of the questionnaire scores.

The result is one of five profiles: **conservative / moderately conservative / balanced / growth / aggressive**.

### Record integrity

We'd like one completed assessment to be one immutable record. Opening an assessment six months from now should make it clear exactly why the system recommended what it did at the time.

---

## Stage 3 — Portfolio recommendation

Map the profile to a target allocation across sleeves — equity, fixed income, cash, and whichever others you choose — then fill each sleeve with instruments from the universe.

Apply the customer's exclusions when selecting instruments.

Percentages and notional amounts are fine. No need to handle whole-share quantities or rounding.

### Instrument universe

The starter bundle contains `universe.json`: 232 US-listed ETFs across 20 sleeves, covering equity by size, style, sector and region, government and corporate credit, inflation-linked, high yield, municipals, emerging market debt, cash, gold, commodities, real estate, multi-asset, and liquid alternatives.

Each instrument carries name, sleeve, region, Morningstar category, provider, expense ratio, fund net assets, distribution yield, inception date, and boolean flags for `sharia_compliant`, `esg` and `crypto`. The exclusion options in Section C map onto those flags.

A note on `fund_net_assets_usd`: for fund families that issue the ETF as one share class of a larger fund, this figure covers the whole fund rather than the ETF alone, so it isn't directly comparable across providers. The definitions are in `field_notes` at the top of the file.

The universe is larger than any one portfolio needs, so how you narrow it down is part of the work.

### Market data

Use **yfinance**, pinned to `1.7.0`. Alongside price, derive and show for each instrument: 1-year and 3-year return, annualised volatility, and maximum drawdown.

yfinance is an unofficial client and isn't always dependable. The starter bundle includes a price snapshot at `snapshot.json` carrying the last close and the derived metrics for every instrument. Please keep it as a fallback. It's there so a bad day at the provider doesn't sink your demo.

---

## Optional extra

Entirely optional. It carries no weight, and skipping it costs you nothing.

Fixed coupon notes are a structured product we see a lot of in this market. The investor takes on the downside of one or more underlying stocks. In exchange they receive a fixed coupon paid on schedule whatever the stocks do. There is usually an early redemption barrier, and a knock-in barrier below which the investor ends up holding the worst performer at a loss.

No FCN has a ticker, and no data feed carries one. The terms are constructed against the underlyings.

There's nothing to build here. If the idea appeals to you, just come ready to talk about how you'd fit one into what you've built, and what would have to change to accommodate it.

Things we'd find interesting: which customer profiles should ever be shown one, how you'd derive indicative terms from the underlying's own data, where the note sits in the allocation and what asset class it counts as, and how you'd show a customer what they are actually taking on.

---

## What we're looking at

| Area | Weight |
|---|---|
| Frontend craft | 30% |
| Assessment logic and record integrity | 35% |
| Recommendation logic and data handling | 35% |

On the frontend: assembling components cleanly is assumed. What interests us is how the experience holds up away from the happy path, how a fifteen-field questionnaire is paced and grouped, and whether the results screen reads well to someone who is a little nervous about their money.

---

## When we meet

We'll talk through the questions below. Nothing needs writing up beforehand. We're telling you now so you know where the conversation will go.

1. Where the LLM sits in your pipeline, and why there and not elsewhere.
2. If an LLM writes customer-facing copy, what stops it from saying something inaccurate about the recommendation.
3. How the risk score is computed. If we re-ran your scorer today against an assessment from six months ago and got a different profile, what would have gone wrong?
4. A customer with high capacity and low tolerance — stable income, twenty-year horizon, large emergency fund, but says they'd sell everything at a 20% drop. What does your system do, and why?
5. Anything you found in the instrument universe that didn't quite fit the constraints, and how you handled it.
6. How many external data calls a single submission triggers, and what happens when the provider is unavailable.
7. Which part of your code you're least confident in, and what you'd test next.
8. What breaks first at 10,000 concurrent users.

---

## Submitting

A repository we can run, plus a short README with:

- How to run it
- **What you cut, why, and what you'd do next** — three bullets is plenty

That's all we need in writing.

We'll then set up a 60-minute session where you walk us through what you built. It's an informal conversation. We're mostly curious how you thought about it.

Questions before or during: [contact].

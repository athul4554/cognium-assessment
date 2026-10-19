export const steps = [
  [
    "Tell us about you",
    "15 questions in three short sections, about 8 minutes.",
  ],
  [
    "See your risk profile",
    "What you can afford and what you're comfortable with, scored separately.",
  ],
  [
    "Get your portfolio",
    "A target allocation and the specific funds to fill it, respecting your exclusions.",
  ],
];

export const sections = [
  ["Welcome"],
  ["Your situation", "Section A"],
  ["Risk and you", "Section B"],
  ["Preferences", "Section C"],
  ["Your risk profile"],
  ["Your portfolio"],
];

export const currencies = ["USD", "AED", "EUR", "GBP"];

// Browser storage keys
export const USER_ID_KEY = "cognium.userId";
export const CAPACITY_KEY = "cognium.capacity";
export const TOLERANCE_KEY = "cognium.tolerance";

export const levels = ["Conservative", "Moderately conservative", "Balanced", "Growth", "Aggressive"];

// Score reason labels by answer code, copied from backend/scorer/v1.0.0.json
export const reasonLabels = {
  horizon: { under_2: "Needs the money within 2 years", "2_5": "2–5 year horizon", "5_10": "5–10 year horizon", "10_plus": "10+ year horizon" },
  big_withdrawal: { true: "Large withdrawal within 3 years", false: "No large withdrawal soon" },
  emergency_fund: { none: "No emergency fund", under_3_months: "Under 3 months saved", "3_6_months": "3–6 months saved", "6_plus_months": "6+ months saved" },
  income: { none: "No earned income", self_employed: "Self-employed", variable: "Variable or commission income", salaried: "Salaried" },
  share_of_wealth: { over_50: "Over 50% of your savings", "25_50": "25–50% of your savings", "10_25": "10–25% of your savings", under_10: "Under 10% of your savings" },
  drop: { sell_all: "Would sell everything at −20%", sell_some: "Would sell some at −20%", hold: "Would hold at −20%", buy_more: "Would buy more at −20%" },
  max_loss: { 0: "Can't accept any loss", 5: "Up to 5% yearly loss", 15: "Up to 15% yearly loss", "30_plus": "30%+ yearly loss" },
  portfolio: { A: "Picked Portfolio A (20/80)", B: "Picked Portfolio B (60/40)", C: "Picked Portfolio C (90/10)" },
  goal: { capital_preservation: "Goal: keep it safe", income: "Goal: regular income", balanced_growth: "Goal: steady growth", aggressive_growth: "Goal: maximum growth" },
  experience: { none: "No investing experience", funds_only: "Funds experience", stocks_etfs: "Stocks and ETFs experience", derivatives_leverage: "Derivatives or leverage experience" },
};

// Text for the caps that decided a profile, by cap id from backend rules v1.0.0.json
export const capLabels = {
  horizon_under_2: "You need the money within 2 years",
  big_withdrawal: "You plan a large withdrawal within 3 years",
  no_emergency_fund: "You have no emergency fund",
  no_income_high_share: "You have no earned income and are investing over half your savings",
  drop_sell_all: "You would sell everything after a 20% fall",
  zero_loss: "You can't accept any loss",
  no_experience: "You have no investing experience",
};

// Recommendation asset groups, in the order the backend returns them
export const assetGroups = {
  equity: { name: "Stocks", color: "bg-[#1E5E4E]", note: "Growth over the long run. The part that moves the most." },
  fixed_income: { name: "Bonds", color: "bg-[#4F7FAE]", note: "Steadier income that softens falls." },
  real_estate: { name: "Property", color: "bg-[#A8674A]", note: "Listed property companies that pay out rental income." },
  gold: { name: "Gold", color: "bg-[#D9A93A]", note: "Often moves differently from stocks and bonds." },
  crypto: { name: "Crypto", color: "bg-[#6B5B95]", note: "A small, very volatile slice. Can halve in a bad year." },
  cash: { name: "Cash", color: "bg-[#B7C2BD]", note: "Stable value and money you can reach quickly." },
};

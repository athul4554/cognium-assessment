# Recommendation architecture: standard portfolio optimization

**Implemented in allocation rules v1.4.0.**

Use **Markowitz mean–variance optimization**, a foundational portfolio-construction method. Its objective matches the feedback: maximize estimated portfolio return within the client's risk budget, using diversification. [Background](https://www.nobelprize.org/prizes/economic-sciences/1990/press-release/)

The earlier shortlist-and-grid-search proposal was a custom heuristic. This design replaces that search with a standard optimizer. The historical drawdown check and cash fallback remain small application rules, not guarantees supplied by mean–variance optimization.

**Flow:** eligible funds → daily returns → return and covariance estimates → optimized weights → historical risk report → recommendation.

## 1. Get the data

| Source | Purpose |
|---|---|
| `universe.json` | Available funds, asset classes, fees and user-preference filters. Currently 232 instruments, all USD-denominated. |
| Yahoo Finance | Approximately three years of adjusted daily prices, using explicit start/end dates. |
| New saved `price_history.json` | The same daily history for use when Yahoo is unavailable. Prepare this before the demo. |
| Existing `snapshot.json` | Legacy fund summaries, unused by new recommendations. They cannot supply correlations or combined portfolio drawdowns. |

Apply user exclusions and retain funds with usable history on common dates, with at least one year of observations. Use eligible broad equity, bond, gold and cash funds; include sukuk for Sharia-compliant fixed income. Define this allowed asset-class list in configuration. Do not preselect funds simply because they have the highest individual return or lowest fee.

`get_price_history()` makes one download attempt and returns aligned prices with their source. The builder calculates daily returns and selected-fund display metrics from these same prices. The router only saves and serves the finished recommendation; it does not download prices again.

Yahoo's download interface supports daily adjusted prices. [Download documentation](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html)

## 2. Calculate two optimizer inputs

- **Estimated return:** annualized arithmetic mean of each fund's daily returns. This is a simple historical estimate, not a promised future return.
- **Covariance:** how much each fund fluctuates and how its returns move with the others. Use the library's Ledoit–Wolf estimator to reduce noise in this estimate. [Risk-model documentation](https://pyportfolioopt.readthedocs.io/en/latest/RiskModels.html)

Covariance incorporates correlation. A negatively correlated fund can offset another fund's movements; low positive correlation can also help. The optimizer weighs that diversification benefit against return and individual risk. It does not require every selected pair to have negative correlation.

## 3. Let the risk profile set the risk budget

Retain the existing configurable assessment targets:

| Profile | Maximum estimated annual volatility | Historical drawdown target |
|---|---:|---:|
| Conservative | 6% | 10% |
| Moderately conservative | 9% | 15% |
| Balanced | 12% | 22% |
| Growth | 15% | 28% |
| Aggressive | 18% | 35% |

These numbers are product assumptions, not thresholds established by portfolio theory.

Give the optimizer this instruction:

> Maximize estimated return while keeping portfolio volatility within the profile's budget.

Add simple constraints: weights total 100%, no borrowing or short selling, and configurable upper limits on individual funds and asset classes to prevent concentration. Include uninvested cash, allowed from 0% to 100%, modeled with zero nominal return and variance. Avoid mandatory minimum investments that make cautious allocations impossible.

Use **PyPortfolioOpt** to solve the same return-maximization problem as `EfficientFrontier.efficient_risk()`. The implementation uses its public `convex_objective()` interface because `efficient_risk()`'s minimum-risk precheck does not correctly account for an explicit zero-variance cash asset. The mathematical objective is unchanged. The weights determine both the selected funds and their allocations. [Optimizer documentation](https://pyportfolioopt.readthedocs.io/en/latest/MeanVariance.html)

## 4. Report historical risk

Calculate weighted daily portfolio returns from the final weights. Report annualized historical volatility and maximum drawdown, including initial capital in the drawdown path.

`historical_risk()` is a direct matrix multiplication followed by volatility and drawdown calculations. It does not simulate monthly rebalancing, compound an annual return, calculate turnover, validate the optimizer, or change the allocation.

**Mean–variance optimization controls estimated volatility, not maximum drawdown.** Historical drawdown is displayed for context and is not an optimizer constraint or a guarantee.

## 5. Keep the demo usable without hiding limitations

- Yahoo unavailable: use saved daily history and show its date.
- Missing history, no eligible funds, or a numerical optimizer failure: return an explicitly unallocated cash balance with an explanation. Do not invent portfolio risk metrics.
- Explicit “can't accept any loss” answer: return a cash-only illustration; do not interpret Conservative as permission to lose 10%.

Cash fallback is not an optimized investment portfolio or a guarantee of purchasing-power protection. A working response does not always mean a fully invested portfolio.

## 6. Small implementation structure

| File | Responsibility |
|---|---|
| `market_data.py` | Download/load saved prices and prepare aligned daily returns. |
| `portfolio.py` | Return/covariance estimates and historical portfolio calculations. |
| `search.py` | Optimizer wrapper and final weight rounding. |
| Rules JSON | Risk budgets, concentration limits and eligible asset classes. |
| `builder.py` | Holdings, amounts and explanations. |
| `router.py` / UI | Show allocation, historical metrics, data date and any fallback reason. |

PyPortfolioOpt is included in the backend dependencies and lockfile. No new service or database schema is needed. Performance figures are in USD; selected-currency amounts remain notionals.

Fund expense ratios are reported but not subtracted from Yahoo adjusted-price returns: fund operating costs are already reflected in those prices. Fees are therefore informational in this assessment rather than the allocation objective.

This is an established mathematical framework, not proof of future investment performance. Historical return estimates and correlations can change.

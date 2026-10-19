from pathlib import Path
from typing import Literal, get_args

API_PREFIX = "/api/v1"

APP_DIR = Path(__file__).resolve().parent

# Scorer config used to compute results
SCORER_PATH = APP_DIR / "assessment" / "rules" / "v1.0.0.json"

# Recommendation rules, instrument universe and fallback price snapshot
RECOMMENDATION_DIR = APP_DIR / "recommendation"
RECOMMENDER_PATH = RECOMMENDATION_DIR / "rules" / "v1.0.0.json"
UNIVERSE_PATH = RECOMMENDATION_DIR / "universe.json"
SNAPSHOT_PATH = RECOMMENDATION_DIR / "snapshot.json"

# Market data (yfinance)
MARKET_DATA_PERIOD = "3y"
MARKET_DATA_TIMEOUT_SECONDS = 10
TRADING_DAYS_PER_YEAR = 252

# Answer option codes, must match the scorer config option keys
# Literal types for the schemas, tuples of the same values for the DB enums
Currency = Literal["USD", "AED", "EUR", "GBP"]
Horizon = Literal["under_2", "2_5", "5_10", "10_plus"]
EmergencyFund = Literal["none", "under_3_months", "3_6_months", "6_plus_months"]
Income = Literal["none", "self_employed", "variable", "salaried"]
ShareOfWealth = Literal["over_50", "25_50", "10_25", "under_10"]
Portfolio = Literal["A", "B", "C"]
DropReaction = Literal["sell_all", "sell_some", "hold", "buy_more"]
MaxLoss = Literal["0", "5", "15", "30_plus"]
Goal = Literal["capital_preservation", "income", "balanced_growth", "aggressive_growth"]
Experience = Literal["none", "funds_only", "stocks_etfs", "derivatives_leverage"]
Exclusion = Literal["no_crypto", "sharia_compliant", "esg_preference"]

CURRENCIES = get_args(Currency)
HORIZONS = get_args(Horizon)
EMERGENCY_FUNDS = get_args(EmergencyFund)
INCOMES = get_args(Income)
SHARES_OF_WEALTH = get_args(ShareOfWealth)
PORTFOLIOS = get_args(Portfolio)
DROP_REACTIONS = get_args(DropReaction)
MAX_LOSSES = get_args(MaxLoss)
GOALS = get_args(Goal)
EXPERIENCES = get_args(Experience)
EXCLUSIONS = get_args(Exclusion)

# Field limits
MIN_BIRTH_YEAR = 1920
USER_ID_MAX_LENGTH = 100
NOTES_MAX_LENGTH = 1000
AMOUNT_MAX_DIGITS = 14
AMOUNT_DECIMAL_PLACES = 2

# Result score card titles
CAPACITY_TITLE = "What you can afford · capacity"
TOLERANCE_TITLE = "How you feel about it · tolerance"

# Error messages
NO_SUBMISSION = "No risk assessment found for this user"
NO_RESULT = "No assessment result found for this user"
NO_RECOMMENDATION = "No recommendation found for this user"
DB_ERROR = "Database error, please try again"

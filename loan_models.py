from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_serializer

TRANCHE_PROMPT = """
Tranche Information:
We need to look into the credit agreement if the loan has multiple tranches or a single-tranche loan. Each tranche has a minimum and maximum loan amount and the details of the repayment schedule. We need all of the tranche-related information.
Extract all the information about the tranches in this loan agreement. Including the tranche type, distribution method, maturity date, currency, minimum and maximum amounts, purpose, LT amount and date, repayment type, swingline loan amount, and any other relevant information like the lender details.
"""


class DealMain(BaseModel):
    borrower_name: str
    purpose: str
    min_commitment: float
    max_commitment: float
    signing_date: datetime

    @field_serializer("signing_date")
    def serialize_date(self, value: datetime) -> str:
        return value.strftime("%d-%m-%Y")

    @classmethod
    def shortlist_prompt(cls) -> str:
        return """
Deal/Loan General Information:
The main items for the high-level information about loan details are the parties that are involved in the credit agreement along with the signing date, loan amount, and all other parties involved like Banks and agents. Include the borrower name, purpose, minimum and maximum commitment amounts, and the signing date and any other relevant information.
"""

    @classmethod
    def prompt(cls) -> str:
        return """
Extract the deal main details:
- Borrower name
- Purpose
- Minimum and maximum commitment amounts
- Signing date
"""


RepaymentType = Literal["Bullet", "Amortizing"]


class TrancheMain(BaseModel):
    tranche_type: Literal[
        "Term A",
        "Term B",
        "Revolving Credit",
        "Delayed Draw",
        "Acquisition Facility",
        "Multicurrency",
        "Institutional",
        "Senior",
        "Subordinated",
    ]
    distribution_method: Literal["Syndicated", "Club Deal", "Bilateral"]
    maturity_date: datetime
    currency: list[str]
    min_amount: float
    max_amount: float
    purpose: str
    lt_amount: float = 0.0
    lt_date: datetime | str = ""
    repayment_type: RepaymentType
    swingline_loan: float

    @field_serializer("maturity_date")
    def serialize_maturity_date(self, value: datetime) -> str:
        return value.strftime("%d-%m-%Y")

    @field_serializer("lt_date")
    def serialize_lt_date(self, value: datetime | str) -> str:
        if isinstance(value, str):
            return ""
        return value.strftime("%d-%m-%Y")

    @classmethod
    def shortlist_prompt(cls) -> str:
        return TRANCHE_PROMPT

    @classmethod
    def prompt(cls) -> str:
        return """
Extract the main tranche details:
- Tranche type
- Distribution method
- Maturity date
- Currencies
- Minimum and maximum amounts
- Purpose
- LT amount and date if applicable
- Repayment type
- Swingline loan amount
"""


class TrancheOptionsRepayment(BaseModel):
    period: RepaymentType
    number_of_periods: int
    amount: float
    percent: float
    begin_date: datetime

    @field_serializer("begin_date")
    def serialize_begin_date(self, value: datetime) -> str:
        return value.strftime("%d-%m-%Y")

    @classmethod
    def shortlist_prompt(cls) -> str:
        return TRANCHE_PROMPT

    @classmethod
    def prompt(cls) -> str:
        return """
Extract the repayment details:
- Period type
- Number of periods
- Repayment amount
- Repayment percentage
- Begin date
"""


class TrancheBank(BaseModel):
    lender_name: str
    primary_role: Literal["Admin Agent", "Co-Admin Agent", "Syndication Agents"]
    lead_arranger: bool = False
    agent_only: bool = False
    agent_co_agent: bool = False
    role: Literal["Bookrunner", "Participant"]
    share_percent: float = 0.0
    min_bank_commitment: float = 0.0
    max_bank_commitment: float = 0.0


class TrancheBankList(BaseModel):
    banks: list[TrancheBank]

    @classmethod
    def shortlist_prompt(cls) -> str:
        return """
Tranche Bank Information:
We need to extract all of the banks involved. We need to extract the lender names, primary roles, lead arranger status, agent only status, agent/co-agent status, role, share percentages, and minimum and maximum bank commitments, and any other relevant information.
"""

    @classmethod
    def prompt(cls) -> str:
        return """
Extract the lender detail for each lender:
- Lender names
- Primary roles
- Lead Arranger status
- Agent Only status
- Agent/Co-Agent status
- Specific role
- Share percentages and commitment amounts
- Minimum and maximum bank commitment amounts
"""


BaseRate = Literal[
    "Prime Rate",
    "LIBOR",
    "SOFR",
    "EURIBOR",
    "SONIA",
    "EONIA",
    "Federal Funds",
    "Treasury Bill",
    "RFR",
]
FeeType = Literal[
    "Commitment Fee",
    "Arrangement Fee",
    "Utilization Fee",
    "Non-Utilization Fee",
    "Agency Fee",
    "Prepayment Fee",
    "Extension Fee",
    "Amendment Fee",
    "Letter of Credit Fee",
    "Ticking Fee",
    "Syndication Fee",
    "Legal Fee",
]


class InterestAndFees(BaseModel):
    base_rate: BaseRate
    fee_type: FeeType
    spread: float
    floor_base_rate_percent: float
    max_fee: float
    default_rate: float = 0.0


class AllInterestAndFees(BaseModel):
    interests_and_fees: list[InterestAndFees]

    @classmethod
    def shortlist_prompt(cls) -> str:
        return """
Interest and Fees:
Each loan agreement is tied with multiple fees and we need to identify those information. We also look forward to the information about the Base rate type, spread, adjustment of spread, fee type, floor base rate percentage, and maximum fee amounts. This information will be used to help us identify the most appropriate interest rate for the loan.
"""

    @classmethod
    def prompt(cls) -> str:
        return """
Extract the interest and fee details:
- Base rates
- Spreads for each base rate
- Floor rate percentage
- Fee types
- Maximum fee amounts
- Default rate
"""


class FinancialCovenant(BaseModel):
    ratio_type: Literal[
        "Total Leverage Ratio",
        "Interest Coverage Ratio",
        "Debt Service Coverage Ratio",
        "Fixed Charge Coverage Ratio",
        "Net Leverage Ratio",
        "Senior Leverage Ratio",
        "Current Ratio",
        "Quick Ratio",
        "Cash Flow Coverage Ratio",
        "Debt to Equity Ratio",
        "Tangible Net Worth",
    ]
    level: str = Field(
        description="Target level or threshold for the ratio, e.g. '4.0 to 1.0' or '< 3.5x'",
    )
    start_date: datetime
    end_date: datetime
    dividend_restriction: bool
    covenant_type: Literal[
        "Leverage Ratio",
        "Interest Coverage Ratio",
        "Debt Service Coverage Ratio",
        "Fixed Charge Coverage Ratio",
        "Liquidity Ratio",
        "Net Worth",
        "Capital Expenditure Limit",
        "Minimum EBITDA",
        "Cash Flow Coverage",
        "Debt to Equity Ratio",
        "Asset Coverage Ratio",
    ]
    capex_carryover: bool
    net_worth_type: Literal["Tangible Net Worth", "Total Net Worth", "Adjusted Net Worth"]
    base_amount: float = 0.0
    percentage_of_net_income: float = 0.0
    build_up: str = ""

    @field_serializer("start_date")
    def serialize_start_date(self, value: datetime) -> str:
        return value.strftime("%d-%m-%Y")

    @field_serializer("end_date")
    def serialize_end_date(self, value: datetime) -> str:
        return value.strftime("%d-%m-%Y")

    @classmethod
    def shortlist_prompt(cls) -> str:
        return """
Financial Covenants:
This information is usually mentioned in the Covenant section of the credit agreement. Financial covenants are the ratio type and information regarding the level of the ratios applies to the agreement. Also include the start date, end date, dividend restrictions, covenant type, capex carryover, net worth details, build up, and any other relevant information.
"""

    @classmethod
    def prompt(cls) -> str:
        return """
Extract the financial covenant details:
- Ratio type
- Level
- Start date
- End date
- Dividend restrictions
- Covenant type
- CapEx carryover
- Net worth details
- Base amount
- Percentage of net income
- Build up
"""


class CovenantsAndAmendmentVoting(BaseModel):
    prepayment_type: Literal["Soft Call", "Hard Call", "Make-Whole", "None"]
    prepayment_percent: float
    prepayment_comment: str

    @classmethod
    def shortlist_prompt(cls) -> str:
        return """
Covenants and Amendment Voting:
Look for sections in the credit agreement that discuss prepayment terms, covenants, and voting rights for amendments. We need to identify information about prepayment types, percentages, and any related comments or conditions.
"""

    @classmethod
    def prompt(cls) -> str:
        return """
Extract the covenants and amendment voting details:
- Prepayment type
- Prepayment percentage
- Prepayment comment
"""


GridOperator = Literal["<", "<=", ">", ">="]

CreditRating = Literal[
    "AAA",
    "AA+",
    "AA",
    "AA-",
    "A+",
    "A",
    "A-",
    "BBB+",
    "BBB",
    "BBB-",
    "BB+",
    "BB",
    "BB-",
    "B+",
    "B",
    "B-",
    "CCC+",
    "CCC",
    "CCC-",
    "CC",
    "C",
    "D",
]

GridMinMax = Literal["Min", "Max"]


class PerformanceType(BaseModel):
    performance_price_code: Literal[
        "Leverage Ratio",
        "Interest Coverage Ratio",
        "Debt to EBITDA Ratio",
        "Fixed Charge Coverage Ratio",
        "Senior Debt to EBITDA Ratio",
        "Ratings Based",
        "S&P",
        "Moody's",
        "Fitch",
    ]
    column_number: int


class PerformancePricing(BaseModel):
    split_rated: Literal["Higher Rating Applies", "Lower Rating Applies"]
    split_by_gt_1_lev: Literal[
        "Below the higher rating applies",
        "Above the lower rating applies",
        "Intermediate rating applies",
    ]
    performance_type: PerformanceType
    grid_min_op: GridOperator
    grid_xyz_min: CreditRating
    grid_max_op: GridOperator
    grid_xyz_max: CreditRating

    @classmethod
    def shortlist_prompt(cls) -> str:
        return """
Performance Pricing:
Look for sections in the credit agreement that discuss performance-based pricing or pricing grids. We need to identify information about split ratings, performance types, and grid details for pricing adjustments based on financial performance or credit ratings.
"""

    @classmethod
    def prompt(cls) -> str:
        return """
Extract the performance pricing details:
- Split rating policy
- Policy for splits greater than 1 level
- Performance price code and column number
- Grid minimum and maximum operators and values
- Grid minimum and maximum values for XYZ ratings
"""

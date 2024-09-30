from datetime import datetime

from pydantic import BaseModel, field_serializer

# date_type = Annotated[str, lambda x: x.strftime("%d-%m-%Y")]

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


class TrancheBankList(BaseModel):
    lender_name: str
    primary_role: str
    lead_arranger: bool = False
    agent_only: bool = False
    agent_co_agent: bool = False
    role: str
    share_percent: float = 0.0
    min_bank_commitment: float = 0.0
    max_bank_commitment: float = 0.0

    @classmethod
    def shortlist_prompt(cls) -> str:
        return TRANCHE_PROMPT

    @classmethod
    def prompt(cls) -> str:
        return """
Extract the lender details:
- Lender names
- Primary roles
- Lead Arranger status
- Agent Only status
- Agent/Co-Agent status
- Specific role
- Share percentages and commitment amounts
- Minimum and maximum bank commitment amounts
"""


class TrancheOptionsRepayment(BaseModel):
    period: str
    number_of_periods: int
    amount: float
    percent: float
    begin_date: str

    @classmethod
    def shortlist_prompt(cls) -> str:
        return TRANCHE_PROMPT

    @classmethod
    def prompt(cls) -> str:
        return """
Extract the repayment details:
- Period type
- Number of periods (e.g., 12)
- Repayment amount (e.g., $100,000)
- Repayment percentage (e.g., 10%)
- Begin date
"""


class InterestAndFees(BaseModel):
    base_rate: list[str]
    spread: list[float]
    floor_br_percent: float
    fee_type: str
    max_fee: float
    default_rate: float = 0.0

    @classmethod
    def prompt(cls) -> str:
        return """
Extract the interest and fee details:
- Base rates
- Spreads for each base rate
- Floor rate percentage (e.g., 0.5%)
- Fee types
- Maximum fee amounts (e.g., $100,000)
- Default rate
"""


class TrancheMain(BaseModel):
    tranche_type: str
    distribution_method: str
    maturity_date: str
    currency: list[str]
    min_amount: float
    max_amount: float
    purpose: str
    lt_amount: float = 0.0
    lt_date: str = ""
    repayment_type: str
    swingline_loan: float

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


class CovenantsAndAmendmentVoting(BaseModel):
    vote_100_percent: bool
    margin_reduction: float
    tenor_extension: float
    amount_reduction: float
    guarantor_release: float
    required_lenders: float

    @classmethod
    def prompt(cls) -> str:
        return """
Extract the covenants and amendment voting details:
- 100% vote requirements
- Percentages for margin reduction, tenor extension, amount reduction, and guarantor release requirements
- Required lenders percentage
"""


class PerformancePricing(BaseModel):
    split_rated: str
    split_by_gt_1_lev: str
    performance_price_code: str
    column_number: int
    grid_min_op: str
    grid_xyz_min: str
    grid_max_op: str
    grid_xyz_max: str

    @classmethod
    def prompt(cls) -> str:
        return """
Extract the performance pricing details:
- Split rating policy
- Policy for splits greater than 1 level
- Performance price code
- Column number
- Grid minimum and maximum operators and values
"""


class PerformancePricingGrid(BaseModel):
    operator: str
    sp_rating: str
    abr_spread: float
    term_benchmark_rfr_spread: float
    commitment_fee_rate: float

    @classmethod
    def prompt(cls) -> str:
        return """
Extract the performance pricing grid details:
- Operator
- S&P rating
- ABR spread
- Term Benchmark and RFR spread
- Commitment fee rate
"""


class FinancialCovenant(BaseModel):
    ratio_type: str
    level: float
    start_date: str
    end_date: str
    dividend_restriction: bool
    covenant_type: str = ""
    capex_carryover: str = ""
    net_worth_type: str = ""
    base_amount: float = 0.0
    percentage_of_net_income: float = 0.0
    build_up: str = ""

    @classmethod
    def shortlist_prompt(cls) -> str:
        return """
Financial Covenants:
This information is usually mentioned in the Covenant section of the credit agreement. Financial covenants are the ratio type and information regarding the level of the ratios applies to the agreement. Also include the start date, end date, dividend restrictions, covenant type, capex carryover, net worth details, and any other relevant information.
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


class LoanAgreement(BaseModel):
    deal_main: DealMain
    tranche_bank_list: list[TrancheBankList]
    tranche_options_repayment: TrancheOptionsRepayment
    interest_and_fees: InterestAndFees
    tranche_main: TrancheMain
    covenants_and_amendment_voting: CovenantsAndAmendmentVoting
    performance_pricing: PerformancePricing
    performance_pricing_grid: list[PerformancePricingGrid]
    financial_covenant: FinancialCovenant

    @classmethod
    def prompt(cls) -> str:
        return """
Compile a comprehensive summary of the entire loan agreement:
- Include all information from the above sections
- Ensure all key loan terms, parties, amounts, dates, and conditions are captured
- Pay attention to any additional comments or special provisions mentioned throughout the document
"""

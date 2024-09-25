import json
from pathlib import Path
from time import sleep

from loguru import logger
from pydantic import BaseModel

from dreamai.ai import ModelName
from dreamai.dialog import Dialog, user_message
from dreamai.dialog_models import SourcedResponse, model_with_typed_response
from dreamai.md_utils import MarkdownData, data_to_md
from dreamai.utils import to_camel

MODEL = ModelName.GEMINI_FLASH
CHUNKS_LIMIT = 1.0


DATA_FILE = "hp.md"
DATA_JSON = "hp.json"
DIALOG_JSON = "hp_dialog.json"
RES_JSON = "hp_res.json"


if not Path(DATA_JSON).exists():
    data = data_to_md(data=DATA_FILE, chunk_size=450, chunk_overlap=50)[0]
    with open(DATA_JSON, "w") as f:
        json.dump(data.model_dump(), f, indent=2)  # type: ignore
else:
    with open(DATA_JSON, "r") as f:
        data = MarkdownData(**json.load(f))

chunks = data.chunks[: int(len(data.chunks) * CHUNKS_LIMIT)]


def extract(user: str, response_type: list | type, name: str, model: ModelName = MODEL):
    dialog = Dialog(
        task="You are a world-class AI financial advisor. Your task is to provide a detailed analysis of a loan application and extract the entities that I want. With sources if you can.",
        chat_history=[
            user_message(
                json.dumps([chunk.model_dump(exclude={"metadata"}) for chunk in data.chunks])
            )
        ],
    )
    creator, kwargs = dialog.creator_with_kwargs(model=model, user=user)
    response_model = model_with_typed_response(
        to_camel(f"Sourced{name.title()}"), response_type, base=SourcedResponse
    )
    res = creator.create(
        **kwargs,
        response_model=response_model,
        validation_context={
            "documents": [chunk.model_dump(exclude={"metadata"}) for chunk in data.chunks]
        },
    )
    # dialog.add_messages([assistant_message(str(res))])
    # dialog.save(name=DIALOG_JSON)
    res_so_far = {}
    if Path(RES_JSON).exists():
        with open(RES_JSON, "r") as f:
            res_so_far = json.load(f)
    res_so_far[name.lower()] = res.model_dump()  # type: ignore
    with open(RES_JSON, "w") as f:
        json.dump(res_so_far, f, indent=2)
    return res


class DealMain(BaseModel):
    borrower_name: str
    purpose: str
    min_commitment: float
    max_commitment: float
    signing_date: str
    refinancing: bool

    @classmethod
    def prompt(cls) -> str:
        return """
Extract the main deal information:
- Borrower name (look for "HEWLETT PACKARD ENTERPRISE COMPANY" or similar)
- Purpose (e.g., "General Corporate Purposes")
- Commitment amounts (min and max, look for numbers around 5,250,000,000)
- Signing date (format: MM/DD/YYYY)
- Refinancing status (Y/N)
- Commitment currencies (look for USD, GBP, EUR)
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
    def prompt(cls) -> str:
        return """
List all lenders and their roles:
- Lender names (e.g., "JPMORGAN CHASE BANK, N.A.", "CITIBANK, N.A.")
- Primary roles (e.g., Admin Agent, Co-Administrative Agent)
- Lead Arranger status (Y/N)
- Agent Only status (Y/N)
- Agent/Co-Agent status (Y/N)
- Specific role (e.g., Bookrunner, Participant)
- Share percentages and commitment amounts if available
"""


class TrancheOptionsRepayment(BaseModel):
    period: str
    number_of_periods: int
    amount: float
    percent: float
    begin_date: str

    @classmethod
    def prompt(cls) -> str:
        return """
Provide the repayment details:
- Period type (e.g., Bullet)
- Number of periods
- Repayment amount
- Repayment percentage
- Begin date (format: MM/DD/YYYY)
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
Extract interest and fee information:
- Base rates (e.g., Prime Rate, RFR)
- Spreads for each base rate
- Floor rate percentage
- Fee types (e.g., Commitment fee)
- Maximum fee amounts
- Default rate if available
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
    def prompt(cls) -> str:
        return """
Summarize the main tranche information:
- Tranche type (e.g., Revolver)
- Distribution method (e.g., Syndication)
- Maturity date (format: MM/DD/YYYY)
- Currencies (e.g., USD, GBP, EUR)
- Minimum and maximum amounts
- Purpose
- LT amount and date if applicable
- Repayment type (e.g., Bullet)
- Swingline loan amount if available
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
Extract voting percentages for amendments:
- 100% vote requirements (Y/N)
- Percentages for margin reduction, tenor extension, amount reduction, and guarantor release
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
Provide details on performance-based pricing:
- Split rating policy (e.g., "Higher Rating Applies")
- Policy for splits greater than 1 level
- Performance price code (e.g., S&P)
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
List the pricing tiers based on ratings:
- S&P ratings (e.g., A-, BBB+, BBB)
- ABR spreads in basis points
- Term Benchmark and RFR spreads in basis points
- Commitment fee rates in basis points
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
    net_income_percent: float = 0.0
    build_up: str = ""

    @classmethod
    def prompt(cls) -> str:
        return """
Extract financial covenant details:
- Ratio types (e.g., Total Leverage Ratio)
- Covenant levels (e.g., 4.00 to 1.0)
- Start and end dates (format: MM/DD/YYYY)
- Dividend restrictions (Y/N)
- Additional covenant types and levels
- Capex carryover information
- Net worth details if applicable
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


for model in [
    DealMain,
    TrancheBankList,
    TrancheOptionsRepayment,
    InterestAndFees,
    TrancheMain,
    CovenantsAndAmendmentVoting,
    PerformancePricing,
    FinancialCovenant,
]:
    res = extract(user=model.prompt(), response_type=model, name=model.__name__)
    logger.success(model.__name__)
    sleep(3)


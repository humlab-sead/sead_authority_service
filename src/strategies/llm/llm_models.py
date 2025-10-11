"""Pydantic models for LLM-based reconciliation responses"""

from pydantic import BaseModel, Field


class Candidate(BaseModel):
    """Individual candidate match from lookup data"""

    id: str = Field(description="The lookup id (must be from lookup data)")
    value: str = Field(description="The lookup value (verbatim from lookup data)")
    score: float = Field(description="Confidence score between 0 and 1 with two decimals")
    reasons: list[str] = Field(description="Short array of explanatory factors (2-4 bullets)")


class ReconciliationResult(BaseModel):
    """Result for a single input value"""

    input_id: str = Field(description="Original input id")
    input_value: str = Field(description="Original input value")
    candidates: list[Candidate] = Field(description="Up to 5 candidates ordered best to worst")


class ReconciliationResponse(BaseModel):
    """Complete response array for all input values"""

    results: list[ReconciliationResult] = Field(description="Results for each input value")

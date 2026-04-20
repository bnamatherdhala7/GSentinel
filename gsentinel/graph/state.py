from typing import TypedDict, Optional
from enum import Enum


class FulfillmentStatus(str, Enum):
    AUTO_FIXED = "AUTO_FIXED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    NOTIFIED = "NOTIFIED"


class FulfillmentState(TypedDict):
    raw_input: str
    employee_id: Optional[str]
    error_code: Optional[str]
    error_description: Optional[str]
    field_affected: Optional[str]
    submitted_value: Optional[str]
    corrected_value: Optional[str]
    confidence_score: float
    action_card: Optional[str]
    status: Optional[FulfillmentStatus]
    trace: list

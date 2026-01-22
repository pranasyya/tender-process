from pydantic import BaseModel

class TenderResponse(BaseModel):
    tender_id: str | None = None
    title: str | None = None
    issuing_authority: str | None = None
    category: str | None = None
    location: str | None = None
    submission_deadline: str | None = None
    emd: str | None = None
    tender_fee: str | None = None
    contract_duration: str | None = None
    scope_of_work: str | None = None
    confidence: int = 0
    decision: str = "Needs Review"

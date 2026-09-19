from pydantic import BaseModel, Field
class IncidentCreate(BaseModel):
    service: str = Field(min_length=1,max_length=120)
    severity: str = Field(pattern=r"^SEV[0-4]$")
    summary: str = Field(min_length=1,max_length=10000)
class ExecuteRequest(BaseModel):
    instruction: str
    approval_token: str | None = None
class RunbookIn(BaseModel):
    id: str
    service: str
    title: str
    text: str
class RunbookRequest(BaseModel):
    runbooks: list[RunbookIn]

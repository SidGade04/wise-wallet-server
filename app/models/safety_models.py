from pydantic import BaseModel

class SafetyCheck(BaseModel):
    allowed: bool
    reason: str = ""

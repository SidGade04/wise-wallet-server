from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AssistantQuery(BaseModel):
    question: str = Field(..., min_length=1)
    context: Optional[Dict[str, Any]] = None


class AssistantResponse(BaseModel):
    answer: str
    citations: List[Any] = Field(default_factory=list)
    used_tools: List[Any] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

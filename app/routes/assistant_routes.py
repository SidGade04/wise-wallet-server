import asyncio
import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException

from ..core.auth import get_current_user
from ..models.assistant_models import AssistantQuery, AssistantResponse
from ..services.assistant_service import AssistantService
from ..services.plaid_service import PlaidService

logger = logging.getLogger(__name__)
router = APIRouter()

_assistant: AssistantService | None = None


def get_assistant_service() -> AssistantService:
    global _assistant
    if _assistant is None:
        try:
            _assistant = AssistantService(PlaidService())
        except Exception as e:
            logger.error("Failed to initialize AssistantService: %s", e)
            raise HTTPException(status_code=500, detail="Assistant service not available")
    return _assistant


@router.post("/query", response_model=AssistantResponse)
async def query_assistant(
    body: AssistantQuery,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> AssistantResponse:
    try:
        previous = (body.context or {}).get("previous_messages") or []
        result = await asyncio.to_thread(
            get_assistant_service().query,
            current_user["user_id"],
            body.question,
            previous,
        )
        return AssistantResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Assistant query failed for %s: %s", current_user.get("user_id"), e)
        raise HTTPException(status_code=500, detail="Failed to get assistant response")

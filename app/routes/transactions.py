# server/routers/test.py (or whichever router you prefer)
from fastapi import APIRouter, Depends
from typing import List, Dict
from pydantic import BaseModel # Use Pydantic for validation
# Assuming your user model and dependency live here
from ..auth import get_current_user
from ..models import User # Replace with your actual user model path
from ..services.embedding_service import ingest_transactions_to_supabase

router = APIRouter(prefix="/test", tags=["Test"])

# 2. Define a Pydantic Model for the incoming test data
class TestTransaction(BaseModel):
    date: str
    amount: float
    merchant_name: str
    category: List[str]
    transaction_id: str

@router.post("/ingest-test-transactions")
def test_ingestion(
    transactions: List[TestTransaction],
    user: User = Depends(get_current_user)
):
    """
    Endpoint to test the vector ingestion service with mock transaction data.
    Requires a valid JWT token.
    """
    
    # Supabase uses UUIDs for auth.users, so we assume User.id is the UUID string.
    user_uuid = str(user.id) 
    
    # Convert Pydantic models back to simple dictionaries for the service
    transactions_data = [tx.dict() for tx in transactions]
    
    result = ingest_transactions_to_supabase(
        transactions=transactions_data,
        user_uuid=user_uuid
    )
    
    return result
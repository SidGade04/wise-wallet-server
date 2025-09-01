from fastapi import APIRouter, Depends, HTTPException, status
import logging
from typing import Dict, Any

from ..services.plaid_service import PlaidService
from ..core.auth import get_current_user, verify_user_access
from ..models.plaid_models import LinkTokenRequest, PublicTokenExchangeRequest

logger = logging.getLogger(__name__)
router = APIRouter()

# Lazy service initialization to prevent import-time errors
_plaid_service = None

def get_plaid_service():
    global _plaid_service
    if _plaid_service is None:
        try:
            _plaid_service = PlaidService()
        except Exception as e:
            logger.error(f"Failed to initialize PlaidService: {e}")
            raise HTTPException(status_code=500, detail="Plaid service not available")
    return _plaid_service

@router.post("/create_link_token")
async def create_link_token(
    request: LinkTokenRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a link token for Plaid Link initialization."""
    try:
        user_id = current_user["user_id"]
        plaid_service = get_plaid_service()
        result = await plaid_service.create_link_token(user_id, request.client_name)
        return result
    except Exception as e:
        logger.error(f"Error creating link token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create link token: {str(e)}")


@router.post("/exchange_public_token")
async def exchange_public_token(
    payload: PublicTokenExchangeRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Exchange public token for access token and store bank item."""
    try:
        user_id = current_user["user_id"]
        plaid_service = get_plaid_service()
        result = await plaid_service.exchange_public_token(
            payload.public_token, 
            user_id, 
            payload.metadata
        )
        return result
    except Exception as e:
        logger.error(f"Error exchanging public token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to exchange public token: {str(e)}")


@router.get("/accounts/user/{user_id}")
async def get_accounts_by_user(
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get all accounts for a user."""
    try:
        verify_user_access(current_user["user_id"], user_id)
        plaid_service = get_plaid_service()
        accounts = await plaid_service.get_user_bank_accounts(user_id)
        return {"accounts": accounts}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user accounts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch accounts: {str(e)}")


@router.get("/user_transactions/{user_id}")
async def get_user_transactions(
    user_id: str,
    days: int = 30,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get all transactions for a user."""
    try:
        verify_user_access(current_user["user_id"], user_id)
        plaid_service = get_plaid_service()
        result = await plaid_service.get_user_transactions(user_id, days)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user transactions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch transactions: {str(e)}")


@router.post("/sync/{item_id}")
async def sync_item_transactions(
    item_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Manually sync transactions for a specific item."""
    try:
        user_id = current_user["user_id"]
        plaid_service = get_plaid_service()
        result = await plaid_service.sync_item_transactions(user_id, item_id)
        return result
    except Exception as e:
        logger.error(f"Error syncing item {item_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to sync transactions: {str(e)}")


@router.delete("/remove/{item_id}")
async def remove_bank_item(
    item_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Remove a bank item and all associated data."""
    try:
        user_id = current_user["user_id"]
        plaid_service = get_plaid_service()
        result = await plaid_service.remove_bank_item(user_id, item_id)
        return result
    except Exception as e:
        logger.error(f"Error removing item {item_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to remove bank item: {str(e)}")


@router.get("/debug/auth")
async def debug_auth(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Debug endpoint to check authentication."""
    from datetime import datetime
    return {
        "user_id": current_user["user_id"],
        "email": current_user.get("email"),
        "role": current_user.get("role"),
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/investments/{item_id}/holdings")
async def get_investment_holdings(
    item_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get investment holdings for a specific item"""
    try:
        user_id = current_user["user_id"]
        plaid_service = get_plaid_service()
        return await plaid_service.get_investment_holdings(user_id, item_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching investment holdings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch holdings: {str(e)}")


@router.get("/investments/{item_id}/transactions")
async def get_investment_transactions(
    item_id: str,
    days: int =30,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get investment transactions for a specific item"""
    try:
        user_id = current_user["user_id"]
        plaid_service = get_plaid_service()
        return await plaid_service.get_investment_transactions(user_id, item_id, days)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching investment transactions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch investment transactions: {str(e)}")

# Debug endpoints for troubleshooting profile issues
@router.get("/debug/profile/{user_id}")
async def debug_user_profile(
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Debug endpoint to check user profile status."""
    try:
        # Check if the requesting user is the same as the target user
        if current_user["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Can only check your own profile")
        
        # Get profile from profiles table
        profile_result = supabase.table("profiles").select("*").eq("user_id", user_id).single().execute()
        
        # Get bank items from bank_items table
        bank_items_result = supabase.table("bank_items").select("*").eq("user_id", user_id).execute()
        
        return {
            "profile": profile_result.data,
            "bank_items": bank_items_result.data,
            "profile_has_bank": profile_result.data.get("has_connected_bank") if profile_result.data else None,
            "bank_items_count": len(bank_items_result.data) if bank_items_result.data else 0
        }
    except Exception as e:
        logger.error(f"Error in debug profile endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Debug failed: {str(e)}")

@router.post("/debug/update-profile/{user_id}")
async def debug_update_profile(
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Debug endpoint to manually update profile has_connected_bank status."""
    try:
        # Check if the requesting user is the same as the target user
        if current_user["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Can only update your own profile")
        
        # Update profile to mark bank as connected
        update_result = supabase.table("profiles").update({
            "has_connected_bank": True
        }).eq("user_id", user_id).execute()
        
        if not update_result.data:
            raise HTTPException(status_code=400, detail="Failed to update profile")
        
        return {
            "message": "Profile updated successfully",
            "updated_profile": update_result.data[0] if update_result.data else None
        }
    except Exception as e:
        logger.error(f"Error in debug update profile endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")

@router.post("/debug/create-profile/{user_id}")
async def debug_create_profile(
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Debug endpoint to manually create a profile for a user who doesn't have one."""
    try:
        # Check if the requesting user is the same as the target user
        if current_user["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Can only create your own profile")
        
        # Check if profile already exists
        existing_profile = supabase.table("profiles").select("*").eq("user_id", user_id).execute()
        
        if existing_profile.data and len(existing_profile.data) > 0:
            return {
                "message": "Profile already exists",
                "profile": existing_profile.data[0]
            }
        
        # Try to get user info from auth
        try:
            user_info = supabase.auth.admin.get_user_by_id(user_id)
            if user_info.user:
                profile_data = {
                    "user_id": user_id,
                    "email": user_info.user.email,
                    "full_name": user_info.user.user_metadata.get('full_name') or user_info.user.user_metadata.get('name') or user_info.user.email.split('@')[0],
                    "has_connected_bank": False
                }
            else:
                # Fallback data
                profile_data = {
                    "user_id": user_id,
                    "email": "unknown@example.com",
                    "full_name": "Unknown User",
                    "has_connected_bank": False
                }
        except Exception as e:
            logger.warning(f"Could not get user info: {e}")
            # Fallback data
            profile_data = {
                "user_id": user_id,
                "email": "unknown@example.com",
                "full_name": "Unknown User",
                "has_connected_bank": False
            }
        
        # Create profile
        result = supabase.table("profiles").insert(profile_data).execute()
        
        if not result.data:
            raise HTTPException(status_code=400, detail="Failed to create profile")
        
        return {
            "message": "Profile created successfully",
            "profile": result.data[0]
        }
        
    except Exception as e:
        logger.error(f"Error in debug create profile endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Create failed: {str(e)}")
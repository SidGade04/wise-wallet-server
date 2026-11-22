"""
Internal AI endpoints for the AI service to access user data.

These endpoints are protected by internal service tokens and provide
read-only access to user financial data for AI analysis.
"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Header, Query

from app.services.db import fetch_one, fetch_all
from app.core.auth import verify_internal_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/ai", tags=["internal-ai"])

@router.get("/users/{user_id}/summary")
async def get_user_summary(
    user_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    _: bool = Depends(verify_internal_token)
) -> Dict[str, Any]:
    """
    Get user financial summary for AI analysis.
    
    Returns:
        - Total account balance
        - Recent transactions count
        - Top spending categories
        - Monthly spending amount
    """
    try:
        logger.info(f"Getting user summary for {user_id}, {days} days")
        
        # Get total balance from all accounts
        balance_query = """
            SELECT COALESCE(SUM(current_balance), 0) as total_balance
            FROM accounts 
            WHERE user_id = :user_id AND account_type = 'depository'
        """
        balance_result = await fetch_one(balance_query, user_id=user_id)
        total_balance = float(balance_result['total_balance']) if balance_result else 0.0
        
        # Get recent transactions count
        start_date = datetime.now() - timedelta(days=days)
        transactions_query = """
            SELECT COUNT(*) as transaction_count
            FROM transactions 
            WHERE user_id = :user_id AND date >= :start_date
        """
        transactions_result = await fetch_one(
            transactions_query, 
            user_id=user_id, 
            start_date=start_date
        )
        transaction_count = transactions_result['transaction_count'] if transactions_result else 0
        
        # Get top spending categories
        categories_query = """
            SELECT 
                COALESCE(category, 'Uncategorized') as category,
                COUNT(*) as transaction_count,
                SUM(ABS(amount)) as total_amount
            FROM transactions 
            WHERE user_id = :user_id 
                AND date >= :start_date 
                AND amount < 0
            GROUP BY category
            ORDER BY total_amount DESC
            LIMIT 5
        """
        categories_result = await fetch_all(
            categories_query,
            user_id=user_id, 
            start_date=start_date
        )
        
        top_categories = [
            {
                "category": row['category'],
                "transaction_count": row['transaction_count'],
                "total_amount": float(row['total_amount'])
            }
            for row in categories_result
        ]
        
        # Calculate monthly spending
        monthly_spend_query = """
            SELECT SUM(ABS(amount)) as monthly_spend
            FROM transactions 
            WHERE user_id = :user_id 
                AND date >= :start_date 
                AND amount < 0
        """
        monthly_spend_result = await fetch_one(
            monthly_spend_query,
            user_id=user_id, 
            start_date=start_date
        )
        monthly_spend = float(monthly_spend_result['monthly_spend']) if monthly_spend_result and monthly_spend_result['monthly_spend'] else 0.0
        
        return {
            "user_id": user_id,
            "period_days": days,
            "total_balance": total_balance,
            "recent_transactions_count": transaction_count,
            "top_categories": top_categories,
            "monthly_spend": monthly_spend,
            "summary_date": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting user summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user summary: {str(e)}")

@router.get("/transactions")
async def get_transactions(
    user_id: str = Query(..., description="User ID"),
    start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of transactions"),
    _: bool = Depends(verify_internal_token)
) -> Dict[str, Any]:
    """
    Get transactions for AI analysis with optional filters.
    
    Returns:
        - List of transactions with metadata
        - Total count and filtered count
    """
    try:
        logger.info(f"Getting transactions for {user_id}")
        
        # Build base query
        base_query = """
            SELECT 
                transaction_id,
                account_id,
                amount,
                date,
                name as description,
                category,
                merchant_name,
                account_name
            FROM transactions t
            LEFT JOIN accounts a ON t.account_id = a.account_id
            WHERE t.user_id = :user_id
        """
        
        params = {"user_id": user_id}
        
        # Add date filters
        if start:
            base_query += " AND t.date >= :start_date"
            params["start_date"] = start
        
        if end:
            base_query += " AND t.date <= :end_date"
            params["end_date"] = end
        
        # Add category filter
        if category:
            base_query += " AND t.category = :category"
            params["category"] = category
        
        # Add ordering and limit
        base_query += " ORDER BY t.date DESC LIMIT :limit"
        params["limit"] = limit
        
        # Execute query
        result = await fetch_all(base_query, **params)
        
        transactions = [
            {
                "id": row['transaction_id'],
                "account_id": row['account_id'],
                "amount": float(row['amount']),
                "date": row['date'].isoformat() if row['date'] else None,
                "description": row['description'],
                "category": row['category'],
                "merchant_name": row['merchant_name'],
                "account_name": row['account_name']
            }
            for row in result
        ]
        
        # Get total count for the same filters (without limit)
        count_query = """
            SELECT COUNT(*)
            FROM transactions t
            WHERE t.user_id = :user_id
        """
        count_params = {"user_id": user_id}
        
        if start:
            count_query += " AND t.date >= :start_date"
            count_params["start_date"] = start
        
        if end:
            count_query += " AND t.date <= :end_date"
            count_params["end_date"] = end
        
        if category:
            count_query += " AND t.category = :category"
            count_params["category"] = category
        
        count_result = await fetch_one(count_query, **count_params)
        total_count = count_result['count'] if count_result else 0
        
        return {
            "user_id": user_id,
            "transactions": transactions,
            "total_count": total_count,
            "returned_count": len(transactions),
            "filters": {
                "start": start,
                "end": end,
                "category": category,
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting transactions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get transactions: {str(e)}")

@router.get("/categories/mapping")
async def get_category_mapping(
    transaction_id: str = Query(..., description="Transaction ID to explain"),
    _: bool = Depends(verify_internal_token)
) -> Dict[str, Any]:
    """
    Explain how a transaction was categorized.
    
    Returns:
        - Original transaction details
        - Mapped category and confidence
        - Reasoning for the mapping
    """
    try:
        logger.info(f"Getting category mapping for transaction {transaction_id}")
        
        # Get transaction details
        transaction_query = """
            SELECT 
                transaction_id,
                name as description,
                amount,
                date,
                category,
                merchant_name,
                account_name
            FROM transactions t
            LEFT JOIN accounts a ON t.account_id = a.account_id
            WHERE t.transaction_id = :transaction_id
        """
        
        result = await fetch_one(transaction_query, transaction_id=transaction_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        transaction = {
            "transaction_id": result['transaction_id'],
            "description": result['description'],
            "amount": float(result['amount']),
            "date": result['date'].isoformat() if result['date'] else None,
            "category": result['category'],
            "merchant_name": result['merchant_name'],
            "account_name": result['account_name']
        }
        
        # Generate explanation based on common patterns
        explanation = _generate_category_explanation(
            transaction["description"],
            transaction["merchant_name"],
            transaction["category"]
        )
        
        return {
            "transaction_id": transaction_id,
            "original_description": transaction["description"],
            "mapped_category": transaction["category"],
            "confidence": 0.85,  # Placeholder - would be calculated by ML model
            "reasoning": explanation,
            "transaction_details": transaction
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting category mapping: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get category mapping: {str(e)}")

def _generate_category_explanation(description: str, merchant: str, category: str) -> str:
    """Generate a human-readable explanation for category mapping."""
    
    # Common patterns for category mapping
    patterns = {
        "Food & Dining": [
            "restaurant", "cafe", "coffee", "food", "dining", "pizza", "burger",
            "starbucks", "mcdonalds", "subway", "kfc", "dominos"
        ],
        "Transportation": [
            "gas", "fuel", "uber", "lyft", "taxi", "bus", "train", "metro",
            "parking", "toll", "auto", "car", "vehicle"
        ],
        "Shopping": [
            "amazon", "walmart", "target", "store", "shop", "retail", "mall",
            "clothing", "apparel", "electronics", "home", "furniture"
        ],
        "Entertainment": [
            "movie", "cinema", "theater", "netflix", "spotify", "game", "gaming",
            "entertainment", "fun", "leisure", "recreation"
        ],
        "Healthcare": [
            "doctor", "hospital", "pharmacy", "medical", "health", "clinic",
            "dental", "vision", "prescription", "medicine"
        ],
        "Utilities": [
            "electric", "gas", "water", "internet", "phone", "cable", "utility",
            "power", "heating", "cooling"
        ],
        "Groceries": [
            "grocery", "supermarket", "food", "market", "fresh", "produce",
            "kroger", "safeway", "whole foods", "trader joe"
        ]
    }
    
    # Find matching patterns
    text_to_search = f"{description} {merchant}".lower()
    matched_patterns = []
    
    for cat, keywords in patterns.items():
        if any(keyword in text_to_search for keyword in keywords):
            matched_patterns.append(cat)
    
    if matched_patterns:
        if category in matched_patterns:
            return f"Transaction was categorized as '{category}' based on keywords found in the description and merchant name that match common patterns for this category."
        else:
            return f"Transaction was categorized as '{category}' based on merchant and description analysis. Alternative categories considered: {', '.join(matched_patterns)}."
    else:
        return f"Transaction was categorized as '{category}' based on merchant name and description analysis. This appears to be a standard categorization for this type of transaction."



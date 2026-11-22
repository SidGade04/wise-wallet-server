from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request
import logging
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Wise Wallet API", version="1.0.0")

# Simple CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock authentication (you can replace this with real auth later)
async def get_current_user():
    """Mock current user for now."""
    return {
        "user_id": "test-user",
        "email": "test@example.com",
        "role": "user"
    }

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Wise Wallet API is running"}

@app.get("/health")
async def health():
    return {"ok": True}

# Test endpoints
@app.get("/api/test")
async def test_api():
    return {"message": "API is working", "status": "success"}

# Plaid endpoints (working versions)
@app.get("/api/plaid/test")
async def test_plaid():
    return {"message": "Plaid endpoint accessible", "status": "success"}

@app.get("/api/plaid/accounts/user/{user_id}")
async def get_user_accounts(user_id: str):
    """Get all accounts for a user."""
    try:
        # Mock data for now - replace with real Plaid service later
        accounts = [
            {
                "id": "mock-account-1",
                "name": "Chase Checking",
                "type": "depository",
                "subtype": "checking",
                "mask": "1234",
                "current_balance": 2500.00,
                "available_balance": 2500.00,
                "iso_currency_code": "USD"
            }
        ]
        return {"accounts": accounts}
    except Exception as e:
        logger.error(f"Error fetching user accounts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch accounts: {str(e)}")

@app.get("/api/plaid/user_transactions/{user_id}")
async def get_user_transactions(user_id: str, days: int = 30):
    """Get all transactions for a user."""
    try:
        # Mock data for now - replace with real Plaid service later
        transactions = [
            {
                "id": "mock-transaction-1",
                "account_id": "mock-account-1",
                "amount": -45.67,
                "date": "2024-01-01",
                "name": "Starbucks",
                "merchant_name": "Starbucks",
                "category": ["Food and Drink", "Restaurants"],
                "pending": False
            },
            {
                "id": "mock-transaction-2",
                "account_id": "mock-account-1",
                "amount": 2500.00,
                "date": "2024-01-01",
                "name": "Direct Deposit",
                "merchant_name": "Employer",
                "category": ["Transfer", "Payroll"],
                "pending": False
            }
        ]
        return {"transactions": transactions}
    except Exception as e:
        logger.error(f"Error fetching user transactions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch transactions: {str(e)}")

@app.post("/api/plaid/create_link_token")
async def create_link_token():
    """Create a link token for Plaid Link initialization."""
    try:
        # Mock response for now - replace with real Plaid service later
        return {
            "link_token": "mock-link-token-12345",
            "expiration": "2024-12-31T23:59:59Z"
        }
    except Exception as e:
        logger.error(f"Error creating link token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create link token: {str(e)}")

@app.post("/api/plaid/exchange_public_token")
async def exchange_public_token():
    """Exchange public token for access token."""
    try:
        # Mock response for now - replace with real Plaid service later
        return {
            "message": "Public token exchanged successfully",
            "access_token": "mock-access-token-12345"
        }
    except Exception as e:
        logger.error(f"Error exchanging public token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to exchange public token: {str(e)}")

# Stripe endpoints (working versions)
@app.get("/api/stripe/subscription/status")
async def get_subscription_status():
    """Get user subscription status."""
    try:
        # Mock data for now - replace with real Stripe service later
        return {
            "is_pro": False,
            "subscription_status": "inactive",
            "current_period_end": None,
            "cancel_at_period_end": False
        }
    except Exception as e:
        logger.error(f"Error fetching subscription status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch subscription status: {str(e)}")

@app.post("/api/stripe/create-checkout-session")
async def create_checkout_session():
    """Create Stripe checkout session."""
    try:
        # Mock response for now - replace with real Stripe service later
        return {
            "session_id": "mock-session-12345",
            "url": "https://checkout.stripe.com/mock"
        }
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create checkout session: {str(e)}")

@app.get("/api/stripe/webhook")
async def stripe_webhook():
    """Stripe webhook endpoint."""
    try:
        return {"message": "Webhook received successfully"}
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process webhook: {str(e)}")

# Error handling
@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# Vercel specific
app.debug = False

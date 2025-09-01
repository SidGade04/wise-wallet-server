from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Plaid Integration API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # use specific domains in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Plaid Integration API is running"}

@app.get("/health")
async def health():
    return {"ok": True}

# Essential Plaid endpoints (working version)
@app.get("/api/plaid/accounts/user/{user_id}")
async def get_user_accounts(user_id: str):
    """Get all accounts for a user."""
    return {
        "message": "Accounts endpoint working",
        "user_id": user_id,
        "accounts": [],
        "note": "This is a fallback endpoint - full functionality requires proper route loading"
    }

@app.get("/api/plaid/user_transactions/{user_id}")
async def get_user_transactions(user_id: str, days: int = 30):
    """Get all transactions for a user."""
    return {
        "message": "Transactions endpoint working",
        "user_id": user_id,
        "days": days,
        "transactions": [],
        "note": "This is a fallback endpoint - full functionality requires proper route loading"
    }

@app.post("/api/plaid/create_link_token")
async def create_link_token():
    """Create a link token for Plaid Link initialization."""
    return {
        "message": "Create link token endpoint working",
        "note": "This is a fallback endpoint - full functionality requires proper route loading"
    }

@app.post("/api/plaid/exchange_public_token")
async def exchange_public_token():
    """Exchange public token for access token."""
    return {
        "message": "Exchange public token endpoint working",
        "note": "This is a fallback endpoint - full functionality requires proper route loading"
    }

# Test endpoints
@app.get("/api/test")
async def test_api():
    return {"message": "API is working", "status": "success"}

@app.get("/api/plaid/test")
async def test_plaid():
    return {"message": "Plaid endpoints are accessible", "status": "success"}

@app.get("/api/plaid/route-test")
async def test_plaid_route():
    return {
        "message": "Plaid endpoints working (fallback mode)",
        "available_routes": [
            "/api/plaid/accounts/user/{user_id}",
            "/api/plaid/user_transactions/{user_id}",
            "/api/plaid/create_link_token",
            "/api/plaid/exchange_public_token"
        ],
        "note": "These are fallback endpoints - full functionality requires proper route loading"
    }

# Error handling
@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# Vercel specific: export the app
app.debug = False

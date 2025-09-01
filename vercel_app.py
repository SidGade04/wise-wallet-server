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

# Try to import and initialize routes with error handling
try:
    # Import route modules without initializing services
    from app.routes import plaid_routes, stripe_routes, settings_routes
    
    # API groups
    app.include_router(plaid_routes.router, prefix="/api/plaid", tags=["plaid"])
    app.include_router(stripe_routes.router, prefix="/api/stripe", tags=["stripe"])
    app.include_router(settings_routes.router)
    
    logger.info("✅ All routes loaded successfully")
    routes_loaded = True
except Exception as e:
    logger.error(f"⚠️ Warning: Some routes failed to load: {str(e)}")
    routes_loaded = False

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Plaid Integration API is running"}

@app.get("/health")
async def health():
    return {"ok": True}

# Fallback endpoints (only used when real routes fail to load)
if not routes_loaded:
    @app.get("/api/plaid/accounts/user/{user_id}")
    async def get_user_accounts(user_id: str):
        """Get all accounts for a user."""
        return {
            "message": "Accounts endpoint working (fallback mode)",
            "user_id": user_id,
            "accounts": [],
            "note": "This is a fallback endpoint - full functionality requires proper route loading"
        }

    @app.get("/api/plaid/user_transactions/{user_id}")
    async def get_user_transactions(user_id: str, days: int = 30):
        """Get all transactions for a user."""
        return {
            "message": "Transactions endpoint working (fallback mode)",
            "user_id": user_id,
            "days": days,
            "transactions": [],
            "note": "This is a fallback endpoint - full functionality requires proper route loading"
        }

    @app.post("/api/plaid/create_link_token")
    async def create_link_token():
        """Create a link token for Plaid Link initialization."""
        return {
            "message": "Create link token endpoint working (fallback mode)",
            "note": "This is a fallback endpoint - full functionality requires proper route loading"
        }

    @app.post("/api/plaid/exchange_public_token")
    async def exchange_public_token():
        """Exchange public token for access token."""
        return {
            "message": "Exchange public token endpoint working (fallback mode)",
            "note": "This is a fallback endpoint - full functionality requires proper route loading"
        }

    @app.get("/api/stripe/subscription/status")
    async def get_subscription_status():
        """Get user subscription status."""
        return {
            "message": "Subscription status endpoint working (fallback mode)",
            "is_pro": False,
            "subscription_status": "inactive",
            "note": "This is a fallback endpoint - full functionality requires proper route loading"
        }

    @app.post("/api/stripe/create-checkout-session")
    async def create_checkout_session():
        """Create Stripe checkout session."""
        return {
            "message": "Create checkout session endpoint working (fallback mode)",
            "note": "This is a fallback endpoint - full functionality requires proper route loading"
        }

    @app.get("/api/stripe/webhook")
    async def stripe_webhook():
        """Stripe webhook endpoint."""
        return {
            "message": "Stripe webhook endpoint working (fallback mode)",
            "note": "This is a fallback endpoint - full functionality requires proper route loading"
        }

# Test endpoints
@app.get("/api/test")
async def test_api():
    return {
        "message": "API is working", 
        "status": "success",
        "routes_loaded": routes_loaded,
        "mode": "full_functionality" if routes_loaded else "fallback_mode"
    }

@app.get("/api/plaid/test")
async def test_plaid():
    return {"message": "Plaid endpoints are accessible", "status": "success"}

@app.get("/api/plaid/route-test")
async def test_plaid_route():
    if routes_loaded:
        return {
            "message": "✅ Real routes loaded successfully!",
            "status": "full_functionality",
            "note": "All real Plaid and Stripe endpoints are available"
        }
    else:
        return {
            "message": "⚠️ Using fallback endpoints",
            "status": "fallback_mode",
            "available_routes": {
                "plaid": [
                    "/api/plaid/accounts/user/{user_id}",
                    "/api/plaid/user_transactions/{user_id}",
                    "/api/plaid/create_link_token",
                    "/api/plaid/exchange_public_token"
                ],
                "stripe": [
                    "/api/stripe/subscription/status",
                    "/api/stripe/create-checkout-session",
                    "/api/stripe/webhook"
                ]
            },
            "note": "These are fallback endpoints - full functionality requires proper route loading"
        }

# Error handling
@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# Vercel specific: export the app
app.debug = False

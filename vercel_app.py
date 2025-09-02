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

# No fallback routes - we want to see if real routes work

# Test endpoints
@app.get("/api/test")
async def test_api():
    return {
        "message": "API is working", 
        "status": "success",
        "routes_loaded": routes_loaded,
        "mode": "full_functionality" if routes_loaded else "routes_failed"
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
            "message": "❌ Real routes failed to load",
            "status": "routes_failed",
            "note": "No endpoints available - routes failed to import"
        }

# Error handling
@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# Vercel specific: export the app
app.debug = False

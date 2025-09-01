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
except Exception as e:
    logger.error(f"⚠️ Warning: Some routes failed to load: {str(e)}")
    # Add fallback routes for when services are not available
    from fastapi import APIRouter
    
    fallback_router = APIRouter()
    
    @fallback_router.get("/api/plaid/status")
    async def plaid_status():
        return {"message": "Plaid service not available", "error": str(e)}
    
    @fallback_router.get("/api/stripe/status")
    async def stripe_status():
        return {"message": "Stripe service not available", "error": str(e)}
    
    app.include_router(fallback_router)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Plaid Integration API is running"}

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/api/test")
async def test_api():
    return {"message": "API is working", "status": "success"}

@app.get("/api/plaid/test")
async def test_plaid():
    return {"message": "Plaid routes are accessible", "status": "success"}

@app.post("/api/plaid/test")
async def test_plaid_post():
    return {"message": "Plaid POST routes are accessible", "status": "success"}

@app.get("/favicon.ico")
async def favicon():
    return {"message": "No favicon"}

@app.get("/favicon.png")
async def favicon_png():
    return {"message": "No favicon"}

@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# Vercel specific: export the app
app.debug = False

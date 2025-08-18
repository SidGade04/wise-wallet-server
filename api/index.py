from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request
import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routes.plaid_routes import router as plaid_router
from app.routes.stripe_routes import router as stripe_router
from app.routes import settings_routes

app = FastAPI(title="Wise Wallet API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API groups
app.include_router(plaid_router,     prefix="/api/plaid",  tags=["plaid"])
app.include_router(stripe_router,    prefix="/api/stripe", tags=["stripe"])
app.include_router(settings_routes.router)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Wise Wallet API is running", "status": "healthy", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"ok": True, "status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}

@app.get("/test")
async def test():
    return {"message": "Test endpoint working", "deployment": "successful"}

@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# Export the app for Vercel
app.debug = False

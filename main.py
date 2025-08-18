from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

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
    from app.routes.plaid_routes import router as plaid_router
    from app.routes.stripe_routes import router as stripe_router
    from app.routes import settings_routes
    
    # API groups
    app.include_router(plaid_router, prefix="/api/plaid", tags=["plaid"])
    app.include_router(stripe_router, prefix="/api/stripe", tags=["stripe"])
    app.include_router(settings_routes.router)
    
    print("✅ All routes loaded successfully")
except Exception as e:
    print(f"⚠️ Warning: Some routes failed to load: {str(e)}")
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

@app.get("/favicon.ico")
async def favicon():
    return {"message": "No favicon"}

@app.get("/favicon.png")
async def favicon_png():
    return {"message": "No favicon"}

@app.get("/{path:path}")
async def catch_all(path: str):
    return {"message": f"Endpoint /{path} not found", "status": "404"}

@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Plaid Integration API", version="1.0.0")

allow_origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "https://lemon-grass-096d3860f.6.azurestaticapps.net",
]
allow_origins += [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

route_load_errors: list[str] = []

def _load_router(name: str, loader) -> None:
    try:
        loader()
        logger.info("loaded router %s", name)
    except Exception as e:
        logger.exception("failed to load router %s", name)
        route_load_errors.append(f"{name}: {type(e).__name__}: {e}")

def _load_plaid():
    from app.routes import plaid_routes
    app.include_router(plaid_routes.router, prefix="/api/plaid", tags=["plaid"])

def _load_stripe():
    from app.routes import stripe_routes
    app.include_router(stripe_routes.router, prefix="/api/stripe", tags=["stripe"])

def _load_settings():
    from app.routes import settings_routes
    app.include_router(settings_routes.router)

def _load_assistant():
    from app.routes import assistant_routes
    app.include_router(assistant_routes.router, prefix="/api/assistant", tags=["assistant"])

_load_router("plaid", _load_plaid)
_load_router("stripe", _load_stripe)
_load_router("settings", _load_settings)
_load_router("assistant", _load_assistant)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Plaid Integration API is running"}

@app.get("/health")
async def health():
    return {"ok": True, "route_errors": route_load_errors}

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    

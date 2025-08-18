from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Wise Wallet API - Simple", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Wise Wallet API is running", "status": "healthy", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"ok": True, "status": "healthy"}

@app.get("/test")
async def test():
    return {"message": "Test endpoint working", "deployment": "successful"}

@app.get("/api/hello")
async def hello():
    return {"message": "Hello from Wise Wallet API!"}

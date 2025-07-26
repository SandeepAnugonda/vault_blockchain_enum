from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

# --- FastAPI App Setup ---
app = FastAPI(
    title="Vault Document Blockchain API",
    description="API for document management with blockchain-like features",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or restrict to your frontend domain(s)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers
from .routes import auth, documents

# Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Blockchain Documents"])

@app.get("/")
def read_root():
    return {"message": "API is running"}

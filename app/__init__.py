# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# import os
# from dotenv import load_dotenv

# load_dotenv()

# # --- FastAPI App Setup ---
# app = FastAPI(
#     title="Vault Document Blockchain API",
#     description="API for document management with blockchain-like features",
#     version="1.0.0"
# )


# # Improved CORS config for Swagger UI and browser compatibility
# origins = [
#     "http://localhost",
#     "http://localhost:8000",
#     "http://127.0.0.1:8000",
#     "*"  # keep only if testing
# ]
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,  # or ["*"] for testing
#     allow_origin_regex="https?://localhost(:[0-9]+)?",
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# from app.routes.documents import router as documents_router

# # Only include the documents router
# app.include_router(documents_router, prefix="/api/v1/documents", tags=["Blockchain Documents"])

# @app.get("/")
# def read_root():
#     return {"message": "API is running"}



from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from dotenv import load_dotenv
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('vault_blockchain.log')
    ]
)
logger = logging.getLogger(__name__)

# Load .env from project root
env_path = Path(__file__).resolve().parents[1] / '.env'
load_dotenv(dotenv_path=str(env_path))

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
# app.include_router(auth., prefix="/api/auth", tags=["Authentication"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Blockchain Documents"])
# app.include_router(blockdetails.router, prefix="/api/v1/blockdetails", tags=["Block Details"])

@app.get("/")
def read_root():
    logger.info("Root endpoint accessed")
    return {"message": "API is running"}

@app.on_event("startup")
async def startup_event():
    logger.info("Vault Blockchain API starting up...")
    logger.info(f"Network: {os.getenv('NETWORK', 'sepolia')}")
    logger.info(f"Contract Address: {os.getenv('CONTRACT_ADDRESS_SEPOLIA') or os.getenv('CONTRACT_ADDRESS')}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Vault Blockchain API shutting down...")

 
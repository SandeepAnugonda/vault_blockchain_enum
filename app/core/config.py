import os
from cryptography.fernet import Fernet

class Settings:
    # Database (SQL Server Express, Windows Authentication)
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "mssql+pyodbc://@DESKTOP-G004CUN\\SQLEXPRESS02/blockchain?driver=ODBC+Driver+17+for+SQL+Server"
    )
    
    # Security
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key())
    SECRET_KEY = os.getenv("SECRET_KEY", "vault-secret-key-change-in-production")
    
    # File Upload
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 50 * 1024 * 1024))  # 50MB default
    ALLOWED_EXTENSIONS = [
        '.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', 
        '.png', '.gif', '.xlsx', '.xls', '.ppt', '.pptx',
        '.csv', '.zip', '.rar', '.mp4', '.avi', '.mp3'
    ]
    
    # API
    API_V1_STR = "/api/v1"
    PROJECT_NAME = "Vault Document Blockchain API"
    VERSION = "1.0.0"
    
    # CORS
    ALLOWED_ORIGINS = ["*"]  # Configure properly for production
    
    # Blockchain
    GENESIS_HASH = "0" * 64
    
    # Directories
    TEMP_DIR = os.getenv("TEMP_DIR", "./temp")
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")

# Create settings instance
settings = Settings()

# Create necessary directories
os.makedirs(settings.TEMP_DIR, exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
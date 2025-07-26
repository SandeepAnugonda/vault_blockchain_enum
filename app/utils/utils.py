import uuid
block_id = str(uuid.uuid4())

def generate_unique_id() -> str:
    return str(uuid.uuid4())
# Utility to create a new block for a document action
import json
from app.db.database import DocumentBlock
from datetime import datetime
import hashlib
import os
import mimetypes
from datetime import datetime
from cryptography.fernet import Fernet
from app.core.config import settings
from app.db.database import DocumentBlock
import json
import uuid

# Initialize cipher for encryption/decryption
cipher = Fernet(settings.ENCRYPTION_KEY if isinstance(settings.ENCRYPTION_KEY, bytes) else settings.ENCRYPTION_KEY.encode())
def create_new_block(db, document_id, user_id, action, filename, file_content=None, metadata=None):
    import uuid
    # Get previous block
    previous_block = db.query(DocumentBlock).filter(DocumentBlock.document_id == document_id).order_by(DocumentBlock.block_number.desc()).first()
    previous_hash = previous_block.block_hash if previous_block else None
    block_number = previous_block.block_number + 1 if previous_block else 1

    # Encrypt file content if provided
    encrypted_content = None
    file_size = None
    if file_content:
        encrypted_content = encrypt_content(file_content)
        file_size = len(file_content)

    # Prepare metadata
    block_metadata = json.dumps(metadata) if metadata else None

    # Calculate block hash
    block_hash_source = f"{document_id}{user_id}{action}{filename}{block_number}{previous_hash}{datetime.utcnow().isoformat()}"
    block_hash = hashlib.sha256(block_hash_source.encode()).hexdigest()

    block_id = str(uuid.uuid4())
    block = DocumentBlock(
        id=block_id,
        document_id=document_id,
        user_id=user_id,
        action=action,
        filename=filename,
        encrypted_content=encrypted_content,
        block_metadata=block_metadata,
        block_number=block_number,
        block_hash=block_hash,
        previous_hash=previous_hash,
        timestamp=datetime.utcnow(),
        status="active",
        file_size=file_size
    )
    db.add(block)
    db.commit()
    db.refresh(block)
    return block
import hashlib
from cryptography.fernet import Fernet
from app.core.config import settings

cipher = Fernet(settings.ENCRYPTION_KEY if isinstance(settings.ENCRYPTION_KEY, bytes) else settings.ENCRYPTION_KEY.encode())

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def encrypt_content(content: bytes) -> bytes:
    return cipher.encrypt(content)

def decrypt_content(token: bytes) -> bytes:
    return cipher.decrypt(token)

def generate_data_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def validate_file_type(filename: str, allowed_types: list = None) -> bool:
    """
    Validate if the file type is allowed based on its extension.
    
    Args:
        filename: Name of the file to validate
        allowed_types: List of allowed MIME types (optional)
    
    Returns:
        bool: True if file type is valid, False otherwise
    """
    if not allowed_types:
        allowed_types = [
            'application/pdf',
            'text/plain',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]
    
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type in allowed_types if mime_type else False

def get_file_info(filename: str, file_content: bytes) -> dict:
    """
    Get information about an uploaded file.
    
    Args:
        filename: Name of the file
        file_content: Content of the file as bytes
    
    Returns:
        dict: File information including size and mime type
    """
    import mimetypes
    mime_type, _ = mimetypes.guess_type(filename)
    return {
        'size': len(file_content),
        'mime_type': mime_type or 'unknown',
    }

def create_block_metadata(document_id: str, user_id: str, action: str) -> dict:
    """
    Create metadata for a new block.
    
    Args:
        document_id: ID of the document
        user_id: ID of the user
        action: Action performed
    
    Returns:
        dict: Metadata dictionary
    """
    return {
        'document_id': document_id,
        'user_id': user_id,
        'action': action,
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0'
    }

def clean_temp_files(temp_dir: str, max_age_hours: int = 24) -> None:
    """
    Clean temporary files older than max_age_hours.
    
    Args:
        temp_dir: Directory containing temporary files
        max_age_hours: Maximum age of files to keep (in hours)
    """
    try:
        current_time = datetime.now().timestamp()
        max_age_seconds = max_age_hours * 3600
        
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    os.remove(file_path)
    except Exception as e:
        print(f"Error cleaning temp files: {str(e)}")

def verify_blockchain_integrity(db, document_id: str) -> bool:
    """
    Verify the integrity of the blockchain for a document.
    
    Args:
        db: Database session
        document_id: ID of the document to verify
    
    Returns:
        bool: True if blockchain is intact, False otherwise
    """
    blocks = db.query(DocumentBlock).filter(DocumentBlock.document_id == document_id).order_by(DocumentBlock.block_number.asc()).all()
    
    for i, block in enumerate(blocks):
        # Verify previous hash
        if i > 0 and block.previous_hash != blocks[i-1].block_hash:
            return False
            
        # Recalculate and verify block hash
        block_hash_source = f"{block.document_id}{block.user_id}{block.action}{block.filename}{block.block_number}{block.previous_hash}{block.timestamp.isoformat()}"
        calculated_hash = hashlib.sha256(block_hash_source.encode()).hexdigest()
        if calculated_hash != block.block_hash:
            return False
            
    return True

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in a human-readable format.
    
    Args:
        size_bytes: File size in bytes
    
    Returns:
        str: Formatted file size
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"

def encrypt_file_content(file_content: bytes) -> bytes:
    """
    Encrypt file content using Fernet encryption.
    
    Args:
        file_content: Content to encrypt
    
    Returns:
        bytes: Encrypted content
    """
    return cipher.encrypt(file_content)

def calculate_file_hash(file_content: bytes) -> str:
    """
    Calculate SHA-256 hash of file content.
    
    Args:
        file_content: Content to hash
    
    Returns:
        str: SHA-256 hash
    """
    return hashlib.sha256(file_content).hexdigest()
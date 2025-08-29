import uuid
import json
from datetime import datetime
import hashlib
import os
import mimetypes
from cryptography.fernet import Fernet
from app.core.config import settings

# Action mapping to Solidity enum
ACTION_MAP = {
    "Created": 0,
    "Shared": 1,
    "Viewed": 2,
    "Downloaded": 3,
    "Shared_view": 4,
    "Shared_download": 5,
}

cipher = Fernet(settings.ENCRYPTION_KEY if isinstance(settings.ENCRYPTION_KEY, bytes) else settings.ENCRYPTION_KEY.encode())

def generate_unique_id() -> str:
    return str(uuid.uuid4())

def create_new_block(document_id, user_id, action, filename, file_content=None, metadata=None):
    """
    Create a new block/document entry compatible with the Solidity contract.
    Returns a dictionary representing the block.
    """
    block_number = 1  # If you want to increment, you must track this externally (e.g., in a file or contract)
    previous_hash = None  # You must provide this if chaining blocks

    # Encrypt file content if provided
    encrypted_content = None
    file_size = None
    if file_content:
        encrypted_content = encrypt_content(file_content)
        file_size = len(file_content)

    # Prepare metadata (Solidity expects specific fields)
    block_metadata = json.dumps(metadata) if metadata else None

    # Calculate block hash
    block_hash_source = f"{document_id}{user_id}{action}{filename}{block_number}{previous_hash}{datetime.utcnow().isoformat()}"
    block_hash = hashlib.sha256(block_hash_source.encode()).hexdigest()

    block_id = str(uuid.uuid4())
    action_enum = ACTION_MAP.get(action, 0)

    block = {
        "id": block_id,
        "document_id": document_id,
        "user_id": user_id,
        "action": action_enum,
        "filename": filename,
        "encrypted_content": encrypted_content,
        "block_metadata": block_metadata,
        "block_number": block_number,
        "block_hash": block_hash,
        "previous_hash": previous_hash,
        "timestamp": datetime.utcnow().isoformat(),
        "status": "active",
        "file_size": file_size
    }
    return block

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def encrypt_content(content: bytes) -> bytes:
    return cipher.encrypt(content)

def decrypt_content(token: bytes) -> bytes:
    return cipher.decrypt(token)

def generate_data_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def validate_file_type(filename: str, allowed_types: list = None) -> bool:
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
    mime_type, _ = mimetypes.guess_type(filename)
    return {
        'size': len(file_content),
        'mime_type': mime_type or 'unknown',
    }

def create_block_metadata(document_id: str, user_id: str, action: str, shared_user: str = "", shared_end_date: str = "") -> dict:
    """
    Create metadata for a new block compatible with Solidity contract.
    """
    return {
        'document_id': document_id,
        'user_id': user_id,
        'action': action,
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0',
        'shared_user': shared_user,
        'shared_end_date': shared_end_date
    }

def clean_temp_files(temp_dir: str, max_age_hours: int = 24) -> None:
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

def format_file_size(size_bytes: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"

def encrypt_file_content(file_content: bytes) -> bytes:
    return cipher.encrypt(file_content)

def calculate_file_hash(file_content: bytes) -> str:
    return hashlib.sha256(file_content).hexdigest()

# ---------------- Blockchain helpers ----------------
from typing import Any, Dict
from web3 import Web3
from app.utils.blockchain import w3

def compute_action_record_hash(block: Dict[str, Any]) -> str:
    """
    Compute keccak256 hash equivalent to Solidity _computeHash(ActionRecord) using abi.encode.
    Expects keys: DocTitle, Owner, LastAccessDate, LastAccessedBy, action, SharedUser,
    SharedEndDate, TimeStamp/timestamp, previousHash
    """
    previous_hash = block.get("previousHash") or "0x" + ("00" * 32)
    if isinstance(previous_hash, bytes):
        previous_hash_bytes32 = previous_hash
    else:
        previous_hash_bytes32 = Web3.to_bytes(hexstr=previous_hash)
    # Ensure bytes32 length
    if len(previous_hash_bytes32) != 32:
        previous_hash_bytes32 = previous_hash_bytes32.rjust(32, b"\x00")[:32]

    # Resolve action value (supports 'actionIndex', numeric 'action', or string action name)
    action_value: int
    if "actionIndex" in block and block["actionIndex"] is not None:
        action_value = int(block["actionIndex"])
    else:
        a = block.get("action", 0)
        if isinstance(a, str):
            action_value = int(ACTION_MAP.get(a, 0))
        else:
            action_value = int(a or 0)

    # Use a single timestamp source for both contract fields
    ts_single = int(block.get("timestamp") or block.get("TimeStamp") or 0)
    values = [
        block.get("DocTitle", ""),
        int(block.get("Owner", 0) or 0),  # Owner is now uint64
        int(block.get("LastAccessDate", 0) or 0),
        block.get("LastAccessedBy", ""),
        action_value,
        block.get("SharedUser", ""),
        int(block.get("SharedEndDate", 0) or 0),
        ts_single,
        ts_single,
        previous_hash_bytes32,
    ]
    types = [
        "string",
        "uint64",  # Owner is now uint64
        "uint256",
        "string",
        "uint8",
        "string",
        "uint256",
        "uint256",
        "uint256",
        "bytes32",
    ]
    return Web3.to_hex(w3.solidity_keccak(types, values))
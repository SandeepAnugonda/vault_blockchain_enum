## Only Pydantic models should be defined here. SQLAlchemy models are in app/db/database.py
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Union
from datetime import datetime

# User Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

    doc_id: Union[str, int]
    owner_id: Union[str, int]
    filename: Optional[str] = None

    doc_id: Union[str, int]
    owner_id: Union[str, int]
    new_doc_id: Union[str, int]
    filename: Optional[str] = None

    owner_id: Union[str, int]
    previous_doc_id: Union[str, int]
    new_doc_id: Union[str, int]
    action: str  # view, download, edit
    accessed_by: Optional[str] = None

    doc_id: Union[str, int]
    owner_id: Union[str, int]
    recipient_email: EmailStr
    access_type: str  # view, download, both
    shared_by: str

# Blockchain Models
class BlockResponse(BaseModel):
    id: str
    document_id: str
    block_number: int
    previous_hash: str
    block_hash: str
    action: str
    filename: Optional[str]
    file_size: int
    timestamp: datetime
    status: str

class DocumentHistory(BaseModel):
    document_id: str
    blocks: List[BlockResponse]
    total_blocks: int

class BlockchainStatus(BaseModel):
    document_id: str
    filename: str
    current_block: int
    total_blocks: int
    last_action: str
    last_updated: datetime
    status: str

class DocumentListResponse(BaseModel):
    documents: List[BlockchainStatus]
    total_documents: int

# Share Models
class ShareRequest(BaseModel):
    shared_with_email: Optional[str] = None
    share_type: str = "public"  # public, private

class ShareResponse(BaseModel):
    document_id: str
    share_block_hash: str
    shared_at: datetime
    share_type: str

# API Response Models
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: Optional[str] = None
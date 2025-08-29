from pydantic import BaseModel, EmailStr
from typing import Optional

class UserAuth(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    message: str
    email: EmailStr
    token: str

# ---------------- New schemas for document routes ----------------

class DocumentBlockRequest(BaseModel):
    DocTitle: str
    Owner: int  # Owner is now uint64 (int)
    LastAccessDate: int

class AccessActionRequest(BaseModel):
    DocTitle: str
    Owner: int  # Owner is now uint64 (int)
    action: int  # 0=view, 1=download
    LastAccessDate: int

class ShareDocumentRequest(BaseModel):
    DocTitle: str
    Owner: int  # Owner is now uint64 (int)
    SharedUser: str
    permissions: str  # "view" or "download"
    SharedEndDate: int
    LastAccessDate: int

class DocumentResponse(BaseModel):
    DocTitle: str
    Owner: int  # Owner is now uint64 (int)
    LastAccessDate: int
    LastAccessedBy: str
    action: str
    SharedUser: str
    SharedEndDate: int
    timestamp: Optional[int] = None
    previousHash: Optional[str] = None
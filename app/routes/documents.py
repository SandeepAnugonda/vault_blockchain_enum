from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime
import hashlib
import json
import uuid
from app.utils.blockchain import upload_to_pinata, is_owner, has_shared_access, create_document_on_chain

# In-memory storage
in_memory_documents = {}  # {owner: {doc_id: [blocks]}}
shared_documents = {}
from app.models.models import APIResponse
# from app.utils.utils import verify_blockchain_integrity, format_file_size

# Define ShareDocumentRequest model
class ShareDocumentRequest(BaseModel):
    doc_id: str  # replaces doc_title, filename, file_path
    owner: str   # replaces owner_id, user_id, ownername, username
    recipient_email: EmailStr
    permissions: str  # view/download/both (given by owner)
    shared_end_time: Optional[str] = None  # access end time/date given by owner

    @validator("permissions")
    def validate_permissions(cls, v):
        allowed = {"view", "download", "both"}
        if v.lower() not in allowed:
            raise ValueError(f"permissions must be one of {allowed}")
        return v.lower()

router = APIRouter()

# Pydantic models for request/response
class Owner(BaseModel):
    owner: str

class DocumentBlockRequest(BaseModel):
    doc_id: str
    owner: str

class UpdateDocumentBlockRequest(BaseModel):
    doc_id: str
    owner: str
    new_doc_id: str


class AccessActionRequest(BaseModel):
    doc_id: str
    owner: str
    accessed_by: str
    action_type: int  # 0 for view, 1 for download

def get_current_user():
    # Replace with real authentication logic 
    return "test_user"

def generate_block_hash(block_data: dict) -> str:
    """Generate SHA-256 hash for block data"""
    block_string = json.dumps(block_data, sort_keys=True)
    return hashlib.sha256(block_string.encode()).hexdigest()

def get_previous_block_hash(document_id: str) -> str:
    """Get the hash of the previous block in the chain (DB REMOVED)"""
    # Placeholder: return dummy previous hash
    return "0"

def get_next_block_number(document_id: str) -> int:
    """Get the next block number for the document chain (DB REMOVED)"""
    # Placeholder: always return 1
    return 1

def create_blockchain_block(
    document_id: str,
    user_id: str,
    action: str,
    file_size: int = None,
    encrypted_content: str = None,
    metadata: dict = None,
    last_accessed_by: str = None
):
    """Create a new blockchain block and store in memory"""
    # Find previous block for block_number and previous_hash
    owner_docs = in_memory_documents.get(user_id, {})
    blocks = owner_docs.get(document_id, [])
    block_number = len(blocks) + 1
    previous_hash = blocks[-1]["block_hash"] if blocks else "0"
    block_data = {
        "document_id": document_id,
        "user_id": user_id,
        "block_number": block_number,
        "previous_hash": previous_hash,
        "action": action,
        "file_size": file_size,
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": metadata
    }
    block_hash = generate_block_hash(block_data)
    block = {
        "id": str(uuid.uuid4()),
        "document_id": document_id,
        "user_id": user_id,
        "block_number": block_number,
        "block_hash": block_hash,
        "previous_hash": previous_hash,
        "action": action,
        "file_size": file_size,
        "encrypted_content": encrypted_content,
        "metadata": json.dumps(metadata) if metadata else None,
        "timestamp": datetime.utcnow().isoformat(),
        "status": action.lower(),
        "last_accessed_by": last_accessed_by or user_id
    }
    # Store in memory
    if user_id not in in_memory_documents:
        in_memory_documents[user_id] = {}
    if document_id not in in_memory_documents[user_id]:
        in_memory_documents[user_id][document_id] = []
    in_memory_documents[user_id][document_id].append(block)
    return block

# 1. POST: Create a block for documents
@router.post("/create-block", response_model=APIResponse)
async def create_document_block(
    request: DocumentBlockRequest
):
    """Create a new blockchain block for a document"""
    try:
        # Check if this is the first block for this document
        # DB REMOVED: Always allow creation
        # Create genesis block
        metadata = {
            "creation_timestamp": datetime.utcnow().isoformat(),
            "owner": request.owner,
            "is_genesis": True
        }
        new_block = create_blockchain_block(
            document_id=request.doc_id,
            user_id=request.owner,
            action="CREATED",
            file_size=0,
            encrypted_content=None,
            metadata=metadata,
            last_accessed_by=request.owner
        )
        # Save metadata to blockchain
        receipt = create_document_on_chain(request.doc_id, request.owner)
        return APIResponse(
            success=True,
            message="Document block created and saved to blockchain",
            data={
                "block_id": new_block["id"],
                "document_id": new_block["document_id"],
                "block_number": new_block["block_number"],
                "block_hash": new_block["block_hash"],
                "status": new_block["status"],
                "last_accessed_by": new_block["last_accessed_by"],
                "timestamp": new_block["timestamp"],
                "blockchain_tx_hash": receipt.transactionHash.hex()
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create document block: {str(e)}"
        )

# 2. PUT: Update document and create new block
@router.put("/update-document", response_model=APIResponse)
async def update_document_block(request: UpdateDocumentBlockRequest):
    """Update document and create a new block in the blockchain"""
    try:
        metadata = {
            "update_timestamp": datetime.utcnow().isoformat(),
            "previous_doc_id": request.doc_id,
            "updated_by": request.owner,
            "version_update": True
        }
        # Always create a new block for the update action
        new_block = create_blockchain_block(
            document_id=request.new_doc_id,
            user_id=request.owner,
            action="UPDATED",
            file_size=0,
            encrypted_content=None,
            metadata=metadata,
            last_accessed_by=request.owner
        )
        return APIResponse(
            success=True,
            message="Document updated and new block created successfully",
            data={
                "new_block_id": new_block["id"],
                "new_document_id": new_block["document_id"],
                "block_number": new_block["block_number"],
                "block_hash": new_block["block_hash"],
                "previous_doc_id": request.doc_id,
                "status": new_block["status"],
                "last_accessed_by": new_block["last_accessed_by"],
                "timestamp": new_block["timestamp"]
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update document: {str(e)}"
        )


# 3. POST: Access document (view or download) and create action block
@router.post("/access-document", response_model=APIResponse)
async def access_document(request: AccessActionRequest):
    """Access document (view or download) and create action block (0=view, 1=download). Owner always has full access."""
    try:
        # Verify document exists
        if request.doc_id not in in_memory_documents.get(request.owner, {}):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        if request.action_type not in [0, 1]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid action: must be 0 (View) or 1 (Download)"
            )
        action = "VIEWED" if request.action_type == 0 else "DOWNLOADED"
        # If accessed_by is the owner, always allow
        if request.accessed_by == request.owner:
            allowed = True
        else:
            # Check if recipient has permission for the requested action
            key = (request.owner, request.doc_id)
            allowed = False
            if key in shared_documents:
                recipient_access = shared_documents[key].get(request.accessed_by)
                if recipient_access == "both":
                    allowed = True
                elif recipient_access == "view" and request.action_type == 0:
                    allowed = True
                elif recipient_access == "download" and request.action_type == 1:
                    allowed = True
                else:
                    # Recipient exists but does not have permission for this action
                    allowed = False
            else:
                # Not shared with this recipient
                allowed = False
        if not allowed:
            action_str = "view" if request.action_type == 0 else "download"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have permission to {action_str} this document. Ask the owner to share with '{action_str}' access."
            )
        metadata = {
            "access_timestamp": datetime.utcnow().isoformat(),
            "action_type": action,
            "doc_id": request.doc_id,
            "accessed_by": request.accessed_by
        }
        action_block = create_blockchain_block(
            document_id=request.doc_id,
            user_id=request.owner,
            action=action,
            file_size=0,
            encrypted_content=None,
            metadata=metadata,
            last_accessed_by=request.accessed_by
        )
        return APIResponse(
            success=True,
            message=f"Document {action.lower()} successfully",
            data={
                "block_id": action_block["id"],
                "document_id": action_block["document_id"],
                "block_number": action_block["block_number"],
                "action": action_block["action"],
                "status": action_block["status"],
                "last_accessed_by": action_block["last_accessed_by"],
                "timestamp": action_block["timestamp"],
                "doc_id": request.doc_id,
                "action_type": request.action_type
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to access document: {str(e)}"
        )

def document_exists(owner: str, doc_id: str) -> bool:
    """Check if a document exists for a given owner and doc_id."""
    return doc_id in in_memory_documents.get(owner, {})

# 4. POST: Share document
@router.post("/share-document", response_model=APIResponse)
async def share_document(request: ShareDocumentRequest):
    """Share document and create sharing block, tracking allowed access for recipient"""
    try:
        if not document_exists(request.owner, request.doc_id):
            raise HTTPException(status_code=404, detail="Document not found to share")
        key = (request.owner, request.doc_id)
        if key not in shared_documents:
            shared_documents[key] = {}
        shared_documents[key][str(request.recipient_email)] = {
            "permissions": request.permissions,
            "shared_end_time": request.shared_end_time
        }
        # Always ensure owner has full access
        shared_documents[key][str(request.owner)] = {
            "permissions": "both",
            "shared_end_time": None
        }
        action = f'SHARED_DOCUMENT_TO_{request.recipient_email}'
        metadata = {
            "share_timestamp": datetime.utcnow().isoformat(),
            "action_type": action,
            "doc_id": request.doc_id,
            "recipient_email": request.recipient_email,
            "permissions": request.permissions,
            "shared_end_time": request.shared_end_time,
            "share_id": str(uuid.uuid4())
        }
        # Always create a new block for the share action
        share_block = create_blockchain_block(
            document_id=request.doc_id,
            user_id=request.owner,
            action=action,
            file_size=0,
            encrypted_content=None,
            metadata=metadata,
            last_accessed_by=request.owner
        )
        return APIResponse(
            success=True,
            message=f"Document shared successfully with {request.recipient_email} ({request.permissions})",
            data={
                "block_id": share_block["id"],
                "document_id": share_block["document_id"],
                "block_number": share_block["block_number"],
                "recipient_email": request.recipient_email,
                "access_type": request.access_type,
                "action": share_block["action"],
                "status": request.owner,
                "last_accessed_by": request.owner,
                "timestamp": share_block["timestamp"],
                "share_id": metadata["share_id"],
                "doc_id": request.doc_id
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to share document: {str(e)}"
        )
# 8. POST: Generic action block for any action (view, download, shared, updated, etc.)
@router.post("/action-block", response_model=APIResponse)
async def create_generic_action_block(
    doc_id: str,
    owner: str,
    action: str,
    metadata: Optional[dict] = None
):
    """Create a new block for any action (view, download, shared, updated, etc.)"""
    try:
        block = create_blockchain_block(
            document_id=doc_id,
            user_id=owner,
            action=action,
            file_size=0,
            encrypted_content=None,
            metadata=metadata,
            last_accessed_by=owner
        )
        return APIResponse(
            success=True,
            message=f"Action block created for action: {action}",
            data={
                "block_id": block["id"],
                "document_id": block["document_id"],
                "block_number": block["block_number"],
                "action": block["action"],
                "status": block["status"],
                "last_accessed_by": block["last_accessed_by"],
                "timestamp": block["timestamp"],
                "doc_id": doc_id
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create action block: {str(e)}"
        )
    # Use request.permissions instead of request.access_type
    # Example usage:
    # permission = request.permissions
    # ...existing code...
# 5. GET: Get all documents for owner
@router.get("/owner/{owner}/documents", response_model=APIResponse)
async def get_owner_documents(owner: str):
    """Get all documents and their history for a specific owner"""
    owner_docs = in_memory_documents.get(owner, {})
    documents = []
    total_blocks = 0
    for doc_id, blocks in owner_docs.items():
        documents.append({
            "doc_id": doc_id,
            "blocks": blocks
        })
        total_blocks += len(blocks)
    return APIResponse(
        success=True,
        message=f"Retrieved documents for owner {owner}",
        data={
            "owner": owner,
            "documents": documents,
            "total_documents": len(documents),
            "total_blocks": total_blocks
        }
    )

# 6. GET: Get individual document details
@router.get("/owner/{owner}/document/{doc_id}", response_model=APIResponse)
async def get_individual_document(owner: str, doc_id: str):
    """Get details of an individual document from owner's document list"""
    owner_docs = in_memory_documents.get(owner, {})
    blocks = owner_docs.get(doc_id)
    if not blocks:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    latest_block = blocks[-1] if blocks else None
    return APIResponse(
        success=True,
        message=f"Retrieved latest block for document {doc_id} (owner {owner})",
        data={
            "owner": owner,
            "doc_id": doc_id,
            "latest_block": latest_block,
            "block_number": latest_block["block_number"] if latest_block else None,
            "block_hash": latest_block["block_hash"] if latest_block else None,
            "status": latest_block["status"] if latest_block else None,
            "last_accessed_by": latest_block["last_accessed_by"] if latest_block else None,
            "timestamp": latest_block["timestamp"] if latest_block else None
        }
    )

# 7. GET: Get complete document history with all blocks
@router.get("/document/{doc_id}/complete-history", response_model=APIResponse)
async def get_complete_document_history(doc_id: str, owner: Optional[str] = None):
    """Get complete blockchain history of a document with all blocks"""
    # If owner is not provided, search all owners
    if owner:
        owner_docs = in_memory_documents.get(owner, {})
        blocks = owner_docs.get(doc_id)
        if not blocks:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return APIResponse(
            success=True,
            message=f"Retrieved complete history for document {doc_id}",
            data={
                "owner": owner,
                "doc_id": doc_id,
                "blocks": blocks,
                "total_blocks": len(blocks)
            }
        )
    # Search all owners for doc_id
    for owner_key, owner_docs in in_memory_documents.items():
        blocks = owner_docs.get(doc_id)
        if blocks:
            return APIResponse(
                success=True,
                message=f"Retrieved complete history for document {doc_id}",
                data={
                    "owner": owner_key,
                    "doc_id": doc_id,
                    "blocks": blocks,
                    "total_blocks": len(blocks)
                }
            )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
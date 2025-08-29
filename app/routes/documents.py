import os
from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from fastapi.responses import FileResponse
from app.schemas import DocumentBlockRequest, ShareDocumentRequest, AccessActionRequest, DocumentResponse
from app.models.models import APIResponse
from app.utils.blockchain import upload_to_pinata, w3, contract, create_document_on_chain, access_document_on_chain, share_document_on_chain, get_document_on_chain, get_user_documents_on_chain, get_document_history_on_chain
from app.utils.utils import get_file_info, create_block_metadata
from typing import List, Optional
from eth_utils import keccak
from web3.exceptions import ContractLogicError

ACTION_ENUM = [
    "Created", "Shared", "Viewed", "Downloaded", "Shared_view", "Shared_download"
]

PERMISSION_ENUM = ["View", "Download"]

def compute_block_hash(block):
    # Solidity's abi.encode order for ActionRecord (no ipfsHash)
    concat = (
        str(block["DocTitle"]) +
        str(block["Owner"]) +
        str(block["LastAccessDate"]) +
        str(block["LastAccessedBy"]) +
        str(block["action"]) +
        str(block["SharedUser"]) +
        str(block["SharedEndDate"]) +
        str(block.get("timestamp") or block.get("TimeStamp")) +
        str(block["previousHash"])
    )
    return "0x" + keccak(text=concat).hex()

def _to_str(value):
    return "" if value is None else str(value)

def _to_int(value):
    try:
        if value is None or value == "":
            return 0
        return int(value)
    except Exception:
        return 0

def _action_to_str(action_value):
    try:
        if isinstance(action_value, int):
            return ACTION_ENUM[action_value] if 0 <= action_value < len(ACTION_ENUM) else str(action_value)
        return str(action_value)
    except Exception:
        return ""

def _standardize_block(raw: dict) -> dict:
    # Normalize fields; keep numeric types as ints for Swagger correctness
    action = raw.get("action")
    owner = raw.get("Owner")
    shared_user = raw.get("SharedUser")
    last_accessed_by = raw.get("LastAccessedBy")
    # For Created, LastAccessedBy is owner
    if (isinstance(action, int) and action == 0) or (action == "Created"):
        last_accessed_by = owner
    # For Shared actions, LastAccessedBy is shared_user
    elif (isinstance(action, int) and action in [1, 4, 5]) or (action in ["Shared", "Shared_view", "Shared_download"]):
        last_accessed_by = shared_user
    # For Viewed/Downloaded, use contract value (do not override)
    # If contract value is empty, fallback to owner
    if (isinstance(action, int) and action in [2, 3]) or (action in ["Viewed", "Downloaded"]):
        if not last_accessed_by:
            last_accessed_by = owner
    prev_hash = raw.get("previousHash")
    if isinstance(prev_hash, bytes):
        prev_hash = prev_hash.hex()
    sanitized = {
        "DocTitle": _to_str(raw.get("DocTitle")),
        "Owner": _to_str(owner),
        "LastAccessDate": _to_int(raw.get("LastAccessDate")),
        "LastAccessedBy": _to_str(last_accessed_by),
        "action": _action_to_str(action),
        "SharedUser": _to_str(shared_user),
        "SharedEndDate": _to_int(raw.get("SharedEndDate")),
        "TimeStamp": _to_int(raw.get("TimeStamp")),
        "previousHash": _to_str(prev_hash),
    }
    compute_input = dict(sanitized)
    compute_input["timestamp"] = _to_str(raw.get("timestamp"))
    sanitized["blockHash"] = _to_str(compute_block_hash(compute_input))
    return sanitized

router = APIRouter()



from app.schemas import DocumentBlockRequest

@router.post("/create_block", response_model=APIResponse)
async def create_document_block(request: DocumentBlockRequest):
    import asyncio
    # Pre-check if document already exists (handles cross-owner duplication as contract uses title key)
    try:
        exists = False
        try:
            # Use wrapper that encodes bytes32
            get_document_on_chain(request.DocTitle, request.Owner)
            exists = True  # found for same owner
        except Exception as e:
            msg = str(e)
            # Treat contract revert/no data as 'not found', not 500
            if "Document does not exist" in msg or "execution reverted" in msg or "no data" in msg:
                exists = False
            elif "Owner does not match" in msg:
                raise HTTPException(status_code=400, detail="DocTitle is already used by another owner. Choose a different title.")
            else:
                raise
        if exists:
            raise HTTPException(status_code=400, detail="Document with this title already exists for this owner.")
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        # Treat contract revert/no data as 'not found', not 500
        if "execution reverted" in msg or "no data" in msg:
            pass  # Document does not exist, so allow creation
        else:
            raise HTTPException(status_code=500, detail=f"Error checking document existence: {e}")

    try:
        # Create document block on blockchain; generate internal placeholder ipfsHash (API does not supply)
        placeholder_ipfs = keccak(text=f"{request.DocTitle}|{request.Owner}|{request.LastAccessDate}").hex()[2:34]
        receipt = create_document_on_chain(request.DocTitle, int(request.Owner), request.LastAccessDate, placeholder_ipfs)
        if receipt.get("status", 1) == 0:
            raise HTTPException(status_code=400, detail="Blockchain transaction reverted. Title may already exist.")
    except Exception as e:
        msg = str(e)
        # If contract revert is for duplicate, return 400
        if "Document already exists" in msg or "Owner does not match" in msg or "reverted" in msg:
            raise HTTPException(status_code=400, detail=f"Document already exists for this owner or title is not unique: {msg}")
        raise HTTPException(status_code=500, detail=f"Blockchain error: {msg}")

    # Retry fetching document/history for up to 5 seconds
    import asyncio
    for _ in range(10):
        try:
            latest_doc = get_document_on_chain(request.DocTitle, request.Owner)
            history = get_document_history_on_chain(request.DocTitle, request.Owner)
            action_str = ACTION_ENUM[latest_doc["action"]] if isinstance(latest_doc["action"], int) and latest_doc["action"] < len(ACTION_ENUM) else str(latest_doc["action"])
            latest_block = dict(latest_doc)
            latest_block["action"] = action_str
            latest_block["timestamp"] = history[0]["timestamp"] if history else None
            latest_block["previousHash"] = history[0].get("previousHash") if history else None
            return APIResponse(
                success=True,
                message="Document block created on blockchain",
                data=_standardize_block(latest_block),
            )
        except Exception as e:
            await asyncio.sleep(0.5)
    raise HTTPException(status_code=202, detail="Document creation transaction sent; data will be readable shortly. Try again in a few seconds.")


@router.post("/access_document", response_model=APIResponse)
async def access_document(request: AccessActionRequest):
    try:
        receipt = access_document_on_chain(request.DocTitle, int(request.Owner), request.action, request.LastAccessDate)
        d = get_document_on_chain(request.DocTitle, int(request.Owner))
        action_str = ACTION_ENUM[d["action"]] if isinstance(d["action"], int) and d["action"] < len(ACTION_ENUM) else str(d["action"])
        block = dict(d)
        block["action"] = action_str
        block["blockHash"] = compute_block_hash(block)
        return APIResponse(
            success=True,
            message="Document accessed",
            data=_standardize_block(block),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/share_document", response_model=APIResponse)
async def share_document(request: ShareDocumentRequest):
    try:
        receipt = share_document_on_chain(
            request.DocTitle,
            int(request.Owner),
            request.SharedUser,
            request.permissions,
            request.SharedEndDate,
            request.LastAccessDate
        )
        d = get_document_on_chain(request.DocTitle, int(request.Owner))
        action_str = ACTION_ENUM[d["action"]] if isinstance(d["action"], int) and d["action"] < len(ACTION_ENUM) else str(d["action"])
        block = dict(d)
        block["action"] = action_str
        block["blockHash"] = compute_block_hash(block)
        return APIResponse(
            success=True,
            message="Document shared",
            data=_standardize_block(block),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# New GET endpoint: Get all blocks for an owner
@router.get("/blocks/owner/{owner}", response_model=APIResponse)
async def get_blocks_by_owner(owner: str):
    try:
        docs = get_user_documents_on_chain(int(owner))
        blocks = []
        for d in docs:
            action_str = ACTION_ENUM[d["action"]] if isinstance(d["action"], int) and d["action"] < len(ACTION_ENUM) else str(d["action"])
            block = dict(d)
            block["action"] = action_str
            # Ensure previousHash is always present, set to None or empty string if missing
            if "previousHash" not in block or block["previousHash"] is None:
                block["previousHash"] = ""
            block["blockHash"] = compute_block_hash(block)
            blocks.append(_standardize_block(block))
        if blocks:
            return APIResponse(success=True, message="Blocks for this owner fetched from blockchain.", data={"blocks": blocks})
        else:
            raise HTTPException(status_code=404, detail="No blocks found for this owner.")
    except Exception as e:
        msg = str(e)
        # If error is only about previousHash, ignore and return blocks
        if "previousHash" in msg:
            # Try to fetch blocks again, ignoring previousHash
            try:
                docs = get_user_documents_on_chain(int(owner))
                blocks = []
                for d in docs:
                    action_str = ACTION_ENUM[d["action"]] if isinstance(d["action"], int) and d["action"] < len(ACTION_ENUM) else str(d["action"])
                    block = dict(d)
                    block["action"] = action_str
                    block["previousHash"] = ""
                    block["blockHash"] = compute_block_hash(block)
                    blocks.append(_standardize_block(block))
                if blocks:
                    return APIResponse(success=True, message="Blocks for this owner fetched from blockchain.", data={"blocks": blocks})
            except Exception:
                pass
        if "invalid" in msg or "not found" in msg or "does not exist" in msg:
            raise HTTPException(status_code=404, detail=f"Owner not found or invalid: {msg}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch blocks for owner: {msg}")

# New GET endpoint: Get all blocks (history) for a document
@router.get("/blocks/document/{doctitle}/owner/{owner}", response_model=APIResponse)
async def get_document_blocks_history(doctitle: str, owner: str):
    try:
        # Pre-check existence to avoid revert and provide clearer error
        try:
            history = get_document_history_on_chain(doctitle, int(owner))
        except Exception as e:
            msg = str(e)
            if "Document does not exist" in msg or "execution reverted" in msg or "no data" in msg:
                raise HTTPException(status_code=404, detail="Document not found for this owner")
            else:
                raise
        try:
            user_docs = get_user_documents_on_chain(owner)
            owner_titles = [d.get("DocTitle") for d in user_docs]
            if doctitle not in owner_titles:
                raise HTTPException(status_code=404, detail="Document not found for this owner")
        except ContractLogicError as cle:
            # If even listing fails, bubble up as 404
            raise HTTPException(status_code=404, detail=str(cle))

        blocks = []
        for h in history:
            action_str = ACTION_ENUM[h["action"]] if isinstance(h["action"], int) and h["action"] < len(ACTION_ENUM) else str(h["action"])
            block = dict(h)
            block["action"] = action_str
            block["blockHash"] = compute_block_hash(block)
            blocks.append(_standardize_block(block))
        if blocks:
            return APIResponse(success=True, message="Document history blocks fetched from blockchain.", data={"blocks": blocks})
        else:
            raise HTTPException(status_code=404, detail="No history found for this document title.")
    except ContractLogicError as e:
        # Map common revert reasons to 404
        msg = str(e)
        if "Document does not exist" in msg or "Owner does not match" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=500, detail=f"Failed to fetch document history: {msg}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch document history: {str(e)}")

# New GET endpoint: Get latest block for a document
@router.get("/blocks/document/{doctitle}/owner/{owner}/latest", response_model=APIResponse)
async def get_document_latest_block(doctitle: str, owner: str):
    try:
        # Pre-check existence to avoid revert and provide clearer error
        try:
            user_docs = get_user_documents_on_chain(int(owner))
            owner_titles = [d.get("DocTitle") for d in user_docs]
            if doctitle not in owner_titles:
                raise HTTPException(status_code=404, detail="Document not found for this owner")
            d = get_document_on_chain(doctitle, int(owner))
        except Exception as e:
            msg = str(e)
            if "Document does not exist" in msg or "execution reverted" in msg or "no data" in msg:
                raise HTTPException(status_code=404, detail="Document not found for this owner")
            else:
                raise
        action_str = ACTION_ENUM[d["action"]] if isinstance(d["action"], int) and d["action"] < len(ACTION_ENUM) else str(d["action"])
        block = dict(d)
        block["action"] = action_str
        block["blockHash"] = compute_block_hash(block)
        return APIResponse(success=True, message="Latest block for document fetched from blockchain.", data=_standardize_block(block))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch document latest block: {str(e)}")
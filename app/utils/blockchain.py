from eth_utils import to_bytes, to_hex

def encode_bytes32(val: str) -> bytes:
    b = val.encode('utf-8')
    if len(b) > 32:
        raise ValueError('String too long for bytes32')
    return b.ljust(32, b'\0')

def decode_bytes32(val: bytes) -> str:
    return val.rstrip(b'\0').decode('utf-8')
import os
from web3 import Web3
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
from dotenv import load_dotenv

load_dotenv()




# --- Network selection: Optimism or Sepolia ---
NETWORK = os.getenv("NETWORK", "optimism").lower()
if NETWORK == "optimism":
    RPC_URL = os.getenv("OPTIMISM_RPC_URL")
    CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
    PRIVATE_KEY = os.getenv("PRIVATE_KEY")
elif NETWORK == "sepolia":
    RPC_URL = os.getenv("SEPOLIA_RPC_URL")
    CONTRACT_ADDRESS = os.getenv("SEPOLIA_CONTRACT_ADDRESS")
    PRIVATE_KEY = os.getenv("SEPOLIA_PRIVATE_KEY") or os.getenv("PRIVATE_KEY")
else:
    raise RuntimeError(f"Unsupported NETWORK: {NETWORK}. Use 'optimism' or 'sepolia'.")

if not RPC_URL:
    raise RuntimeError(f"No RPC URL found for {NETWORK}. Set the correct RPC URL in .env.")
if not CONTRACT_ADDRESS:
    raise RuntimeError(f"No contract address found for {NETWORK}. Set the correct contract address in .env.")

PINATA_JWT = os.getenv("PINATA_JWT")
INFURA_IPFS_PROJECT_ID = os.getenv("INFURA_IPFS_PROJECT_ID") or os.getenv("IPFS_PROJECT_ID")
INFURA_IPFS_PROJECT_SECRET = os.getenv("INFURA_IPFS_PROJECT_SECRET") or os.getenv("IPFS_PROJECT_SECRET")

# Load ABI from a JSON file or paste it directly
import json

def _load_contract_abi() -> list:
    """Load ABI from common locations, preferring Hardhat artifact structure.
    Supports either raw ABI array or artifact JSON with an 'abi' field.
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    candidate_paths = [
        os.path.join(base_dir, 'artifacts', 'contracts', 'Enhancedblockdocument.sol', 'EnhancedBlockDocument.json'),
        os.path.join(base_dir, 'contracts', 'EnhancedBlockDocument.json'),
        os.path.join(base_dir, 'contract', 'Enhancedblockdocument.json'),
    ]
    for path in candidate_paths:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict) and 'abi' in data:
                    return data['abi']
                if isinstance(data, list):
                    return data
        except FileNotFoundError:
            continue
    raise FileNotFoundError('Contract ABI not found in artifacts or contract directories')

CONTRACT_ABI = _load_contract_abi()

w3 = Web3(Web3.HTTPProvider(RPC_URL))
account = w3.eth.account.from_key(PRIVATE_KEY)
contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=CONTRACT_ABI)

def upload_to_pinata(file_bytes, filename):
    m = MultipartEncoder(
        fields={
            "file": (filename, file_bytes),
            "pinataMetadata": ('', '{"name": "%s"}' % filename, 'application/json')
        }
    )
    headers = {
        "Authorization": f"Bearer {PINATA_JWT}",
        "Content-Type": m.content_type
    }
    response = requests.post("https://api.pinata.cloud/pinning/pinFileToIPFS", data=m, headers=headers)
    response.raise_for_status()
    data = response.json()
    return data.get("IpfsHash") or data.get("IpfsCid") or data.get("cid") or data.get("Hash")

def upload_to_infura_ipfs(file_bytes: bytes, filename: str) -> str:
    """Upload a file to Infura IPFS API v0 and return CID."""
    auth = None
    if INFURA_IPFS_PROJECT_ID and INFURA_IPFS_PROJECT_SECRET:
        auth = (INFURA_IPFS_PROJECT_ID, INFURA_IPFS_PROJECT_SECRET)
    files = {"file": (filename, file_bytes)}
    resp = requests.post("https://ipfs.infura.io:5001/api/v0/add", files=files, auth=auth)
    resp.raise_for_status()
    info = resp.json()
    # Infura returns { Name, Hash, Size }
    return info.get("Hash") or info.get("Cid")

def upload_file(file_bytes: bytes, filename: str) -> str:
    """Try Pinata first; if not configured or fails, try Infura IPFS. Return CID."""
    last_err: Exception | None = None
    if PINATA_JWT:
        try:
            return upload_to_pinata(file_bytes, filename)
        except Exception as e:
            last_err = e
    # Fallback to Infura IPFS
    try:
        return upload_to_infura_ipfs(file_bytes, filename)
    except Exception as e:
        if last_err is not None:
            raise RuntimeError(f"Pinata and Infura IPFS upload failed: pinata={last_err}, infura={e}")
        raise

def is_owner(user_address, document_id):
    doc = contract.functions.documents(user_address, document_id).call()
    return doc[0].lower() == user_address.lower()  # Adjust index as per your contract

def has_shared_access(owner_address, document_id, user_address):
    return contract.functions.sharedAccess(owner_address, document_id, user_address).call()

def _get_create_document_inputs_len() -> int:
    for entry in CONTRACT_ABI:
        if entry.get('type') == 'function' and entry.get('name') == 'createDocument':
            return len(entry.get('inputs', []))
    return -1

def create_document_on_chain(doc_title: str, owner: str, last_access_date: int, ipfs_hash: str):
    fn = contract.functions.createDocument(
        encode_bytes32(doc_title),
        int(owner),  # Owner is now uint64
        int(last_access_date),
        encode_bytes32(ipfs_hash)
    )
    tx = fn.build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 500000,
        "gasPrice": w3.to_wei("1", "gwei"),
    })
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt

def share_document_on_chain(doc_title: str, owner: str, shared_user: str, permissions: str, shared_end_date: int | None, last_access_date: int):
    """permissions: 'view', 'download', or 'both'"""
    perm_map = {"view": 0, "download": 1}
    base_nonce = w3.eth.get_transaction_count(account.address)

    def send_one(perm_value: int, nonce: int):
        tx = contract.functions.shareDocument(
            encode_bytes32(doc_title),
            int(owner),  # Owner is now uint64
            encode_bytes32(shared_user),
            perm_value,
            int(shared_end_date or 0),
            int(last_access_date),
        ).build_transaction({
            "from": account.address,
            "nonce": nonce,
            "gas": 500000,
            "gasPrice": w3.to_wei("1", "gwei"),
        })
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        return w3.eth.wait_for_transaction_receipt(tx_hash)

    permissions = (permissions or "").lower()
    if permissions == "both":
        r1 = send_one(perm_map["view"], base_nonce)
        r2 = send_one(perm_map["download"], base_nonce + 1)
        return [r1, r2]
    elif permissions in perm_map:
        return send_one(perm_map[permissions], base_nonce)
    else:
        raise ValueError("permissions must be 'view', 'download', or 'both'")

def access_document_on_chain(doc_title: str, owner: str, action_type: int, last_access_date: int):
    if action_type not in (0, 1):
        raise ValueError("action_type must be 0 (View) or 1 (Download)")
    tx = contract.functions.accessDocument(
        encode_bytes32(doc_title),
        int(owner),  # Owner is now uint64
        int(action_type),
        int(last_access_date)
    ).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 300000,
        "gasPrice": w3.to_wei("1", "gwei"),
    })
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt

def get_document_on_chain(doc_title: str, owner: str):
    doc = contract.functions.getDocument(
        encode_bytes32(doc_title),
        int(owner)
    ).call()
    # To get previousHash, fetch ActionRecord from documentHistory mapping
    # This requires a separate call to getDocumentHistory and extract previousHash
    try:
        history = contract.functions.getDocumentHistory(
            encode_bytes32(doc_title),
            int(owner)
        ).call()
        previous_hash = history[0][10] if history and len(history[0]) > 10 else b''
    except Exception:
        previous_hash = b''
    return {
        "DocTitle": decode_bytes32(doc[0]),
        "Owner": int(doc[1]),  # Owner is now uint64
        "LastAccessDate": int(doc[2]),
        "LastAccessedBy": decode_bytes32(doc[3]),
        "action": int(doc[4]),
        "SharedUser": decode_bytes32(doc[5]),
        "SharedEndDate": int(doc[6]),
        "ipfsHash": decode_bytes32(doc[7]),
        "TimeStamp": int(doc[8]),
        "previousHash": previous_hash.hex() if isinstance(previous_hash, bytes) else str(previous_hash),
    }

def get_user_documents_on_chain(owner: str):
    docs = contract.functions.getUserDocuments(int(owner)).call()
    results = []
    for d in docs:
        results.append({
            "DocTitle": decode_bytes32(d[0]),
            "Owner": int(d[1]),  # Owner is now uint64
            "LastAccessDate": int(d[2]),
            "LastAccessedBy": decode_bytes32(d[3]),
            "action": int(d[4]),
            "SharedUser": decode_bytes32(d[5]),
            "SharedEndDate": int(d[6]),
            "ipfsHash": decode_bytes32(d[7]),
            "TimeStamp": int(d[8]),
        })
    return results

def get_document_history_on_chain(doc_title: str, owner: str):
    hist = contract.functions.getDocumentHistory(
        encode_bytes32(doc_title),
        int(owner)
    ).call()
    results = []
    for r in hist:
        results.append({
            "DocTitle": decode_bytes32(r[0]),
            "Owner": int(r[1]),  # Owner is now uint64
            "LastAccessDate": int(r[2]),
            "LastAccessedBy": decode_bytes32(r[3]),
            "action": int(r[4]),
            "SharedUser": decode_bytes32(r[5]),
            "SharedEndDate": int(r[6]),
            "ipfsHash": decode_bytes32(r[7]),
            "TimeStamp": int(r[8]),
            "timestamp": int(r[9]),
            "previousHash": r[10],
        })
    return results
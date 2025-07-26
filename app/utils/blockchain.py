import os
from web3 import Web3
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
from dotenv import load_dotenv

load_dotenv()

INFURA_URL = "https://sepolia.infura.io/v3/b6b72fbbcb4b4e91a927ad90c9c3629d"
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
PINATA_JWT = os.getenv("PINATA_JWT")

# Load ABI from a JSON file or paste it directly
import json
ABI_PATH = os.path.join(os.path.dirname(__file__), '../../contract/Enhancedblockdocument.json')
with open(ABI_PATH) as f:
    CONTRACT_ABI = json.load(f)

w3 = Web3(Web3.HTTPProvider(INFURA_URL))
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

def is_owner(user_address, document_id):
    doc = contract.functions.documents(user_address, document_id).call()
    return doc[0].lower() == user_address.lower()  # Adjust index as per your contract

def has_shared_access(owner_address, document_id, user_address):
    return contract.functions.sharedAccess(owner_address, document_id, user_address).call()

def create_document_on_chain(doc_id, owner):
    tx = contract.functions.createDocument(doc_id, owner).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 300000,
        "gasPrice": w3.to_wei("10", "gwei"),
    })
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt
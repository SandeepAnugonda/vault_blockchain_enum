# BlockDocument

BlockDocument is a FastAPI-based backend for secure document management using blockchain technology. It integrates with an Ethereum smart contract (deployed on Sepolia testnet) to record document actions (create, update, share, access) immutably, and uses IPFS (via Pinata) for decentralized file storage.

## Features
- Create, update, and share documents with blockchain-backed audit trails
- Store and retrieve document metadata and actions as blockchain blocks
- Share documents with specific permissions (view/download/both) and expiry
- Access control for document actions
- Integration with Ethereum smart contract (Solidity, Hardhat)
- IPFS file uploads via Pinata
- RESTful API endpoints for all operations

## Tech Stack
- Python 3.13, FastAPI, Pydantic
- web3.py (Ethereum interaction)
- Solidity (Smart Contract)
- Hardhat (contract deployment)
- Pinata (IPFS)
- dotenv (environment variables)

## Setup Instructions

1. **Clone the repository**
2. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```
3. **Configure environment variables:**
   - Copy `.env.example` to `.env` and fill in:
     - `SEPOLIA_RPC_URL` (Infura endpoint)
     - `PRIVATE_KEY` (Ethereum wallet private key)
     - `CONTRACT_ADDRESS` (Deployed contract address)
     - `PINATA_JWT` (Pinata JWT for IPFS uploads)

4. **Compile and deploy the smart contract:**
   - Edit `contracts/Enhancedblockdocument.sol` as needed
   - Deploy using Hardhat:
     ```
     npx hardhat run scripts/deploy.js --network sepolia
     ```
   - Copy the deployed contract address to `.env`
   - Copy the ABI from `artifacts/contracts/Enhancedblockdocument.sol/EnhancedBlockDocument.json` to `contract/Enhancedblockdocument.json`

5. **Run the FastAPI server:**
   ```
   uvicorn app.main:app --reload
   ```

## API Endpoints

- `POST /create-block` — Create a new document block (and record on blockchain)
- `PUT /update-document` — Update a document and create a new block
- `POST /access-document` — Access (view/download) a document, with permission checks
- `POST /share-document` — Share a document with another user (with permissions)
- `GET /owner/{owner}/documents` — List all documents for an owner
- `GET /owner/{owner}/document/{doc_id}` — Get the latest block for a document
- `GET /document/{doc_id}/complete-history` — Get all blocks (history) for a document

## Notes
- All blockchain and document actions are stored as blocks in memory and on-chain
- IPFS integration is for file storage; only hashes are stored in the backend
- The backend is stateless except for in-memory block storage (for demo/testing)

## License
MIT

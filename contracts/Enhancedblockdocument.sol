// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract EnhancedBlockDocument {
    address public owner; // Authorized account for all operations

    // Enum for document action
    enum Action { Created, Shared, Viewed, Downloaded, Shared_view, Shared_download }

    // Enum for permission in shareDocument
    enum Permission { View, Download }

    // Struct for document block
    struct Document {
        bytes32 DocTitle; // Document title
        uint64 Owner; // Owner ID (changed from bytes32 to uint64)
        uint64 LastAccessDate; // When block was created/updated
        bytes32 LastAccessedBy; // User ID or email who last accessed
        Action action; // Current action of document
        bytes32 SharedUser; // User with whom document is shared
        uint64 SharedEndDate; // Share end date as timestamp
        bytes32 ipfsHash; // IPFS hash
        uint64 TimeStamp; // Blockchain-generated timestamp
    }

    // Struct for action history
    struct ActionRecord {
        bytes32 DocTitle; // Document title
        uint64 Owner; // Owner ID (changed from bytes32 to uint64)
        uint64 LastAccessDate; // Frontend-provided timestamp
        bytes32 LastAccessedBy; // User who performed the action
        Action action; // Action type
        bytes32 SharedUser; // User with whom document was shared
        uint64 SharedEndDate; // Share end date
        bytes32 ipfsHash; // IPFS hash
        uint64 TimeStamp; // Blockchain-generated timestamp
        uint64 timestamp; // When the action occurred
        bytes32 previousHash; // Hash of previous ActionRecord
    }

    // Mappings
    mapping(bytes32 => Document) internal documents; // DocTitle => Document (internal to hide in transactions)
    mapping(uint64 => bytes32[]) public userDocuments; // Owner (uint64) => DocTitles
    mapping(bytes32 => ActionRecord) public documentHistory; // DocTitle => Latest ActionRecord
    mapping(bytes32 => ActionRecord) public historyByHash; // Hash => Previous ActionRecord

    // Events
    event DocumentCreated(bytes32 DocTitle, uint64 Owner, uint64 LastAccessDate, bytes32 LastAccessedBy, Action action, bytes32 SharedUser, uint64 SharedEndDate, bytes32 ipfsHash, uint64 TimeStamp);
    // Removed DocumentUpdated event
    event DocumentShared(bytes32 DocTitle, uint64 Owner, uint64 LastAccessDate, bytes32 LastAccessedBy, Action action, bytes32 SharedUser, uint64 SharedEndDate, bytes32 ipfsHash, uint64 TimeStamp);
    event DocumentAccessed(bytes32 DocTitle, uint64 Owner, uint64 LastAccessDate, bytes32 LastAccessedBy, Action action, bytes32 SharedUser, uint64 SharedEndDate, bytes32 ipfsHash, uint64 TimeStamp);

    constructor() {
        owner = msg.sender;
    }

    // Internal function to compute hash of ActionRecord
    function _computeHash(ActionRecord memory record) internal pure returns (bytes32) {
        return keccak256(abi.encode(
            record.DocTitle,
            record.Owner,
            record.LastAccessDate,
            record.LastAccessedBy,
            record.action,
            record.SharedUser,
            record.SharedEndDate,
            record.ipfsHash,
            record.TimeStamp,
            record.timestamp,
            record.previousHash
        ));
    }

    // Internal function to record action and update history
    function _recordAction(
        bytes32 _DocTitle,
        uint64 _Owner,
        uint64 _LastAccessDate,
        bytes32 _LastAccessedBy,
        Action _action,
        bytes32 _SharedUser,
        uint64 _SharedEndDate
    ) internal {
        uint64 currentTimestamp = uint64(block.timestamp);
        ActionRecord memory currentRecord = documentHistory[_DocTitle];
        bytes32 currentHash = _computeHash(currentRecord);
        historyByHash[currentHash] = currentRecord;
        bytes32 ipfsHash = currentRecord.ipfsHash;
        documentHistory[_DocTitle] = ActionRecord({
            DocTitle: _DocTitle,
            Owner: _Owner,
            LastAccessDate: _LastAccessDate,
            LastAccessedBy: _LastAccessedBy,
            action: _action,
            SharedUser: _SharedUser,
            SharedEndDate: _SharedEndDate,
            ipfsHash: ipfsHash,
            TimeStamp: currentTimestamp,
            timestamp: currentTimestamp,
            previousHash: currentHash
        });

        if (_action == Action.Created) {
            emit DocumentCreated(_DocTitle, _Owner, _LastAccessDate, _LastAccessedBy, _action, _SharedUser, _SharedEndDate, ipfsHash, currentTimestamp);
        } else if (_action == Action.Shared_view || _action == Action.Shared_download) {
            emit DocumentShared(_DocTitle, _Owner, _LastAccessDate, _LastAccessedBy, _action, _SharedUser, _SharedEndDate, ipfsHash, currentTimestamp);
        } else {
            emit DocumentAccessed(_DocTitle, _Owner, _LastAccessDate, _LastAccessedBy, _action, _SharedUser, _SharedEndDate, ipfsHash, currentTimestamp);
        }
    }

    // Create new document block
    function createDocument(
        bytes32 _DocTitle,
        uint64 _Owner,
        uint64 _LastAccessDate,
        bytes32 _ipfsHash
    ) public {
        require(documentHistory[_DocTitle].ipfsHash == bytes32(0), "Document already exists");
        require(_ipfsHash != bytes32(0), "IPFS hash cannot be empty");

        if (documentHistory[_DocTitle].ipfsHash == bytes32(0)) {
            userDocuments[_Owner].push(_DocTitle);
        }
        // Set ipfsHash in ActionRecord for Created action
        uint64 currentTimestamp = uint64(block.timestamp);
        documentHistory[_DocTitle] = ActionRecord({
            DocTitle: _DocTitle,
            Owner: _Owner,
            LastAccessDate: _LastAccessDate,
            LastAccessedBy: bytes32(0),
            action: Action.Created,
            SharedUser: bytes32(0),
            SharedEndDate: 0,
            ipfsHash: _ipfsHash,
            TimeStamp: currentTimestamp,
            timestamp: currentTimestamp,
            previousHash: bytes32(0)
        });
    emit DocumentCreated(_DocTitle, _Owner, _LastAccessDate, bytes32(0), Action.Created, bytes32(0), 0, _ipfsHash, currentTimestamp);
    }

    // Get all documents for a user
    function getUserDocuments(uint64 _Owner)
        public
        view
        returns (Document[] memory)
    {
        bytes32[] memory docTitles = userDocuments[_Owner];
        Document[] memory userDocs = new Document[](docTitles.length);

        for (uint i = 0; i < docTitles.length; i++) {
            ActionRecord memory record = documentHistory[docTitles[i]];
            userDocs[i] = Document({
                DocTitle: docTitles[i],
                Owner: _Owner,
                LastAccessDate: record.LastAccessDate,
                LastAccessedBy: record.LastAccessedBy,
                action: record.action,
                SharedUser: record.SharedUser,
                SharedEndDate: record.SharedEndDate,
                ipfsHash: record.ipfsHash,
                TimeStamp: uint64(block.timestamp)
            });
        }

        return userDocs;
    }

    // Get specific document
    function getDocument(bytes32 _DocTitle, uint64 _Owner)
        public
        view
        returns (Document memory)
    {
        require(documentHistory[_DocTitle].ipfsHash != bytes32(0), "Document does not exist");
        require(documentHistory[_DocTitle].Owner == _Owner, "Owner does not match");
        ActionRecord memory record = documentHistory[_DocTitle];
        return Document({
            DocTitle: _DocTitle,
            Owner: record.Owner,
            LastAccessDate: record.LastAccessDate,
            LastAccessedBy: record.LastAccessedBy,
            action: record.action,
            SharedUser: record.SharedUser,
            SharedEndDate: record.SharedEndDate,
            ipfsHash: record.ipfsHash,
            TimeStamp: uint64(block.timestamp)
        });
    }

    // Get document history
    function getDocumentHistory(bytes32 _DocTitle, uint64 _Owner)
        public
        view
        returns (ActionRecord[] memory)
    {
        require(documentHistory[_DocTitle].ipfsHash != bytes32(0), "Document does not exist");
        require(documentHistory[_DocTitle].Owner == _Owner, "Owner does not match");

        // Count history length
        uint256 count = 0;
        bytes32 currentHash = documentHistory[_DocTitle].previousHash;
        count = 1; // Include latest record
        while (currentHash != bytes32(0)) {
            count++;
            currentHash = historyByHash[currentHash].previousHash;
        }

        // Build history array
        ActionRecord[] memory result = new ActionRecord[](count);
        result[0] = documentHistory[_DocTitle];
        currentHash = documentHistory[_DocTitle].previousHash;
        for (uint256 i = 1; i < count; i++) {
            result[i] = historyByHash[currentHash];
            currentHash = historyByHash[currentHash].previousHash;
        }

        return result;
    }

    // Share document
    function shareDocument(
        bytes32 _DocTitle,
        uint64 _Owner,
        bytes32 _SharedUser,
        Permission _permission,
        uint64 _SharedEndDate,
        uint64 _LastAccessDate
    ) public {
        require(documentHistory[_DocTitle].ipfsHash != bytes32(0), "Document does not exist");
        require(documentHistory[_DocTitle].Owner == _Owner, "Owner does not match");

        Action _action = _permission == Permission.View ? Action.Shared_view : Action.Shared_download;
        _recordAction(_DocTitle, _Owner, _LastAccessDate, bytes32(0), _action, _SharedUser, _SharedEndDate);
    }

    // Access document (view or download)
    function accessDocument(
        bytes32 _DocTitle,
        uint64 _Owner,
        uint8 _action,
        uint64 _LastAccessDate
    ) public {
        require(documentHistory[_DocTitle].ipfsHash != bytes32(0), "Document does not exist");
        require(documentHistory[_DocTitle].Owner == _Owner, "Owner does not match");
        require(_action <= 1, "Invalid action: must be 0 (View) or 1 (Download)");

        Action _finalAction = _action == 0 ? Action.Viewed : Action.Downloaded;
        _recordAction(_DocTitle, _Owner, _LastAccessDate, bytes32(0), _finalAction, bytes32(0), 0);
    }
}



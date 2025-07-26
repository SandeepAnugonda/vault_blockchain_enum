// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract EnhancedBlockDocument {
address public owner;

// Removed duplicate onlyOwner modifier
enum Action { Created, Updated, Shared, Viewed, Downloaded, Shared_view, Shared_download }
enum Permission { View, Download }

struct Document {
    string DocTitle;
    string Owner;
    uint256 LastAccessDate;
    string LastAccessedBy;
    Action action;
    string SharedUser;
    string SharedEndDate;
}

// Define ActionRecord struct outside Document
struct ActionRecord {
    Action action;
    uint256 timestamp;
    string LastAccessedBy;
    string SharedUser;
    string SharedEndDate;
}

// Mappings outside Document struct
mapping(string => Document) public documents;
mapping(string => string[]) public userDocuments;
mapping(string => ActionRecord[]) public documentHistory;

// Events outside Document struct
event DocumentCreated(string DocTitle, string Owner, uint256 LastAccessDate);
event DocumentUpdated(string DocTitle, string Owner, uint256 LastAccessDate);
event DocumentShared(string DocTitle, string Owner, string SharedUser, string SharedEndDate, uint256 LastAccessDate);
event DocumentAccessed(string DocTitle, string Owner, uint8 action, uint256 LastAccessDate);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can perform this action");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function createDocument(string memory _DocTitle, string memory _Owner) public onlyOwner {
        require(bytes(documents[_DocTitle].DocTitle).length == 0, "Document already exists");
        documents[_DocTitle] = Document({
            DocTitle: _DocTitle,
            Owner: _Owner,
            LastAccessDate: block.timestamp,
            LastAccessedBy: _Owner,
            action: Action.Created,
            SharedUser: "",
            SharedEndDate: ""
        });
        userDocuments[_Owner].push(_DocTitle);
        documentHistory[_DocTitle].push(ActionRecord({
            action: Action.Created,
            timestamp: block.timestamp,
            LastAccessedBy: _Owner,
            SharedUser: "",
            SharedEndDate: ""
        }));
        emit DocumentCreated(_DocTitle, _Owner, block.timestamp);
    }

    function getUserDocuments(string memory _Owner) public view onlyOwner returns (Document[] memory) {
        string[] memory docTitles = userDocuments[_Owner];
        Document[] memory userDocs = new Document[](docTitles.length);
        for (uint i = 0; i < docTitles.length; i++) {
            userDocs[i] = documents[docTitles[i]];
        }
        return userDocs;
    }

    function getDocument(string memory _DocTitle) public view onlyOwner returns (Document memory) {
        require(bytes(documents[_DocTitle].DocTitle).length != 0, "Document does not exist");
        return documents[_DocTitle];
    }

    function getDocumentHistory(string memory _DocTitle, string memory _Owner) public view onlyOwner returns (ActionRecord[] memory) {
        require(bytes(documents[_DocTitle].DocTitle).length != 0, "Document does not exist");
        require(keccak256(bytes(documents[_DocTitle].Owner)) == keccak256(bytes(_Owner)), "Owner does not match");
        return documentHistory[_DocTitle];
    }

    function updateDocument(string memory _Owner, string memory _oldDocTitle, string memory _newDocTitle) public onlyOwner {
        require(bytes(documents[_oldDocTitle].DocTitle).length != 0, "Old document does not exist");
        require(bytes(documents[_newDocTitle].DocTitle).length == 0, "New document title already exists");
        require(keccak256(bytes(documents[_oldDocTitle].Owner)) == keccak256(bytes(_Owner)), "Owner does not match");
        string[] storage docTitles = userDocuments[_Owner];
        for (uint i = 0; i < docTitles.length; i++) {
            if (keccak256(bytes(docTitles[i])) == keccak256(bytes(_oldDocTitle))) {
                docTitles[i] = docTitles[docTitles.length - 1];
                docTitles.pop();
                break;
            }
        }
        documentHistory[_newDocTitle] = documentHistory[_oldDocTitle];
        delete documentHistory[_oldDocTitle];
        delete documents[_oldDocTitle];
        documents[_newDocTitle] = Document({
            DocTitle: _newDocTitle,
            Owner: _Owner,
            LastAccessDate: block.timestamp,
            LastAccessedBy: _Owner,
            action: Action.Updated,
            SharedUser: "",
            SharedEndDate: ""
        });
        userDocuments[_Owner].push(_newDocTitle);
        documentHistory[_newDocTitle].push(ActionRecord({
            action: Action.Updated,
            timestamp: block.timestamp,
            LastAccessedBy: _Owner,
            SharedUser: "",
            SharedEndDate: ""
        }));
        emit DocumentUpdated(_newDocTitle, _Owner, block.timestamp);
    }

    function shareDocument(string memory _DocTitle, string memory _Owner, string memory _SharedUser, Permission _permission, string memory _SharedEndDate) public onlyOwner {
        require(bytes(documents[_DocTitle].DocTitle).length != 0, "Document does not exist");
        require(keccak256(bytes(documents[_DocTitle].Owner)) == keccak256(bytes(_Owner)), "Owner does not match");
        require(bytes(_SharedEndDate).length == 8, "SharedEndDate must be 8 digits (DDMMYYYY)");
        documents[_DocTitle].action = _permission == Permission.View ? Action.Shared_view : Action.Shared_download;
        documents[_DocTitle].LastAccessedBy = _Owner;
        documents[_DocTitle].LastAccessDate = block.timestamp;
        documents[_DocTitle].SharedUser = _SharedUser;
        documents[_DocTitle].SharedEndDate = _SharedEndDate;
        documentHistory[_DocTitle].push(ActionRecord({
            action: _permission == Permission.View ? Action.Shared_view : Action.Shared_download,
            timestamp: block.timestamp,
            LastAccessedBy: _Owner,
            SharedUser: _SharedUser,
            SharedEndDate: _SharedEndDate
        }));
        emit DocumentShared(_DocTitle, _Owner, _SharedUser, _SharedEndDate, block.timestamp);
    }

    function accessDocument(string memory _DocTitle, string memory _Owner, uint8 _action) public onlyOwner {
        require(bytes(documents[_DocTitle].DocTitle).length != 0, "Document does not exist");
        require(keccak256(bytes(documents[_DocTitle].Owner)) == keccak256(bytes(_Owner)), "Owner does not match");
        require(_action <= 1, "Invalid action: must be 0 (View) or 1 (Download)");
        documents[_DocTitle].action = _action == 0 ? Action.Viewed : Action.Downloaded;
        documents[_DocTitle].LastAccessedBy = _Owner;
        documents[_DocTitle].LastAccessDate = block.timestamp;
        documents[_DocTitle].SharedUser = "";
        documents[_DocTitle].SharedEndDate = "";
        documentHistory[_DocTitle].push(ActionRecord({
            action: _action == 0 ? Action.Viewed : Action.Downloaded,
            timestamp: block.timestamp,
            LastAccessedBy: _Owner,
            SharedUser: "",
            SharedEndDate: ""
        }));
        emit DocumentAccessed(_DocTitle, _Owner, _action, block.timestamp);
    }
}
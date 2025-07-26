# // SPDX-License-Identifier: MIT
# pragma solidity ^0.8.0;
# 
# contract VaultDocument {
    # address public owner; // Authorized account for all operations
# 
    # // Enum for document action
    # enum Action { Created, Updated, Shared, Viewed, Downloaded, Shared_view, Shared_download }
# 
    # // Enum for permission in shareDocument
    # enum Permission { View, Download }
# 
    # // Struct for document block
    # struct Document {
        # string DocTitle; // Document title
        # string Owner; // Owner ID
        # uint256 LastAccessDate; // When block was created/updated
        # string LastAccessedBy; // User ID or email who last accessed
        # Action action; // Current action of document
        # string SharedUser; // User with whom document is shared
        # string SharedEndDate; // Share end date in DDMMYYYY format
    # }
# 
    # // Struct for action history
    # struct ActionRecord {
        # Action action; // Action type
        # uint256 timestamp; // When the action occurred
        # string LastAccessedBy; // User who performed the action
        # string SharedUser; // User with whom document was shared (if applicable)
        # string SharedEndDate; // Share end date (if applicable)
    # }
# 
    # // Mappings
    # mapping(string => Document) public documents; // DocTitle => Document
    # mapping(string => string[]) public userDocuments; // Owner => DocTitles
    # mapping(string => ActionRecord[]) public documentHistory; // DocTitle => Action history
# 
    # // Events
    # event DocumentCreated(string DocTitle, string Owner, uint256 LastAccessDate);
    # event DocumentUpdated(string DocTitle, string Owner, uint256 LastAccessDate);
    # event DocumentShared(string DocTitle, string Owner, string SharedUser, string SharedEndDate, uint256 LastAccessDate);
    # event DocumentAccessed(string DocTitle, string Owner, uint8 action, uint256 LastAccessDate);
# 
    # // Modifier to restrict access to owner
    # modifier onlyOwner() {
        # require(msg.sender == owner, "Only owner can perform this action");
        # _;
    # }
# 
    # constructor() {
        # owner = msg.sender;
    # }
# 
    # // Create new document block
    # function createDocument(
        # string memory _DocTitle,
        # string memory _Owner
    # ) public onlyOwner {
        # require(bytes(documents[_DocTitle].DocTitle).length == 0, "Document already exists");
# 
        # documents[_DocTitle] = Document({
            # DocTitle: _DocTitle,
            # Owner: _Owner,
            # LastAccessDate: block.timestamp,
            # LastAccessedBy: _Owner,
            # action: Action.Created,
            # SharedUser: "",
            # SharedEndDate: ""
        # });
# 
        # userDocuments[_Owner].push(_DocTitle);
# 
        # // Record action in history
        # documentHistory[_DocTitle].push(ActionRecord({
            # action: Action.Created,
            # timestamp: block.timestamp,
            # LastAccessedBy: _Owner,
            # SharedUser: "",
            # SharedEndDate: ""
        # }));
# 
        # emit DocumentCreated(_DocTitle, _Owner, block.timestamp);
    # }
# 
    # // Get all documents for a user
    # function getUserDocuments(string memory _Owner) 
        # public 
        # view 
        # onlyOwner 
        # returns (Document[] memory) 
    # {
        # string[] memory docTitles = userDocuments[_Owner];
        # Document[] memory userDocs = new Document[](docTitles.length);
# 
        # for (uint i = 0; i < docTitles.length; i++) {
            # userDocs[i] = documents[docTitles[i]];
        # }
# 
        # return userDocs;
    # }
# 
    # // Get specific document
    # function getDocument(string memory _DocTitle) 
        # public 
        # view 
        # onlyOwner 
        # returns (Document memory) 
    # {
        # require(bytes(documents[_DocTitle].DocTitle).length != 0, "Document does not exist");
        # return documents[_DocTitle];
    # }
# 
    # // Get document history
    # function getDocumentHistory(string memory _DocTitle, string memory _Owner) 
        # public 
        # view 
        # onlyOwner 
        # returns (ActionRecord[] memory) 
    # {
        # require(bytes(documents[_DocTitle].DocTitle).length != 0, "Document does not exist");
        # require(keccak256(bytes(documents[_DocTitle].Owner)) == keccak256(bytes(_Owner)), 
            # "Owner does not match");
        # return documentHistory[_DocTitle];
    # }
# 
    # // Update document
    # function updateDocument(
        # string memory _Owner,
        # string memory _oldDocTitle,
        # string memory _newDocTitle
    # ) public onlyOwner {
        # require(bytes(documents[_oldDocTitle].DocTitle).length != 0, "Old document does not exist");
        # require(bytes(documents[_newDocTitle].DocTitle).length == 0, "New document title already exists");
        # require(keccak256(bytes(documents[_oldDocTitle].Owner)) == keccak256(bytes(_Owner)), 
            # "Owner does not match");
# 
        # // Remove old document title from userDocuments
        # string[] storage docTitles = userDocuments[_Owner];
        # for (uint i = 0; i < docTitles.length; i++) {
            # if (keccak256(bytes(docTitles[i])) == keccak256(bytes(_oldDocTitle))) {
                # docTitles[i] = docTitles[docTitles.length - 1];
                # docTitles.pop();
                # break;
            # }
        # }
# 
        # // Transfer history to new DocTitle
        # documentHistory[_newDocTitle] = documentHistory[_oldDocTitle];
        # delete documentHistory[_oldDocTitle];
# 
        # // Delete old document
        # delete documents[_oldDocTitle];
# 
        # // Create new document
        # documents[_newDocTitle] = Document({
            # DocTitle: _newDocTitle,
            # Owner: _Owner,
            # LastAccessDate: block.timestamp,
            # LastAccessedBy: _Owner,
            # action: Action.Updated,
            # SharedUser: "",
            # SharedEndDate: ""
        # });
# 
        # userDocuments[_Owner].push(_newDocTitle);
# 
        # // Record action in history
        # documentHistory[_newDocTitle].push(ActionRecord({
            # action: Action.Updated,
            # timestamp: block.timestamp,
            # LastAccessedBy: _Owner,
            # SharedUser: "",
            # SharedEndDate: ""
        # }));
# 
        # emit DocumentUpdated(_newDocTitle, _Owner, block.timestamp);
    # }
# 
    # // Share document
    # function shareDocument(
        # string memory _DocTitle,
        # string memory _Owner,
        # string memory _SharedUser,
        # Permission _permission,
        # string memory _SharedEndDate
    # ) public onlyOwner {
        # require(bytes(documents[_DocTitle].DocTitle).length != 0, "Document does not exist");
        # require(keccak256(bytes(documents[_DocTitle].Owner)) == keccak256(bytes(_Owner)), 
            # "Owner does not match");
        # require(bytes(_SharedEndDate).length == 8, "SharedEndDate must be 8 digits (DDMMYYYY)");
# 
        # documents[_DocTitle].action = _permission == Permission.View 
            # ? Action.Shared_view 
            # : Action.Shared_download;
        # documents[_DocTitle].LastAccessedBy = _Owner;
        # documents[_DocTitle].LastAccessDate = block.timestamp;
        # documents[_DocTitle].SharedUser = _SharedUser;
        # documents[_DocTitle].SharedEndDate = _SharedEndDate;
# 
        # // Record action in history
        # documentHistory[_DocTitle].push(ActionRecord({
            # action: _permission == Permission.View ? Action.Shared_view : Action.Shared_download,
            # timestamp: block.timestamp,
            # LastAccessedBy: _Owner,
            # SharedUser: _SharedUser,
            # SharedEndDate: _SharedEndDate
        # }));
# 
        # emit DocumentShared(_DocTitle, _Owner, _SharedUser, _SharedEndDate, block.timestamp);
    # }
# 
    # // Access document (view or download)
    # function accessDocument(
        # string memory _DocTitle,
        # string memory _Owner,
        # uint8 _action
    # ) public onlyOwner {
        # require(bytes(documents[_DocTitle].DocTitle).length != 0, "Document does not exist");
        # require(keccak256(bytes(documents[_DocTitle].Owner)) == keccak256(bytes(_Owner)), 
            # "Owner does not match");
        # require(_action <= 1, "Invalid action: must be 0 (View) or 1 (Download)");
# 
        # documents[_DocTitle].action = _action == 0 
            # ? Action.Viewed 
            # : Action.Downloaded;
        # documents[_DocTitle].LastAccessedBy = _Owner;
        # documents[_DocTitle].LastAccessDate = block.timestamp;
        # documents[_DocTitle].SharedUser = "";
        # documents[_DocTitle].SharedEndDate = "";
# 
        # // Record action in history
        # documentHistory[_DocTitle].push(ActionRecord({
            # action: _action == 0 ? Action.Viewed : Action.Downloaded,
            # timestamp: block.timestamp,
            # LastAccessedBy: _Owner,
            # SharedUser: "",
            # SharedEndDate: ""
        # }));
# 
        # emit DocumentAccessed(_DocTitle, _Owner, _action, block.timestamp);
    # }
# }
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract TaxRecord {
    struct Record {
        string userId;
        string details;
        uint256 timestamp;
    }

    mapping(uint256 => Record) public records;
    uint256 public recordCount;

    event RecordAdded(uint256 id, string userId, string details, uint256 timestamp);

    function addRecord(string memory _userId, string memory _details) public {
        recordCount++;
        records[recordCount] = Record(_userId, _details, block.timestamp);
        emit RecordAdded(recordCount, _userId, _details, block.timestamp);
    }

    function getRecord(uint256 _id) public view returns (string memory, string memory, uint256) {
        Record memory rec = records[_id];
        return (rec.userId, rec.details, rec.timestamp);
    }
}

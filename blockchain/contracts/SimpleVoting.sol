// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SimpleVoting {
    // Ultra simple structures
    struct Election {
        uint256 id;
        string title;
        string description;
        address creator;
        bool exists;
        uint256 totalVotes;
    }
    
    struct Candidate {
        uint256 id;
        string name;
        address candidateAddress;
        uint256 voteCount;
        bool exists;
    }
    
    // Simple storage
    uint256 public electionCounter;
    mapping(uint256 => Election) public elections;
    mapping(uint256 => mapping(uint256 => Candidate)) public candidates;
    mapping(uint256 => uint256) public candidateCounters;
    mapping(uint256 => mapping(address => bool)) public hasVoted;
    
    // Events
    event ElectionCreated(uint256 indexed electionId, string title);
    event CandidateAdded(uint256 indexed electionId, uint256 indexed candidateId, string name);
    event VoteCast(uint256 indexed electionId, uint256 indexed candidateId, address voter);
    
    // ULTRA SIMPLE: Create election (no time complexity)
    function createElection(
        string memory title,
        string memory description,
        uint256, // startTime - ignored for simplicity
        uint256  // endTime - ignored for simplicity
    ) public returns (uint256) {
        electionCounter++;
        
        elections[electionCounter] = Election({
            id: electionCounter,
            title: title,
            description: description,
            creator: msg.sender,
            exists: true,
            totalVotes: 0
        });
        
        candidateCounters[electionCounter] = 0;
        
        emit ElectionCreated(electionCounter, title);
        return electionCounter;
    }
    
    // ULTRA SIMPLE: Add candidate
    function addCandidate(
        uint256 electionId,
        address candidateAddress,
        string memory name
    ) public returns (uint256) {
        require(elections[electionId].exists, "Election does not exist");
        require(msg.sender == elections[electionId].creator, "Only creator can add candidates");
        
        candidateCounters[electionId]++;
        uint256 candidateId = candidateCounters[electionId];
        
        candidates[electionId][candidateId] = Candidate({
            id: candidateId,
            name: name,
            candidateAddress: candidateAddress,
            voteCount: 0,
            exists: true
        });
        
        emit CandidateAdded(electionId, candidateId, name);
        return candidateId;
    }
    
    // ULTRA SIMPLE: Vote (no time checks)
    function vote(
        uint256 electionId,
        uint256 candidateId,
        string memory // ignored
    ) public {
        require(elections[electionId].exists, "Election does not exist");
        require(candidates[electionId][candidateId].exists, "Candidate does not exist");
        require(!hasVoted[electionId][msg.sender], "Already voted");
        
        candidates[electionId][candidateId].voteCount++;
        hasVoted[electionId][msg.sender] = true;
        elections[electionId].totalVotes++;
        
        emit VoteCast(electionId, candidateId, msg.sender);
    }
    
    // Simple getter functions
    function getCurrentElectionId() public view returns (uint256) {
        return electionCounter;
    }
    
    function getCandidateCount(uint256 electionId) public view returns (uint256) {
        require(elections[electionId].exists, "Election does not exist");
        return candidateCounters[electionId];
    }
    
    function hasUserVoted(uint256 electionId, address user) public view returns (bool) {
        require(elections[electionId].exists, "Election does not exist");
        return hasVoted[electionId][user];
    }
    
    function getCandidateVotes(uint256 electionId, uint256 candidateId) public view returns (uint256) {
        require(elections[electionId].exists, "Election does not exist");
        require(candidates[electionId][candidateId].exists, "Candidate does not exist");
        return candidates[electionId][candidateId].voteCount;
    }
    
    function getTotalVotes(uint256 electionId) public view returns (uint256) {
        require(elections[electionId].exists, "Election does not exist");
        return elections[electionId].totalVotes;
    }
    
    function getElectionBasic(uint256 electionId) public view returns (uint256, uint256, uint256, address) {
        require(elections[electionId].exists, "Election does not exist");
        return (elections[electionId].id, 0, 0, elections[electionId].creator); // Return 0 for time fields
    }
    
    function getElectionInfo(uint256 electionId) public view returns (string memory, string memory, address) {
        require(elections[electionId].exists, "Election does not exist");
        return (elections[electionId].title, elections[electionId].description, elections[electionId].creator);
    }
    
    function getCandidateInfo(uint256 electionId, uint256 candidateId) public view returns (string memory, address) {
        require(elections[electionId].exists, "Election does not exist");
        require(candidates[electionId][candidateId].exists, "Candidate does not exist");
        return (candidates[electionId][candidateId].name, candidates[electionId][candidateId].candidateAddress);
    }
    
    // SIMPLIFIED: Get election results - return simple arrays
    function getElectionResults(uint256 electionId) public view returns (
        uint256[] memory candidateIds,
        string[] memory names,
        uint256[] memory voteCounts,
        uint256 totalVotes
    ) {
        require(elections[electionId].exists, "Election does not exist");
        
        uint256 count = candidateCounters[electionId];
        candidateIds = new uint256[](count);
        names = new string[](count);
        voteCounts = new uint256[](count);
        
        for (uint256 i = 1; i <= count; i++) {
            candidateIds[i-1] = i;
            names[i-1] = candidates[electionId][i].name;
            voteCounts[i-1] = candidates[electionId][i].voteCount;
        }
        
        totalVotes = elections[electionId].totalVotes;
        return (candidateIds, names, voteCounts, totalVotes);
    }
    
    // Dummy functions for compatibility (always return false/0)
    function isElectionActive(uint256) public pure returns (bool) {
        return true; // Always active for simplicity
    }
    
    function hasElectionEnded(uint256) public pure returns (bool) {
        return false; // Never ended for simplicity
    }
    
    function getVoteCount(uint256 electionId) public view returns (uint256) {
        require(elections[electionId].exists, "Election does not exist");
        return elections[electionId].totalVotes;
    }
    
    function getVoteAtIndex(uint256, uint256) public view returns (address, uint256, uint256) {
        return (address(0), 0, 0); // Dummy implementation
    }
    
    function getVotesByCandidate(uint256 electionId, uint256 candidateId) public view returns (uint256) {
        require(elections[electionId].exists, "Election does not exist");
        require(candidates[electionId][candidateId].exists, "Candidate does not exist");
        return candidates[electionId][candidateId].voteCount;
    }
}
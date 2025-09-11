// SPDX-License-Identifier: MIT
pragma solidity ^0.5.16;
pragma experimental ABIEncoderV2;

contract SimpleVotingWithUpdate {
    // Same simple structures as your original
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
    
    // Same storage as original + one new mapping
    uint256 public electionCounter;
    mapping(uint256 => Election) public elections;
    mapping(uint256 => mapping(uint256 => Candidate)) public candidates;
    mapping(uint256 => uint256) public candidateCounters;
    mapping(uint256 => mapping(address => bool)) public hasVoted;
    
    // NEW: Track what each user voted for (for updates)
    mapping(uint256 => mapping(address => uint256)) public userVotes;
    
    // Same events + one new event
    event ElectionCreated(uint256 indexed electionId, string title);
    event CandidateAdded(uint256 indexed electionId, uint256 indexed candidateId, string name);
    event VoteCast(uint256 indexed electionId, uint256 indexed candidateId, address voter);
    event VoteUpdated(uint256 indexed electionId, address voter, uint256 oldCandidateId, uint256 newCandidateId);
    
    // EXACT SAME: Create election
    function createElection(
        string memory title,
        string memory description,
        uint256,
        uint256
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
    
    // EXACT SAME: Add candidate
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
    
    // MODIFIED: Vote (now tracks what user voted for)
    function vote(
        uint256 electionId,
        uint256 candidateId,
        string memory
    ) public {
        require(elections[electionId].exists, "Election does not exist");
        require(candidates[electionId][candidateId].exists, "Candidate does not exist");
        require(!hasVoted[electionId][msg.sender], "Already voted");
        
        candidates[electionId][candidateId].voteCount++;
        hasVoted[electionId][msg.sender] = true;
        elections[electionId].totalVotes++;
        
        // NEW: Track what they voted for
        userVotes[electionId][msg.sender] = candidateId;
        
        emit VoteCast(electionId, candidateId, msg.sender);
    }
    
    // NEW: Update vote function
    function updateVote(
        uint256 electionId,
        uint256 newCandidateId
    ) public {
        require(elections[electionId].exists, "Election does not exist");
        require(candidates[electionId][newCandidateId].exists, "Candidate does not exist");
        require(hasVoted[electionId][msg.sender], "No vote to update");
        
        uint256 oldCandidateId = userVotes[electionId][msg.sender];
        require(oldCandidateId != newCandidateId, "Already voting for this candidate");
        
        // Update vote counts
        candidates[electionId][oldCandidateId].voteCount--;
        candidates[electionId][newCandidateId].voteCount++;
        
        // Update user's vote record
        userVotes[electionId][msg.sender] = newCandidateId;
        
        emit VoteUpdated(electionId, msg.sender, oldCandidateId, newCandidateId);
    }
    
    // ALL THE SAME GETTER FUNCTIONS AS YOUR ORIGINAL
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
    
    function getElectionInfo(uint256 electionId) public view returns (string memory, string memory, address) {
        require(elections[electionId].exists, "Election does not exist");
        return (elections[electionId].title, elections[electionId].description, elections[electionId].creator);
    }
    
    function getCandidateInfo(uint256 electionId, uint256 candidateId) public view returns (string memory, address) {
        require(elections[electionId].exists, "Election does not exist");
        require(candidates[electionId][candidateId].exists, "Candidate does not exist");
        return (candidates[electionId][candidateId].name, candidates[electionId][candidateId].candidateAddress);
    }
    
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
    
    // NEW: Get what user voted for
    function getUserVote(uint256 electionId, address user) public view returns (uint256) {
        require(elections[electionId].exists, "Election does not exist");
        require(hasVoted[electionId][user], "User has not voted");
        return userVotes[electionId][user];
    }
    
    // Dummy functions for compatibility
    function isElectionActive(uint256) public pure returns (bool) {
        return true;
    }
    
    function hasElectionEnded(uint256) public pure returns (bool) {
        return false;
    }
}
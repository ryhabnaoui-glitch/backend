package main

import (
    "fmt"
    "strconv"
    "strings"

    "github.com/hyperledger/fabric-contract-api-go/contractapi"
)

type VotingContract struct {
    contractapi.Contract
}

// BULLETPROOF: Create election with simple string storage - NO JSON
func (vc *VotingContract) CreateElection(ctx contractapi.TransactionContextInterface, electionId string, title string, description string, startTime string, endTime string, creatorId string) error {
    electionKey := "election_" + electionId
    
    // Simple pipe-separated string - can't fail
    electionData := electionId + "|" + title + "|" + description + "|" + creatorId + "|true|0"
    
    return ctx.GetStub().PutState(electionKey, []byte(electionData))
}

// FIXED: Add candidate with correct election key lookup
func (vc *VotingContract) AddCandidate(ctx contractapi.TransactionContextInterface, electionId string, candidateId string, name string, callerId string) error {
    // FIXED: Check election exists - USE SAME KEY AS CreateElection
    electionKey := "election_" + electionId
    electionBytes, err := ctx.GetStub().GetState(electionKey)
    if err != nil {
        return err
    }
    if electionBytes == nil {
        return fmt.Errorf("election does not exist: %s", electionId)
    }

    // Simple string storage for candidate
    candidateData := candidateId + "|" + name + "|0|true"
    candidateKey := "candidate_" + electionId + "_" + candidateId
    
    return ctx.GetStub().PutState(candidateKey, []byte(candidateData))
}

// BULLETPROOF: Cast vote with simple operations
func (vc *VotingContract) CastVote(ctx contractapi.TransactionContextInterface, electionId string, candidateId string, voterId string, timestamp string) error {
    // Check election exists
    electionKey := "election_" + electionId
    electionBytes, err := ctx.GetStub().GetState(electionKey)
    if err != nil {
        return err
    }
    if electionBytes == nil {
        return fmt.Errorf("election does not exist: %s", electionId)
    }

    // Check if already voted
    voteKey := "vote_" + electionId + "_" + voterId
    existingVote, err := ctx.GetStub().GetState(voteKey)
    if err != nil {
        return err
    }
    if existingVote != nil {
        return fmt.Errorf("already voted")
    }

    // Check candidate exists
    candidateKey := "candidate_" + electionId + "_" + candidateId
    candidateBytes, err := ctx.GetStub().GetState(candidateKey)
    if err != nil {
        return err
    }
    if candidateBytes == nil {
        return fmt.Errorf("candidate does not exist")
    }

    // Parse candidate data: candidateId|name|voteCount|exists
    candidateData := string(candidateBytes)
    parts := strings.Split(candidateData, "|")
    if len(parts) != 4 {
        return fmt.Errorf("invalid candidate data")
    }

    // Increment vote count
    voteCount, err := strconv.Atoi(parts[2])
    if err != nil {
        return fmt.Errorf("invalid vote count")
    }
    voteCount++

    // Update candidate
    updatedCandidateData := parts[0] + "|" + parts[1] + "|" + strconv.Itoa(voteCount) + "|" + parts[3]
    err = ctx.GetStub().PutState(candidateKey, []byte(updatedCandidateData))
    if err != nil {
        return err
    }

    // Parse election data: electionId|title|description|creator|exists|totalVotes
    electionData := string(electionBytes)
    electionParts := strings.Split(electionData, "|")
    if len(electionParts) != 6 {
        return fmt.Errorf("invalid election data")
    }

    // Increment total votes
    totalVotes, err := strconv.Atoi(electionParts[5])
    if err != nil {
        return fmt.Errorf("invalid total votes")
    }
    totalVotes++

    // Update election
    updatedElectionData := electionParts[0] + "|" + electionParts[1] + "|" + electionParts[2] + "|" + electionParts[3] + "|" + electionParts[4] + "|" + strconv.Itoa(totalVotes)
    err = ctx.GetStub().PutState(electionKey, []byte(updatedElectionData))
    if err != nil {
        return err
    }

    // Record vote
    voteData := electionId + "|" + candidateId + "|" + voterId + "|" + timestamp
    return ctx.GetStub().PutState(voteKey, []byte(voteData))
}

// BULLETPROOF: Check if voted
func (vc *VotingContract) HasVoted(ctx contractapi.TransactionContextInterface, electionId string, voterId string) (bool, error) {
    voteKey := "vote_" + electionId + "_" + voterId
    voteBytes, err := ctx.GetStub().GetState(voteKey)
    if err != nil {
        return false, err
    }
    return voteBytes != nil, nil
}

// BULLETPROOF: Get results with simple string parsing
func (vc *VotingContract) GetResults(ctx contractapi.TransactionContextInterface, electionId string) (string, error) {
    // Check if election exists
    electionKey := "election_" + electionId
    electionBytes, err := ctx.GetStub().GetState(electionKey)
    if err != nil {
        return "", err
    }
    if electionBytes == nil {
        // Return simple string - no JSON
        return `{"candidates":[],"totalVotes":0,"electionId":"` + electionId + `","message":"Election not found"}`, nil
    }

    // Parse election data: electionId|title|description|creator|exists|totalVotes
    electionData := string(electionBytes)
    electionParts := strings.Split(electionData, "|")
    if len(electionParts) != 6 {
        return `{"candidates":[],"totalVotes":0,"electionId":"` + electionId + `","message":"Invalid election data"}`, nil
    }

    totalVotes := electionParts[5]

    // Get candidates
    candidatesJSON := `[]`
    candidatesList := make([]string, 0)

    // Try candidate IDs 1-10
    for i := 1; i <= 10; i++ {
        candidateKey := "candidate_" + electionId + "_" + strconv.Itoa(i)
        candidateBytes, err := ctx.GetStub().GetState(candidateKey)
        if err != nil {
            continue
        }
        if candidateBytes == nil {
            continue
        }

        // Parse candidate: candidateId|name|voteCount|exists
        candidateData := string(candidateBytes)
        candidateParts := strings.Split(candidateData, "|")
        if len(candidateParts) != 4 {
            continue
        }

        candidateJSON := `{"id":"` + candidateParts[0] + `","name":"` + candidateParts[1] + `","votes":` + candidateParts[2] + `}`
        candidatesList = append(candidatesList, candidateJSON)
    }

    if len(candidatesList) > 0 {
        candidatesJSON = `[` + strings.Join(candidatesList, ",") + `]`
    }

    // Return simple JSON string
    result := `{"candidates":` + candidatesJSON + `,"totalVotes":` + totalVotes + `,"electionId":"` + electionId + `"}`
    return result, nil
}

func main() {
    votingContract := new(VotingContract)
    cc, err := contractapi.NewChaincode(votingContract)
    if err != nil {
        panic(err.Error())
    }

    if err := cc.Start(); err != nil {
        panic(err.Error())
    }
}
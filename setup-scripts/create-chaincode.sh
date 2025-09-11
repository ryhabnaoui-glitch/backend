#!/bin/bash

echo "📦 Creating voting chaincode..."

mkdir -p ../chaincode/voting

# Create voting.go
cat > ../chaincode/voting/voting.go << 'EOF'
package main

import (
    "encoding/json"
    "fmt"
    "strconv"
    "time"

    "github.com/hyperledger/fabric-contract-api-go/contractapi"
)

type VotingContract struct {
    contractapi.Contract
}

type Election struct {
    ID          string `json:"id"`
    Title       string `json:"title"`
    Description string `json:"description"`
    StartTime   int64  `json:"startTime"`
    EndTime     int64  `json:"endTime"`
    CreatorID   string `json:"creatorId"`
    Active      bool   `json:"active"`
}

type Candidate struct {
    ID         string `json:"id"`
    ElectionID string `json:"electionId"`
    Name       string `json:"name"`
    VoteCount  int    `json:"voteCount"`
}

type Vote struct {
    ID         string `json:"id"`
    ElectionID string `json:"electionId"`
    CandidateID string `json:"candidateId"`
    VoterID    string `json:"voterId"`
    Timestamp  int64  `json:"timestamp"`
}

func (vc *VotingContract) CreateElection(ctx contractapi.TransactionContextInterface, title string, description string, startTime string, endTime string, creatorId string) error {
    st, _ := strconv.ParseInt(startTime, 10, 64)
    et, _ := strconv.ParseInt(endTime, 10, 64)
    
    electionId := fmt.Sprintf("election_%d", time.Now().Unix())
    
    election := Election{
        ID:          electionId,
        Title:       title,
        Description: description,
        StartTime:   st,
        EndTime:     et,
        CreatorID:   creatorId,
        Active:      true,
    }

    electionJSON, err := json.Marshal(election)
    if err != nil {
        return err
    }

    return ctx.GetStub().PutState("ELECTION_"+electionId, electionJSON)
}

func (vc *VotingContract) AddCandidate(ctx contractapi.TransactionContextInterface, electionId string, candidateId string, name string, callerId string) error {
    candidate := Candidate{
        ID:         candidateId,
        ElectionID: electionId,
        Name:       name,
        VoteCount:  0,
    }

    candidateJSON, err := json.Marshal(candidate)
    if err != nil {
        return err
    }

    return ctx.GetStub().PutState("CANDIDATE_"+electionId+"_"+candidateId, candidateJSON)
}

func (vc *VotingContract) CastVote(ctx contractapi.TransactionContextInterface, electionId string, candidateId string, voterId string, timestamp string) error {
    voteKey := "VOTE_" + electionId + "_" + voterId
    existingVoteJSON, err := ctx.GetStub().GetState(voteKey)
    if err != nil {
        return fmt.Errorf("failed to read vote: %v", err)
    }
    if existingVoteJSON != nil {
        return fmt.Errorf("voter %s has already voted in election %s", voterId, electionId)
    }

    ts, _ := strconv.ParseInt(timestamp, 10, 64)
    vote := Vote{
        ID:          voteKey,
        ElectionID:  electionId,
        CandidateID: candidateId,
        VoterID:     voterId,
        Timestamp:   ts,
    }

    voteJSON, err := json.Marshal(vote)
    if err != nil {
        return err
    }

    err = ctx.GetStub().PutState(voteKey, voteJSON)
    if err != nil {
        return err
    }

    candidateKey := "CANDIDATE_" + electionId + "_" + candidateId
    candidateJSON, err := ctx.GetStub().GetState(candidateKey)
    if err != nil {
        return fmt.Errorf("failed to read candidate: %v", err)
    }
    if candidateJSON == nil {
        return fmt.Errorf("candidate does not exist: %s", candidateId)
    }

    var candidate Candidate
    err = json.Unmarshal(candidateJSON, &candidate)
    if err != nil {
        return err
    }

    candidate.VoteCount++
    updatedCandidateJSON, err := json.Marshal(candidate)
    if err != nil {
        return err
    }

    return ctx.GetStub().PutState(candidateKey, updatedCandidateJSON)
}

func (vc *VotingContract) HasVoted(ctx contractapi.TransactionContextInterface, electionId string, voterId string) (bool, error) {
    voteKey := "VOTE_" + electionId + "_" + voterId
    voteJSON, err := ctx.GetStub().GetState(voteKey)
    if err != nil {
        return false, fmt.Errorf("failed to read vote: %v", err)
    }
    return voteJSON != nil, nil
}

func (vc *VotingContract) GetResults(ctx contractapi.TransactionContextInterface, electionId string) (string, error) {
    resultsIterator, err := ctx.GetStub().GetStateByRange("CANDIDATE_"+electionId+"_", "CANDIDATE_"+electionId+"_~")
    if err != nil {
        return "", fmt.Errorf("failed to get candidates: %v", err)
    }
    defer resultsIterator.Close()

    var candidates []map[string]interface{}
    for resultsIterator.HasNext() {
        queryResponse, err := resultsIterator.Next()
        if err != nil {
            return "", err
        }

        var candidate Candidate
        err = json.Unmarshal(queryResponse.Value, &candidate)
        if err != nil {
            return "", err
        }
        
        candidates = append(candidates, map[string]interface{}{
            "id": candidate.ID,
            "name": candidate.Name,
            "votes": candidate.VoteCount,
        })
    }

    result := map[string]interface{}{
        "candidates": candidates,
    }
    
    resultsJSON, err := json.Marshal(result)
    if err != nil {
        return "", err
    }

    return string(resultsJSON), nil
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
EOF

# Create go.mod
cat > ../chaincode/voting/go.mod << 'EOF'
module voting

go 1.19

require github.com/hyperledger/fabric-contract-api-go v1.2.1

require (
    github.com/golang/protobuf v1.5.2 // indirect
    github.com/hyperledger/fabric-chaincode-go v0.0.0-20220720122508-9207360bbddd // indirect
    github.com/hyperledger/fabric-protos-go v0.0.0-20220613214546-bf864f01d9fb // indirect
    github.com/stretchr/testify v1.8.0 // indirect
    google.golang.org/protobuf v1.28.0 // indirect
)
EOF

echo "✅ Voting chaincode created successfully!"

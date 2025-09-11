#!/bin/bash
set -e

echo "🚀 Deploying voting chaincode to Fabric network..."

# Set environment variables
export FABRIC_CFG_PATH=/app/fabric-samples/config
export CORE_PEER_TLS_ENABLED=true
export CORE_PEER_LOCALMSPID=Org1MSP
export CORE_PEER_TLS_ROOTCERT_FILE=/app/fabric-samples/test-network/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt
export CORE_PEER_MSPCONFIGPATH=/app/fabric-samples/test-network/organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp
export CORE_PEER_ADDRESS=peer0.org1.example.com:7051
export ORDERER_CA=/app/fabric-samples/test-network/organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem

CHANNEL_NAME="mychannel"
CHAINCODE_NAME="voting"
CHAINCODE_PATH="/app/blockchain/contracts"
VERSION="1.0"
SEQUENCE=1

echo "📦 Packaging chaincode..."
/app/fabric-samples/bin/peer lifecycle chaincode package ${CHAINCODE_NAME}.tar.gz \
  --path ${CHAINCODE_PATH} \
  --lang node \
  --label ${CHAINCODE_NAME}_${VERSION}

echo "📥 Installing chaincode on peer0.org1..."
/app/fabric-samples/bin/peer lifecycle chaincode install ${CHAINCODE_NAME}.tar.gz

echo "🔍 Querying installed chaincodes..."
/app/fabric-samples/bin/peer lifecycle chaincode queryinstalled

# Get package ID
PACKAGE_ID=$(/app/fabric-samples/bin/peer lifecycle chaincode queryinstalled --output json | jq -r ".installed_chaincodes[0].package_id")
echo "📋 Package ID: $PACKAGE_ID"

echo "✅ Approving chaincode for Org1..."
/app/fabric-samples/bin/peer lifecycle chaincode approveformyorg \
  -o orderer.example.com:7050 \
  --ordererTLSHostnameOverride orderer.example.com \
  --tls \
  --cafile $ORDERER_CA \
  --channelID $CHANNEL_NAME \
  --name $CHAINCODE_NAME \
  --version $VERSION \
  --package-id $PACKAGE_ID \
  --sequence $SEQUENCE

echo "🔄 Switching to Org2..."
export CORE_PEER_LOCALMSPID=Org2MSP
export CORE_PEER_TLS_ROOTCERT_FILE=/app/fabric-samples/test-network/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt
export CORE_PEER_MSPCONFIGPATH=/app/fabric-samples/test-network/organizations/peerOrganizations/org2.example.com/users/Admin@org2.example.com/msp
export CORE_PEER_ADDRESS=peer0.org2.example.com:9051

echo "📥 Installing chaincode on peer0.org2..."
/app/fabric-samples/bin/peer lifecycle chaincode install ${CHAINCODE_NAME}.tar.gz

echo "✅ Approving chaincode for Org2..."
/app/fabric-samples/bin/peer lifecycle chaincode approveformyorg \
  -o orderer.example.com:7050 \
  --ordererTLSHostnameOverride orderer.example.com \
  --tls \
  --cafile $ORDERER_CA \
  --channelID $CHANNEL_NAME \
  --name $CHAINCODE_NAME \
  --version $VERSION \
  --package-id $PACKAGE_ID \
  --sequence $SEQUENCE

echo "🚀 Committing chaincode to channel..."
/app/fabric-samples/bin/peer lifecycle chaincode commit \
  -o orderer.example.com:7050 \
  --ordererTLSHostnameOverride orderer.example.com \
  --tls \
  --cafile $ORDERER_CA \
  --channelID $CHANNEL_NAME \
  --name $CHAINCODE_NAME \
  --version $VERSION \
  --sequence $SEQUENCE \
  --peerAddresses peer0.org1.example.com:7051 \
  --tlsRootCertFiles /app/fabric-samples/test-network/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt \
  --peerAddresses peer0.org2.example.com:9051 \
  --tlsRootCertFiles /app/fabric-samples/test-network/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt

echo "✅ Chaincode deployment completed!"
echo "🎉 Your voting chaincode is now ready on channel: $CHANNEL_NAME"

# Test the chaincode
echo "🧪 Testing chaincode..."
/app/fabric-samples/bin/peer chaincode invoke \
  -o orderer.example.com:7050 \
  --ordererTLSHostnameOverride orderer.example.com \
  --tls \
  --cafile $ORDERER_CA \
  -C $CHANNEL_NAME \
  -n $CHAINCODE_NAME \
  --peerAddresses peer0.org1.example.com:7051 \
  --tlsRootCertFiles /app/fabric-samples/test-network/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt \
  --peerAddresses peer0.org2.example.com:9051 \
  --tlsRootCertFiles /app/fabric-samples/test-network/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt \
  -c '{"function":"InitLedger","Args":[]}'

echo "🎯 Chaincode test completed!"
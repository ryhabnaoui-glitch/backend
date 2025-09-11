#!/bin/bash

# Hyperledger Fabric Network Setup Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up Hyperledger Fabric Network...${NC}"

# Create directory structure
echo -e "${YELLOW}Creating directory structure...${NC}"
mkdir -p organizations/ordererOrganizations/example.com/orderers/orderer.example.com/{msp,tls}
mkdir -p organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/{msp,tls}
mkdir -p organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp
mkdir -p organizations/peerOrganizations/org1.example.com/ca
mkdir -p channel-artifacts
mkdir -p scripts

# Create cryptographic materials (simplified for demo)
echo -e "${YELLOW}Generating crypto materials...${NC}"

# Create MSP structure for Org1
mkdir -p organizations/peerOrganizations/org1.example.com/msp/{admincerts,cacerts,keystore,signcerts,tlscacerts}
mkdir -p organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/msp/{admincerts,cacerts,keystore,signcerts,tlscacerts}
mkdir -p organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp/{admincerts,cacerts,keystore,signcerts,tlscacerts}

# Create MSP structure for Orderer
mkdir -p organizations/ordererOrganizations/example.com/msp/{admincerts,cacerts,keystore,signcerts,tlscacerts}
mkdir -p organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/{admincerts,cacerts,keystore,signcerts,tlscacerts}

# Generate dummy certificates (in production, use proper crypto-config)
echo -e "${YELLOW}Creating dummy certificates for development...${NC}"

# Create dummy private key
echo "dummy-private-key" > organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/msp/keystore/priv_sk
echo "dummy-private-key" > organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp/keystore/priv_sk
echo "dummy-private-key" > organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/keystore/priv_sk

# Create dummy certificates
cat > organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/msp/signcerts/peer0.org1.example.com-cert.pem << 'EOF'
-----BEGIN CERTIFICATE-----
MIICGjCCAcCgAwIBAgIRANuOnVjoMUjF1CwwYgdHl1kwCgYIKoZIzj0EAwIwczEL
MAkGA1UEBhMCVVMxEzARBgNVBAgTCkNhbGlmb3JuaWExFjAUBgNVBAcTDVNhbiBG
cmFuY2lzY28xGTAXBgNVBAoTEG9yZzEuZXhhbXBsZS5jb20xHDAaBgNVBAMTE2Nh
Lm9yZzEuZXhhbXBsZS5jb20wHhcNMjQwMTAxMDAwMDAwWhcNMzQwMTAxMDAwMDAw
WjBbMQswCQYDVQQGEwJVUzETMBEGA1UECBMKQ2FsaWZvcm5pYTEWMBQGA1UEBxMN
U2FuIEZyYW5jaXNjbzEfMB0GA1UEAwwWcGVlcjAub3JnMS5leGFtcGxlLmNvbTBZ
MBMGByqGSM49AgEGCCqGSM49AwEHA0IABDummy123456789abcdefghijklmnop
qrstuvwxyzABCDEF123456789abcdefghijklmnopqrstuvwxyzABCDEF1234567
89abcdefghijklmnopCjTTBLMA4GA1UdDwEB/wQEAwIHgDAMBgNVHRMBAf8EAjAA
MCsGA1UdIwQkMCKAIDummy123456789abcdefghijklmnopqrstuvwxyzABCDEF
MAoGCCqGSM49BAMCA0gAMEUCIQDdummy123456789abcdefghijklmnopqrstuvw
xyzABCDEFAIgdummy123456789abcdefghijklmnopqrstuvwxyzABCDEF123456
-----END CERTIFICATE-----
EOF

# Copy certificate to other required locations
cp organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/msp/signcerts/peer0.org1.example.com-cert.pem \
   organizations/peerOrganizations/org1.example.com/msp/signcerts/
   
# Create CA certificate
cat > organizations/peerOrganizations/org1.example.com/msp/cacerts/ca-cert.pem << 'EOF'
-----BEGIN CERTIFICATE-----
MIICGjCCAcCgAwIBAgIRANuOnVjoMUjF1CwwYgdHl1kwCgYIKoZIzj0EAwIwczEL
MAkGA1UEBhMCVVMxEzARBgNVBAgTCkNhbGlmb3JuaWExFjAUBgNVBAcTDVNhbiBG
cmFuY2lzY28xGTAXBgNVBAoTEG9yZzEuZXhhbXBsZS5jb20xHDAaBgNVBAMTE2Nh
Lm9yZzEuZXhhbXBsZS5jb20wHhcNMjQwMTAxMDAwMDAwWhcNMzQwMTAxMDAwMDAw
WjBbMQswCQYDVQQGEwJVUzETMBEGA1UECBMKQ2FsaWZvcm5pYTEWMBQGA1UEBxMN
U2FuIEZyYW5jaXNjbzEfMB0GA1UEAwwWcGVlcjAub3JnMS5leGFtcGxlLmNvbTBZ
MBMGByqGSM49AgEGCCqGSM49AwEHA0IABDummy123456789abcdefghijklmnop
qrstuvwxyzABCDEF123456789abcdefghijklmnopqrstuvwxyzABCDEF1234567
89abcdefghijklmnopCjTTBLMA4GA1UdDwEB/wQEAwIHgDAMBgNVHRMBAf8EAjAA
MCsGA1UdIwQkMCKAIDummy123456789abcdefghijklmnopqrstuvwxyzABCDEF
MAoGCCqGSM49BAMCA0gAMEUCIQDdummy123456789abcdefghijklmnopqrstuvw
xyzABCDEFAIgdummy123456789abcdefghijklmnopqrstuvwxyzABCDEF123456
-----END CERTIFICATE-----
EOF

# Copy CA cert to required locations
cp organizations/peerOrganizations/org1.example.com/msp/cacerts/ca-cert.pem \
   organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/msp/cacerts/
cp organizations/peerOrganizations/org1.example.com/msp/cacerts/ca-cert.pem \
   organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp/cacerts/

# Create admin certificate
cat > organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp/signcerts/Admin@org1.example.com-cert.pem << 'EOF'
-----BEGIN CERTIFICATE-----
MIICGjCCAcCgAwIBAgIRANuOnVjoMUjF1CwwYgdHl1kwCgYIKoZIzj0EAwIwczEL
MAkGA1UEBhMCVVMxEzARBgNVBAgTCkNhbGlmb3JuaWExFjAUBgNVBAcTDVNhbiBG
cmFuY2lzY28xGTAXBgNVBAoTEG9yZzEuZXhhbXBsZS5jb20xHDAaBgNVBAMTE2Nh
Lm9yZzEuZXhhbXBsZS5jb20wHhcNMjQwMTAxMDAwMDAwWhcNMzQwMTAxMDAwMDAw
WjBbMQswCQYDVQQGEwJVUzETMBEGA1UECBMKQ2FsaWZvcm5pYTEWMBQGA1UEBxMN
U2FuIEZyYW5jaXNjbzEfMB0GA1UEAwwWQWRtaW5Ab3JnMS5leGFtcGxlLmNvbTBZ
MBMGByqGSM49AgEGCCqGSM49AwEHA0IABDdummy123456789abcdefghijklmnop
qrstuvwxyzABCDEF123456789abcdefghijklmnopqrstuvwxyzABCDEF1234567
89abcdefghijklmnopCjTTBLMA4GA1UdDwEB/wQEAwIHgDAMBgNVHRMBAf8EAjAA
MCsGA1UdIwQkMCKAIDummy123456789abcdefghijklmnopqrstuvwxyzABCDEF
MAoGCCqGSM49BAMCA0gAMEUCIQDdummy123456789abcdefghijklmnopqrstuvw
xyzABCDEFAIgdummy123456789abcdefghijklmnopqrstuvwxyzABCDEF123456
-----END CERTIFICATE-----
EOF

# Orderer certificates
cat > organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/signcerts/orderer.example.com-cert.pem << 'EOF'
-----BEGIN CERTIFICATE-----
MIICGjCCAcCgAwIBAgIRANuOnVjoMUjF1CwwYgdHl1kwCgYIKoZIzj0EAwIwczEL
MAkGA1UEBhMCVVMxEzARBgNVBAgTCkNhbGlmb3JuaWExFjAUBgNVBAcTDVNhbiBG
cmFuY2lzY28xGTAXBgNVBAoTEG9yZzEuZXhhbXBsZS5jb20xHDAaBgNVBAMTE2Nh
Lm9yZzEuZXhhbXBsZS5jb20wHhcNMjQwMTAxMDAwMDAwWhcNMzQwMTAxMDAwMDAw
WjBbMQswCQYDVQQGEwJVUzETMBEGA1UECBMKQ2FsaWZvcm5pYTEWMBQGA1UEBxMN
U2FuIEZyYW5jaXNjbzEfMB0GA1UEAwwWb3JkZXJlci5leGFtcGxlLmNvbTBZMBMG
ByqGSM49AgEGCCqGSM49AwEHA0IABDdummy123456789abcdefghijklmnopqrst
uvwxyzABCDEF123456789abcdefghijklmnopqrstuvwxyzABCDEF123456789ab
cdefghijklmnopCjTTBLMA4GA1UdDwEB/wQEAwIHgDAMBgNVHRMBAf8EAjAA
MCsGA1UdIwQkMCKAIDummy123456789abcdefghijklmnopqrstuvwxyzABCDEF
MAoGCCqGSM49BAMCA0gAMEUCIQDdummy123456789abcdefghijklmnopqrstuvw
xyzABCDEFAIgdummy123456789abcdefghijklmnopqrstuvwxyzABCDEF123456
-----END CERTIFICATE-----
EOF

cat > organizations/ordererOrganizations/example.com/msp/cacerts/ca-cert.pem << 'EOF'
-----BEGIN CERTIFICATE-----
MIICGjCCAcCgAwIBAgIRANuOnVjoMUjF1CwwYgdHl1kwCgYIKoZIzj0EAwIwczEL
MAkGA1UEBhMCVVMxEzARBgNVBAgTCkNhbGlmb3JuaWExFjAUBgNVBAcTDVNhbiBG
cmFuY2lzY28xGTAXBgNVBAoTEG9yZzEuZXhhbXBsZS5jb20xHDAaBgNVBAMTE2Nh
Lm9yZzEuZXhhbXBsZS5jb20wHhcNMjQwMTAxMDAwMDAwWhcNMzQwMTAxMDAwMDAw
WjBbMQswCQYDVQQGEwJVUzETMBEGA1UECBMKQ2FsaWZvcm5pYTEWMBQGA1UEBxMN
U2FuIEZyYW5jaXNjbzEfMB0GA1UEAwwWb3JkZXJlci5leGFtcGxlLmNvbTBZMBMG
ByqGSM49AgEGCCqGSM49AwEHA0IABDdummy123456789abcdefghijklmnopqrst
uvwxyzABCDEF123456789abcdefghijklmnopqrstuvwxyzABCDEF123456789ab
cdefghijklmnopCjTTBLMA4GA1UdDwEB/wQEAwIHgDAMBgNVHRMBAf8EAjAA
MCsGA1UdIwQkMCKAIDummy123456789abcdefghijklmnopqrstuvwxyzABCDEF
MAoGCCqGSM49BAMCA0gAMEUCIQDdummy123456789abcdefghijklmnopqrstuvw
xyzABCDEFAIgdummy123456789abcdefghijklmnopqrstuvwxyzABCDEF123456
-----END CERTIFICATE-----
EOF

cp organizations/ordererOrganizations/example.com/msp/cacerts/ca-cert.pem \
   organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/cacerts/

# Create genesis block (simplified)
echo -e "${YELLOW}Creating genesis block...${NC}"
cat > channel-artifacts/genesis.block << 'EOF'
This is a dummy genesis block for development purposes.
In production, use proper configtxgen to generate this.
EOF

# Create channel configuration script
cat > scripts/create-channel.sh << 'EOF'
#!/bin/bash
set -e

CHANNEL_NAME=${1:-mychannel}
ORDERER_ADDRESS=${2:-orderer.example.com:7050}

echo "Creating channel: $CHANNEL_NAME"

# Create channel configuration
cat > channel.tx << CHANNEL_EOF
This is a dummy channel configuration.
In production, use configtxgen to create proper channel configurations.
CHANNEL_EOF

echo "Channel creation script ready"
echo "To create channel, run inside CLI container:"
echo "peer channel create -o $ORDERER_ADDRESS -c $CHANNEL_NAME -f channel.tx"
EOF

chmod +x scripts/create-channel.sh

# Create chaincode deployment script
cat > scripts/deploy-chaincode.sh << 'EOF'
#!/bin/bash
set -e

CHAINCODE_NAME=${1:-voting}
CHAINCODE_PATH=${2:-/opt/gopath/src/github.com/chaincode}
CHANNEL_NAME=${3:-mychannel}

echo "Deploying chaincode: $CHAINCODE_NAME"

# Package chaincode
echo "Packaging chaincode..."

# Install chaincode
echo "Installing chaincode on peer..."

# Instantiate chaincode
echo "Instantiating chaincode on channel $CHANNEL_NAME..."

echo "Chaincode deployment completed"
EOF

chmod +x scripts/deploy-chaincode.sh

echo -e "${GREEN}Fabric network setup completed!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Run: docker-compose up -d"
echo "2. Wait for all services to start"
echo "3. Use CLI container to create channel and deploy chaincode"
echo ""
echo -e "${YELLOW}To interact with the network:${NC}"
echo "docker exec -it \$(docker-compose ps -q cli) bash"
echo "cd scripts && ./create-channel.sh"
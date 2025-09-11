import os
import subprocess
import json
import logging
import time
from typing import Optional, Dict, Any, List
from pathlib import Path
from django.conf import settings

logger = logging.getLogger('EnhancedHyperledgerHandler')

class EnhancedHyperledgerHandler:
    def __init__(self, network_path: Optional[str] = None, channel_name: Optional[str] = None):
        """Initialize Hyperledger handler with Django settings"""
        # Get configuration from Django settings or environment
        hlf_config = getattr(settings, 'BLOCKCHAIN_CONFIG', {}).get('HYPERLEDGER', {})
        
        self.network_path = network_path or os.getenv('FABRIC_NETWORK_PATH', '/opt/fabric-samples/test-network')
        self.channel_name = channel_name or os.getenv('CHANNEL_NAME', 'mychannel')
        self.chaincode_name = os.getenv('CHAINCODE_NAME', 'voting')
        self.chaincode_version = '2.0'
        
        logger.info(f"Initialized Hyperledger handler for network: {self.network_path}")
        logger.info(f"Channel: {self.channel_name}, Chaincode: {self.chaincode_name}")

    def _get_environment_variables(self) -> Dict[str, str]:
        """Get environment variables for Hyperledger commands"""
        return {
            'CORE_PEER_TLS_ENABLED': os.getenv('CORE_PEER_TLS_ENABLED', 'true'),
            'CORE_PEER_LOCALMSPID': os.getenv('CORE_PEER_LOCALMSPID', 'Org1MSP'),
            'CORE_PEER_MSPCONFIGPATH': os.getenv('CORE_PEER_MSPCONFIGPATH', '/opt/organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp'),
            'FABRIC_CFG_PATH': os.getenv('FABRIC_CFG_PATH', '/opt/fabric-config'),
            'PATH': os.getenv('PATH', '/opt/hyperledger-fabric-bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin')
        }

    def _invoke_chaincode(self, function: str, args: List[str] = None, timeout: int = 30) -> Dict[str, Any]:
        """Invoke chaincode function with arguments and enhanced error handling"""
        if args is None:
            args = []
        
        cmd = [
            'peer', 'chaincode', 'invoke',
            '-o', os.getenv('ORDERER_ADDRESS', 'orderer.example.com:7050'),
            '--tls',
            '--cafile', os.getenv('ORDERER_TLS_ROOTCERT_FILE', '/opt/organizations/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem'),
            '-C', self.channel_name,
            '-n', self.chaincode_name,
            '--peerAddresses', 'peer0.org1.example.com:7051',
            '--tlsRootCertFiles', '/opt/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt',
            '--peerAddresses', 'peer0.org2.example.com:9051',  # ADD THIS
            '--tlsRootCertFiles', '/opt/organizations/peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt',  # ADD THIS
            '-c', json.dumps({"function": function, "Args": args})
        ]
        
        logger.info(f"Executing command: {function} with args: {args}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.network_path,
                env=self._get_environment_variables()
            )
            
            logger.info(f"Command result - Return code: {result.returncode}")
            logger.info(f"Command stdout: {result.stdout}")
            if result.stderr:
                logger.warning(f"Command stderr: {result.stderr}")
            
            if result.returncode != 0:
                # Enhanced error parsing
                error_message = result.stderr or result.stdout or "Unknown error"
                
                # Extract meaningful error from Hyperledger response
                if "endorsement failure" in error_message:
                    # Extract the actual error message
                    if 'message:"' in error_message:
                        start = error_message.find('message:"') + 9
                        end = error_message.find('"', start)
                        if end > start:
                            extracted_error = error_message[start:end]
                            raise Exception(extracted_error)
                
                raise Exception(f"Chaincode invocation failed: {error_message}")
            
            return {
                'success': True,
                'transactionId': f'hlf_tx_{function}_{int(time.time())}',
                'output': result.stdout,
                'function': function,
                'args': args
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"Command timeout after {timeout} seconds")
            raise Exception(f"Chaincode invocation timed out after {timeout} seconds")
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            raise

    def _query_chaincode(self, function: str, args: List[str] = None, timeout: int = 30) -> Dict[str, Any]:
        """Query chaincode function with arguments and enhanced error handling"""
        if args is None:
            args = []
        
        cmd = [
            'peer', 'chaincode', 'query',
            '-C', self.channel_name,
            '-n', self.chaincode_name,
            '--peerAddresses', os.getenv('CORE_PEER_ADDRESS', 'peer0.org1.example.com:7051'),
            '--tlsRootCertFiles', os.getenv('CORE_PEER_TLS_ROOTCERT_FILE', '/opt/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt'),
            '-c', json.dumps({"function": function, "Args": args})
        ]
        
        logger.info(f"Querying: {function} with args: {args}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.network_path,
                env=self._get_environment_variables()
            )
            
            logger.info(f"Query result - Return code: {result.returncode}")
            logger.info(f"Query stdout: {result.stdout}")
            if result.stderr:
                logger.warning(f"Query stderr: {result.stderr}")
            
            if result.returncode != 0:
                error_message = result.stderr or result.stdout or "Unknown error"
                raise Exception(f"Chaincode query failed: {error_message}")
            
            # Parse JSON response if possible
            response_data = None
            if result.stdout:
                try:
                    response_data = json.loads(result.stdout.strip())
                except json.JSONDecodeError:
                    response_data = result.stdout.strip()
            
            return {
                'success': True,
                'data': response_data,
                'raw_output': result.stdout,
                'function': function,
                'args': args
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"Query timeout after {timeout} seconds")
            raise Exception(f"Chaincode query timed out after {timeout} seconds")
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def create_election(self, title: str, description: str, start_time: int, end_time: int, creator_id: str, db_election_id: str = None) -> Dict[str, Any]:
        """Create election with enhanced error handling"""
        try:
            election_id = db_election_id or f"election_{int(time.time())}"
            
            logger.info(f"Creating election: {election_id} - {title}")
            
            args = [election_id, title, description, str(start_time), str(end_time), creator_id]
            result = self._invoke_chaincode('CreateElection', args, timeout=60)
            
            return {
                'success': True,
                'electionId': election_id,
                'dbElectionId': db_election_id,
                'transactionId': result.get('transactionId'),
                'title': title,
                'message': f'Election "{title}" created successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to create election: {e}")
            raise Exception(f"Election creation failed: {str(e)}")

    def add_candidate(self, election_id: str, candidate_id: str, name: str, caller_id: str) -> Dict[str, Any]:
        """Add candidate with enhanced error handling"""
        try:
            logger.info(f"Adding candidate: {name} (ID: {candidate_id}) to election {election_id}")
            
            args = [election_id, candidate_id, name, caller_id]
            result = self._invoke_chaincode('AddCandidate', args, timeout=60)
            
            return {
                'success': True,
                'candidateId': candidate_id,
                'candidateName': name,
                'electionId': election_id,
                'transactionId': result.get('transactionId'),
                'message': f'Candidate "{name}" added successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to add candidate: {e}")
            raise Exception(f"Candidate addition failed: {str(e)}")

    def ensure_election_and_candidates_exist(self, db_election_id: str, title: str, description: str, creator_id: str, candidates_data: List[Dict]) -> bool:
        """Simple election setup - mirrors Ethereum approach"""
        try:
            logger.info(f"Setting up Hyperledger election: {title} (ID: {db_election_id})")
            
            # 1. Create election (ignore if exists)
            try:
                self._invoke_chaincode('CreateElection', [
                    db_election_id, title, description, "0", "999999999", creator_id
                ])
                logger.info(f"Election created or already exists")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    logger.error(f"Election creation failed: {e}")
                    return False
                logger.info(f"Election already exists")
            
            # 2. Add candidates (ignore if exist)
            for i, candidate_data in enumerate(candidates_data, 1):
                candidate_name = candidate_data.get('name', f'Candidate {i}')
                try:
                    self._invoke_chaincode('AddCandidate', [
                        db_election_id, str(i), candidate_name, creator_id
                    ])
                    logger.info(f"Added candidate {i}: {candidate_name}")
                except Exception as e:
                    logger.info(f"Candidate {candidate_name}: {e}")
            
            logger.info(f"Election setup complete")
            return True
            
        except Exception as e:
            logger.error(f"Election setup failed: {e}")
            return False

    def cast_vote(self, election_id: str, candidate_id: str, voter_id: str) -> Dict[str, Any]:
        """Cast a vote for a candidate in an election with enhanced error handling"""
        try:
            logger.info(f"Casting vote: election={election_id}, candidate={candidate_id}, voter={voter_id}")
            
            # Validate inputs
            if not all([election_id, candidate_id, voter_id]):
                raise Exception("Missing required parameters for vote casting")
            
            # Add timestamp as required by chaincode
            timestamp = str(int(time.time()))
            args = [election_id, candidate_id, voter_id, timestamp]
            
            result = self._invoke_chaincode('CastVote', args, timeout=60)
            
            logger.info(f"Vote cast successfully: {result}")
            
            return {
                'success': True,
                'transactionId': result.get('transactionId'),
                'electionId': election_id,
                'candidateId': candidate_id,
                'voterId': voter_id,
                'timestamp': timestamp,
                'message': 'Vote cast successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to cast vote: {e}")
            raise Exception(f"Vote casting failed: {str(e)}")

    def has_user_voted(self, election_id: str, voter_id: str) -> bool:
        """Check if a user has already voted in an election with enhanced error handling"""
        try:
            logger.info(f"Checking vote status: election={election_id}, voter={voter_id}")
            
            if not all([election_id, voter_id]):
                logger.warning("Missing parameters for vote status check")
                return False
            
            args = [election_id, voter_id]
            result = self._query_chaincode('HasVoted', args)
            
            # Parse boolean response
            if result.get('data') is not None:
                data = result.get('data')
                if isinstance(data, bool):
                    return data
                elif isinstance(data, str):
                    return data.lower() in ['true', '1', 'yes']
            
            logger.info(f"Vote status check result: False (no vote found)")
            return False
            
        except Exception as e:
            logger.error(f"Failed to check vote status: {e}")
            # Return False to allow voting attempt (safer default)
            return False

    def get_election_results(self, election_id: str) -> Dict[str, Any]:
        """Get results for an election with enhanced error handling"""
        try:
            logger.info(f"Getting results for election: {election_id}")
            
            if not election_id:
                raise Exception("Election ID is required")
            
            args = [election_id]
            result = self._query_chaincode('GetResults', args)
            
            if result.get('data'):
                data = result.get('data')
                
                # Handle dict response
                if isinstance(data, dict):
                    candidates = data.get('candidates', []) or []
                    total_votes = sum(candidate.get('votes', 0) for candidate in candidates)
                    
                    return {
                        'success': True,
                        'candidates': candidates,
                        'totalVotes': total_votes,
                        'electionId': election_id,
                        'message': data.get('message', 'Results retrieved successfully')
                    }
                
                # Handle string response (JSON)
                elif isinstance(data, str):
                    try:
                        parsed_data = json.loads(data)
                        candidates = parsed_data.get('candidates', []) or []
                        total_votes = sum(candidate.get('votes', 0) for candidate in candidates)
                        
                        return {
                            'success': True,
                            'candidates': candidates,
                            'totalVotes': total_votes,
                            'electionId': election_id,
                            'message': parsed_data.get('message', 'Results retrieved successfully')
                        }
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse results data: {data}")
            
            # Return empty results if no data
            return {
                'success': True,
                'candidates': [],
                'totalVotes': 0,
                'electionId': election_id,
                'message': 'No results found'
            }
            
        except Exception as e:
            logger.error(f"Failed to get election results: {e}")
            return {
                'success': False,
                'candidates': [],
                'totalVotes': 0,
                'electionId': election_id,
                'error': str(e),
                'message': f'Failed to retrieve results: {str(e)}'
            }

    def get_election_info(self, election_id: str) -> Dict[str, Any]:
        """Get election information with enhanced error handling"""
        try:
            logger.info(f"Getting info for election: {election_id}")
            
            if not election_id:
                raise Exception("Election ID is required")
            
            # Use GetResults to get election info (since we don't have a separate GetElection function)
            result = self.get_election_results(election_id)
            
            if result.get('success'):
                return {
                    'success': True,
                    'electionId': election_id,
                    'exists': True,
                    'candidateCount': len(result.get('candidates', [])),
                    'totalVotes': result.get('totalVotes', 0),
                    'message': 'Election info retrieved successfully'
                }
            else:
                return {
                    'success': False,
                    'electionId': election_id,
                    'exists': False,
                    'candidateCount': 0,
                    'totalVotes': 0,
                    'error': result.get('error', 'Election not found'),
                    'message': 'Election not found'
                }
                
        except Exception as e:
            logger.error(f"Failed to get election info: {e}")
            return {
                'success': False,
                'electionId': election_id,
                'exists': False,
                'candidateCount': 0,
                'totalVotes': 0,
                'error': str(e),
                'message': f'Failed to retrieve election info: {str(e)}'
            }

    def verify_network_connection(self) -> bool:
        """Verify that the Hyperledger network is accessible with enhanced error handling"""
        try:
            logger.info("Verifying network connection")
            
            cmd = [
                'peer', 'lifecycle', 'chaincode', 'querycommitted',
                '-C', self.channel_name,
                '--peerAddresses', os.getenv('CORE_PEER_ADDRESS', 'peer0.org1.example.com:7051'),
                '--tlsRootCertFiles', os.getenv('CORE_PEER_TLS_ROOTCERT_FILE', '/opt/organizations/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt')
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
                cwd=self.network_path,
                env=self._get_environment_variables()
            )
            
            success = result.returncode == 0
            if success:
                logger.info("Network connection verified successfully")
            else:
                logger.error(f"Network verification failed: {result.stderr}")
            
            return success
            
        except subprocess.TimeoutExpired:
            logger.error("Network verification timed out")
            return False
        except Exception as e:
            logger.error(f"Network verification failed: {e}")
            return False

    def test_chaincode_functions(self) -> Dict[str, bool]:
        """Test basic chaincode functions to verify deployment"""
        try:
            logger.info("Testing chaincode functions")
            
            test_results = {}
            test_election_id = f"test_{int(time.time())}"
            
            # Test CreateElection
            try:
                self.create_election(
                    title="Test Election",
                    description="Test Description", 
                    start_time=0,
                    end_time=999999999,
                    creator_id="test_user",
                    db_election_id=test_election_id
                )
                test_results['CreateElection'] = True
                logger.info("CreateElection test: PASSED")
            except Exception as e:
                test_results['CreateElection'] = False
                logger.error(f"CreateElection test: FAILED - {e}")
            
            # Test GetResults
            try:
                result = self.get_election_results(test_election_id)
                test_results['GetResults'] = result.get('success', False)
                logger.info(f"GetResults test: {'PASSED' if test_results['GetResults'] else 'FAILED'}")
            except Exception as e:
                test_results['GetResults'] = False
                logger.error(f"GetResults test: FAILED - {e}")
            
            # Test AddCandidate
            try:
                self.add_candidate(test_election_id, "1", "Test Candidate", "test_user")
                test_results['AddCandidate'] = True
                logger.info("AddCandidate test: PASSED")
            except Exception as e:
                test_results['AddCandidate'] = False
                logger.error(f"AddCandidate test: FAILED - {e}")
            
            # Test HasVoted
            try:
                has_voted = self.has_user_voted(test_election_id, "test_user")
                test_results['HasVoted'] = True
                logger.info("HasVoted test: PASSED")
            except Exception as e:
                test_results['HasVoted'] = False
                logger.error(f"HasVoted test: FAILED - {e}")
            
            return test_results
            
        except Exception as e:
            logger.error(f"Chaincode function testing failed: {e}")
            return {}

# Factory function to create handler instance
def get_hyperledger_handler() -> Optional[EnhancedHyperledgerHandler]:
    """Factory function to create and return Hyperledger handler with comprehensive validation"""
    try:
        handler = EnhancedHyperledgerHandler()
        
        # Test network connection
        if not handler.verify_network_connection():
            logger.warning("Hyperledger network not accessible")
            return None
        
        # Test chaincode functions
        test_results = handler.test_chaincode_functions()
        if not any(test_results.values()):
            logger.warning("No chaincode functions are working")
            return None
        
        logger.info("Hyperledger handler created and validated successfully")
        logger.info(f"Chaincode function test results: {test_results}")
        return handler
        
    except Exception as e:
        logger.error(f"Failed to create Hyperledger handler: {e}")
        return None
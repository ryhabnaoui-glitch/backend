# authentication/views.py - COMPLETE FIXED VERSION WITH PROPER ERROR HANDLING
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from .serializers import UserSerializer, ElectionSerializer, ElectionChoiceSerializer, CandidateSerializer
from .models import User, Election, Candidate, Vote
from blockchain.ethereum_handler import EthereumHandler
from blockchain.ethereum_handler_update import EthereumUpdateHandler
from django.views.decorators.csrf import csrf_exempt
import time
from datetime import datetime
from django.utils import timezone
import logging
import json
import traceback
import os


logger = logging.getLogger(__name__)

# Try to import Hyperledger handler, but don't fail if it doesn't exist
try:
    from blockchain.hyperledger_handler import EnhancedHyperledgerHandler
    HYPERLEDGER_AVAILABLE = True
except ImportError:
    HYPERLEDGER_AVAILABLE = False
    logger.warning("Hyperledger handler not found - Hyperledger features will be disabled")

# Global contract address storage
DEPLOYED_CONTRACT_ADDRESS = None

# ============== HELPER FUNCTIONS ==============

def get_hyperledger_handler():
    """Get configured Hyperledger handler"""
    if not HYPERLEDGER_AVAILABLE:
        return None
    try:
        return EnhancedHyperledgerHandler(
            network_path=os.getenv('FABRIC_NETWORK_PATH', '/opt/fabric-samples/test-network'),
            channel_name='mychannel'
        )
    except Exception as e:
        logger.error(f"Failed to initialize Hyperledger handler: {e}")
        return None

def get_ethereum_handler():
    """Get configured Ethereum handler"""
    try:
        return EthereumHandler()
    except Exception as e:
        logger.error(f"Failed to initialize Ethereum handler: {e}")
        return None


def get_ethereum_update_handler():
    """Get configured Ethereum Update handler"""
    try:
        return EthereumUpdateHandler()
    except Exception as e:
        logger.error(f"Failed to initialize Ethereum Update handler: {e}")
        return None



def auto_assign_wallet_address(user):
    """Auto-assign wallet address to user if they're a candidate"""
    try:
        eth_handler = EthereumHandler()
        if not eth_handler.is_connected():
            print(f"⚠️ Ganache not connected, cannot assign wallet to {user.username}")
            return None
        
        with transaction.atomic():
            used_addresses = set(
                User.objects.exclude(wallet_address__isnull=True)
                           .exclude(wallet_address='')
                           .values_list('wallet_address', flat=True)
            )
            
            accounts = eth_handler.get_accounts()
            available_address = None
            
            for account in accounts:
                if account not in used_addresses:
                    if not User.objects.filter(wallet_address=account).exists():
                        available_address = account
                        break
            
            if not available_address:
                print(f"⚠️ No available Ganache accounts for {user.username}")
                return None
            
            user.wallet_address = available_address
            user.save()
            return available_address
            
    except Exception as e:
        print(f"❌ Auto-assignment failed for {user.username}: {e}")
        return None

def ensure_contract_and_election_exist(election_id=None):
    """Ensure contract and blockchain election exist, create if needed"""
    try:
        global DEPLOYED_CONTRACT_ADDRESS
        
        eth_handler = EthereumHandler()
        if not eth_handler.is_connected():
            print("⚠️ Ganache not connected")
            return False
        
        contract_address = cache.get('voting_system_contract_simple') or DEPLOYED_CONTRACT_ADDRESS
        
        if not contract_address:
            admin_address = eth_handler.w3.eth.accounts[0]
            contract_address = eth_handler.deploy_contract(admin_address)
            cache.set('voting_system_contract_simple', contract_address, 86400)
            DEPLOYED_CONTRACT_ADDRESS = contract_address
            print(f"🚀 Auto-deployed contract: {contract_address}")
        else:
            contract = eth_handler.get_contract(contract_address)
            if not contract:
                print("❌ Failed to load existing contract")
                return False
        
        if election_id:
            try:
                db_election = Election.objects.get(id=election_id)
                
                if not db_election.blockchain_id:
                    admin_address = eth_handler.w3.eth.accounts[0]
                    tx_hash, receipt, blockchain_election_id = eth_handler.create_election(
                        db_election.title,
                        db_election.description,
                        0, 0, admin_address
                    )
                    
                    db_election.blockchain_id = blockchain_election_id
                    db_election.contract_address = contract_address
                    db_election.save()
                    
                    print(f"🗳️ Created election on blockchain: {db_election.title} (ID: {blockchain_election_id})")
                    
                    candidates = Candidate.objects.filter(election=db_election).order_by('id')
                    for i, candidate in enumerate(candidates):
                        try:
                            tx_hash, receipt, candidate_blockchain_id = eth_handler.add_candidate(
                                blockchain_election_id,
                                candidate.wallet_address,
                                candidate.name,
                                admin_address
                            )
                            candidate.blockchain_id = candidate_blockchain_id
                            candidate.save()
                            print(f"✅ Added existing candidate {i+1}: {candidate.name} (Blockchain ID: {candidate_blockchain_id})")
                        except Exception as e:
                            print(f"⚠️ Failed to add existing candidate {candidate.name}: {e}")
            
            except Election.DoesNotExist:
                print(f"❌ Election with ID {election_id} not found in database")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Contract/election setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

# ============== ELECTION MANAGEMENT VIEWS ==============

# ============== ELECTION MANAGEMENT VIEWS - COMPLETELY FIXED ==============

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_available_elections(request):
    """Get available elections for registration dropdown"""
    try:
        elections = Election.objects.filter(is_active=True).order_by('-created_at')
        serializer = ElectionChoiceSerializer(elections, many=True)
        
        return Response({
            'elections': serializer.data,
            'count': elections.count()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_elections(request):
    """Get all elections (admin) or user's election (regular user)"""
    try:
        if request.user.is_admin:
            elections = Election.objects.all().order_by('-created_at')
        else:
            if request.user.selected_election:
                elections = Election.objects.filter(id=request.user.selected_election.id)
            else:
                elections = Election.objects.none()
        
        serializer = ElectionSerializer(elections, many=True)
        
        return Response({
            'elections': serializer.data,
            'count': elections.count()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_election(request):
    """Create new election (admin only)"""
    if not request.user.is_admin:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        data = request.data.copy()
        data['created_by'] = request.user.id
        
        serializer = ElectionSerializer(data=data)
        if serializer.is_valid():
            election = serializer.save()
            
            print(f"✅ Election created: {election.title} (ID: {election.id})")
            
            return Response({
                'message': 'Election created successfully',
                'election': ElectionSerializer(election).data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        print(f"❌ Election creation failed: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_election(request, election_id):
    """Delete election (admin only)"""
    if not request.user.is_admin:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        election = Election.objects.get(id=election_id)
        
        if election.vote_set.exists():
            return Response({
                'error': 'Cannot delete election with existing votes'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        election_title = election.title
        election.delete()
        
        return Response({
            'message': f'Election "{election_title}" deleted successfully'
        }, status=status.HTTP_200_OK)
        
    except Election.DoesNotExist:
        return Response({'error': 'Election not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# authentication/views.py - FIXED get_election_results function

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_election_results(request):
    """Get election results - FIXED VERSION WITH PROPER VOTE FILTERING"""
    try:
        election_id = request.GET.get('election_id')
        
        if election_id:
            try:
                election = Election.objects.get(id=election_id)
            except Election.DoesNotExist:
                return Response({'error': 'Election not found'}, status=status.HTTP_404_NOT_FOUND)
        elif request.user.selected_election:
            election = request.user.selected_election
        else:
            return Response({
                'error': 'No election specified',
                'results': [],
                'total_votes': 0
            }, status=status.HTTP_400_BAD_REQUEST)

        print(f"🔍 Getting results for election: {election.title} (ID: {election.id})")

        # PRIORITY FIX: Check database votes first with proper filtering
        from .models import Vote
        # CRITICAL: Filter votes by BOTH election AND make sure we only get votes for THIS election
        db_votes = Vote.objects.filter(election=election).select_related('candidate', 'candidate__user')
        
        if db_votes.exists():
            print(f"📊 Found {db_votes.count()} database votes for election {election.id}")
            
            results = []
            candidates = {}
            
            # CRITICAL FIX: Only process votes for THIS specific election with unique candidate keys
            for vote in db_votes:
                # Triple-check the vote belongs to this election (defensive programming)
                if vote.election.id != election.id:
                    print(f"⚠️ Skipping vote from wrong election: {vote.election.id} != {election.id}")
                    continue
                
                # CRITICAL: Also check that the candidate belongs to this election
                if vote.candidate.election.id != election.id:
                    print(f"⚠️ Skipping candidate from wrong election: {vote.candidate.election.id} != {election.id}")
                    continue
                    
                candidate_name = vote.candidate.name
                # Use unique key combining candidate ID and name to prevent mixing
                candidate_key = f"{vote.candidate.id}_{candidate_name}_{election.id}"
                
                if candidate_key not in candidates:
                    candidates[candidate_key] = {
                        'blockchain_id': vote.candidate.blockchain_id or (len(candidates) + 1),
                        'name': candidate_name,
                        'vote_count': 0,
                        'email': vote.candidate.user.email if vote.candidate.user else None,
                        'user_id': vote.candidate.user.id if vote.candidate.user else None,
                        'candidate_id': vote.candidate.id,  # Add actual candidate ID
                        'election_id': election.id,  # Verify election ID
                        'manifesto': vote.candidate.manifesto if hasattr(vote.candidate, 'manifesto') else None,
                        'election_type': election.get_election_type_display()
                    }
                candidates[candidate_key]['vote_count'] += 1
            
            results = list(candidates.values())
            total_votes = db_votes.count()  # Use the filtered queryset count
            
            # Additional verification: Make sure all results are from the correct election
            verified_results = []
            for result in results:
                if result.get('election_id') == election.id:
                    verified_results.append(result)
                else:
                    print(f"⚠️ Filtering out result from wrong election: {result}")
            
            print(f"✅ Returning {len(verified_results)} candidates with {total_votes} total votes from database")
            
            return Response({
                'election_id': election.id,
                'election_title': election.title,
                'election_type': election.get_election_type_display(),
                'results': verified_results,
                'total_votes': total_votes,
                'source': 'database',
                'success': True
            }, status=status.HTTP_200_OK)

        # If no database votes, try blockchain
        print("📋 No database votes found, checking blockchain...")
        
        if not election.blockchain_id:
            print(f"⚠️ Election {election.title} not on blockchain yet")
            return Response({
                'error': f'Election "{election.title}" not yet created on blockchain',
                'election': election.title,
                'results': [],
                'total_votes': 0,
                'source': 'none'
            }, status=status.HTTP_200_OK)
        
        # Auto-deploy contract if missing
        contract_address = cache.get('voting_system_contract_simple')
        if not contract_address:
            print("🔄 Contract not found in cache, trying to redeploy...")
            ensure_contract_and_election_exist(election.id)
            contract_address = cache.get('voting_system_contract_simple')
        
        if not contract_address:
            print("❌ Failed to deploy contract")
            return Response({
                'error': 'Failed to deploy voting contract for results',
                'election': election.title,
                'results': [],
                'total_votes': 0,
                'source': 'blockchain_failed'
            }, status=status.HTTP_200_OK)
        
        eth_handler = EthereumHandler()
        if not eth_handler.is_connected():
            print("❌ Ganache not connected")
            return Response({
                'error': 'Ganache connection failed',
                'election': election.title,
                'results': [],
                'total_votes': 0,
                'source': 'ganache_failed'
            }, status=status.HTTP_200_OK)
        
        contract = eth_handler.get_contract(contract_address)
        if not contract:
            print("❌ Failed to load contract")
            return Response({
                'error': 'Failed to load contract',
                'election': election.title,
                'results': [],
                'total_votes': 0,
                'source': 'contract_failed'
            }, status=status.HTTP_200_OK)
        
        # Get blockchain results
        blockchain_results = eth_handler.get_election_results(election.blockchain_id)
        candidates = Candidate.objects.filter(election=election).order_by('id')
        
        formatted_results = []
        for i, (candidate_id, name, vote_count) in enumerate(zip(
            blockchain_results['candidate_ids'], 
            blockchain_results['names'], 
            blockchain_results['vote_counts']
        )):
            candidate_obj = None
            if i < len(candidates):
                candidate_obj = candidates[i]
            
            formatted_results.append({
                'blockchain_id': candidate_id,
                'name': name,
                'vote_count': vote_count,
                'user_id': candidate_obj.user.id if candidate_obj else None,
                'email': candidate_obj.user.email if candidate_obj else None,
                'manifesto': candidate_obj.manifesto if candidate_obj else None,
                'election_type': election.get_election_type_display(),
                'candidate_id': candidate_obj.id if candidate_obj else None,
                'election_id': election.id
            })
        
        print(f"✅ Returning {len(formatted_results)} blockchain results")
        
        return Response({
            'election_id': election.id,
            'election_title': election.title,
            'election_type': election.get_election_type_display(),
            'results': formatted_results,
            'contract_address': contract_address,
            'total_votes': blockchain_results['total_votes'],
            'source': 'blockchain',
            'success': True
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"❌ Get results failed: {e}")
        import traceback
        traceback.print_exc()
        
        return Response({
            'error': str(e),
            'results': [],
            'total_votes': 0,
            'source': 'error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ============== AUTHENTICATION VIEWS ==============

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register(request):
    """User registration - UPDATED WITH ELECTION SELECTION"""
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        with transaction.atomic():
            user = serializer.save()
            
            if user.is_candidate:
                try:
                    assigned_address = auto_assign_wallet_address(user)
                    if assigned_address:
                        print(f"✅ Auto-assigned wallet to new candidate {user.username}: {assigned_address}")
                except Exception as e:
                    print(f"❌ Wallet assignment failed for {user.username}: {e}")
            
            token, created = Token.objects.get_or_create(user=user)
            
            return Response({
                'user': UserSerializer(user).data,
                'token': token.key,
                'user_id': user.id,
                'email': user.email,
                'selected_election': user.selected_election.title if user.selected_election else None
            }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login(request):
    """User login"""
    email = request.data.get('email')
    username = request.data.get('username')
    password = request.data.get('password')
    
    user = None
    if email and password:
        try:
            user_obj = User.objects.get(email=email)
            user = authenticate(username=user_obj.username, password=password)
        except User.DoesNotExist:
            pass
    elif username and password:
        user = authenticate(username=username, password=password)
    
    if user:
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key,
            'user_id': user.id,
            'email': user.email
        })
    
    return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout(request):
    """User logout"""
    try:
        token = Token.objects.get(user=request.user)
        token.delete()
        return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)
    except Token.DoesNotExist:
        return Response({'error': 'Token not found'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def verify_auth(request):
    """Verify authentication"""
    return Response({
        'user': UserSerializer(request.user).data,
        'user_id': request.user.id,
        'email': request.user.email,
        'authenticated': True
    }, status=status.HTTP_200_OK)

# ============== USER MANAGEMENT ==============

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_pending_users(request):
    """Get pending users for admin approval with election info"""
    if not request.user.is_admin:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    pending_users = User.objects.filter(approved=False, is_admin=False).select_related('selected_election')
    return Response({
        'pending_users': UserSerializer(pending_users, many=True).data
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_approved_candidates(request):
    """Get candidates for user's selected election"""
    try:
        election_id = request.GET.get('election_id')
        
        if election_id:
            candidates = Candidate.objects.filter(
                election_id=election_id,
                user__approved=True
            ).select_related('user', 'election').order_by('id')
        elif request.user.selected_election:
            candidates = Candidate.objects.filter(
                election=request.user.selected_election,
                user__approved=True
            ).select_related('user', 'election').order_by('id')
        else:
            candidates = Candidate.objects.none()
        
        candidates_data = []
        for i, candidate in enumerate(candidates):
            candidates_data.append({
                'id': candidate.user.id,
                'database_id': candidate.user.id,
                'blockchain_id': i + 1,
                'username': candidate.user.username,
                'email': candidate.user.email,
                'wallet_address': candidate.wallet_address,
                'election_id': candidate.election.id,
                'election_title': candidate.election.title,
                'election_type': candidate.election.get_election_type_display(),
                'manifesto': candidate.manifesto,
                'date_joined': candidate.user.date_joined
            })
        
        return Response({
            'candidates': candidates_data,
            'count': len(candidates_data),
            'election': request.user.selected_election.title if request.user.selected_election else None
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"❌ Get candidates failed: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def approve_user(request, user_id):
    """Approve user - FIXED VERSION - NO BLOCKCHAIN SETUP DURING APPROVAL"""
    if not request.user.is_admin:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        with transaction.atomic():
            user = User.objects.get(id=user_id)
            
            assign_to_election_id = request.data.get('election_id')
            
            if assign_to_election_id:
                try:
                    election = Election.objects.get(id=assign_to_election_id)
                    user.selected_election = election
                except Election.DoesNotExist:
                    return Response({'error': 'Invalid election ID'}, status=status.HTTP_400_BAD_REQUEST)
            
            user.approved = True
            user.save()
            
            print(f"✅ User approved: {user.username} (ID: {user.id})")
            if user.selected_election:
                print(f"   Assigned to election: {user.selected_election.title}")
            
            wallet_assigned = False
            if user.is_candidate and not user.wallet_address:
                try:
                    assigned_address = auto_assign_wallet_address(user)
                    if assigned_address:
                        wallet_assigned = True
                        print(f"✅ Auto-assigned wallet to approved candidate {user.username}: {assigned_address}")
                except Exception as e:
                    print(f"⚠️ Could not auto-assign wallet during approval: {e}")
            
            # CREATE CANDIDATE DATABASE ENTRY ONLY - NO BLOCKCHAIN SETUP
            if user.is_candidate and user.wallet_address and user.selected_election:
                try:
                    candidate, created = Candidate.objects.get_or_create(
                        election=user.selected_election,
                        user=user,
                        defaults={
                            'name': user.username or user.email,
                            'wallet_address': user.wallet_address,
                        }
                    )
                    
                    if created:
                        print(f"📝 Created candidate database entry for {user.username}")
                    else:
                        print(f"📝 Candidate entry already exists for {user.username}")
                    
                    # DON'T DO BLOCKCHAIN SETUP HERE - IT CAUSES ERRORS
                    print(f"ℹ️ Blockchain setup will happen automatically when voting starts")
                    
                except Exception as candidate_error:
                    print(f"⚠️ Failed to create candidate entry: {candidate_error}")
            
            return Response({
                'message': 'User approved successfully',
                'user': UserSerializer(user).data,
                'details': {
                    'approved': user.approved,
                    'election_assigned': user.selected_election.title if user.selected_election else None,
                    'wallet_assigned': wallet_assigned or bool(user.wallet_address),
                    'blockchain_setup': 'Will be done during voting',
                    'is_candidate': user.is_candidate,
                    'ready_to_vote': user.approved and user.wallet_address,
                    'wallet_address': user.wallet_address
                }
            }, status=status.HTTP_200_OK)
            
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"❌ Approval failed: {e}")
        import traceback
        traceback.print_exc()
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def reject_user(request, user_id):
    """Reject user"""
    if not request.user.is_admin:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user = User.objects.get(id=user_id)
        user.delete()
        return Response({
            'message': 'User rejected and removed successfully'
        }, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

# ============== WALLET MANAGEMENT ==============

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_available_accounts(request):
    """Get truly available Ganache accounts"""
    try:
        eth_handler = EthereumHandler()
        if not eth_handler.is_connected():
            return Response({
                'error': 'Ganache not connected',
                'available_accounts': [],
                'total_accounts': 0
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        all_accounts = eth_handler.get_accounts()
        
        used_addresses = set(
            User.objects.exclude(wallet_address__isnull=True)
                       .exclude(wallet_address='')
                       .values_list('wallet_address', flat=True)
        )
        
        available_accounts = [
            account for account in all_accounts 
            if account not in used_addresses
        ]
        
        return Response({
            'available_accounts': available_accounts,
            'total_accounts': len(all_accounts),
            'used_accounts': len(used_addresses),
            'available_count': len(available_accounts)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def connect_wallet(request):
    """Connect wallet with collision prevention"""
    try:
        wallet_address = request.data.get('wallet_address')
        if not wallet_address:
            return Response({'error': 'Wallet address required'}, status=status.HTTP_400_BAD_REQUEST)
        
        existing_user = User.objects.filter(wallet_address=wallet_address).exclude(id=request.user.id).first()
        if existing_user:
            return Response({
                'error': f'Wallet address already in use by {existing_user.username}',
                'collision': True,
                'used_by': existing_user.username
            }, status=status.HTTP_400_BAD_REQUEST)
        
        eth_handler = EthereumHandler()
        if not eth_handler.is_connected():
            return Response({'error': 'Ganache not connected'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        ganache_accounts = eth_handler.get_accounts()
        if wallet_address not in ganache_accounts:
            return Response({
                'error': 'Invalid Ganache address',
                'valid_addresses': len(ganache_accounts)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            request.user.wallet_address = wallet_address
            request.user.save()
        
        return Response({
            'message': 'Wallet connected successfully',
            'wallet_address': wallet_address,
            'user': UserSerializer(request.user).data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_ganache_accounts(request):
    """Get available Ganache accounts"""
    try:
        eth_handler = EthereumHandler()
        if not eth_handler.is_connected():
            return Response({'error': 'Ganache not connected'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        accounts = eth_handler.get_accounts()
        return Response({'accounts': accounts}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def assign_ganache_address(request):
    """Assign next available Ganache address"""
    try:
        user_id = request.data.get('user_id')
        if user_id and request.user.is_admin:
            target_user = User.objects.get(id=user_id)
        else:
            target_user = request.user
            
        if target_user.wallet_address:
            return Response({
                'message': 'Wallet already assigned',
                'wallet_address': target_user.wallet_address
            }, status=status.HTTP_200_OK)
        
        eth_handler = EthereumHandler()
        if not eth_handler.is_connected():
            return Response({'error': 'Ganache not connected'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        with transaction.atomic():
            used_addresses = set(
                User.objects.exclude(wallet_address__isnull=True)
                           .exclude(wallet_address='')
                           .values_list('wallet_address', flat=True)
            )
            
            accounts = eth_handler.get_accounts()
            available_address = None
            
            for account in accounts:
                if account not in used_addresses:
                    if not User.objects.filter(wallet_address=account).exists():
                        available_address = account
                        break
            
            if not available_address:
                return Response({'error': 'No available Ganache accounts'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            target_user.wallet_address = available_address
            target_user.save()
        
        return Response({
            'message': 'Ganache address assigned successfully',
            'wallet_address': available_address
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ============== CONTRACT INFO ==============

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_contract_address(request):
    """Get current deployed contract address"""
    global DEPLOYED_CONTRACT_ADDRESS
    
    contract_address = cache.get('voting_system_contract_simple') or DEPLOYED_CONTRACT_ADDRESS
    
    return Response({
        'contract_address': contract_address,
        'auto_deployed': bool(contract_address)
    }, status=status.HTTP_200_OK)

# ============== ETHEREUM VOTING ==============

# authentication/views.py - FIXED cast_vote function

# authentication/views.py - FIXED cast_vote function

# ADD THIS TO YOUR views.py - Fix Ethereum timeout
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cast_vote(request):
    """Cast vote - FIXED VERSION"""
    if not request.user.is_elector or not request.user.approved:
        return Response({'error': 'Approved elector access required'}, status=status.HTTP_403_FORBIDDEN)
    
    if not request.user.selected_election:
        return Response({'error': 'No election selected. Please contact admin.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        candidate_id = request.data.get('candidate_id')
        if not candidate_id:
            return Response({'error': 'Candidate ID required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not request.user.wallet_address:
            return Response({'error': 'Wallet address not connected'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_election = request.user.selected_election
        
        # Get/create contract
        contract_address = cache.get('voting_system_contract_simple')
        if not contract_address:
            eth_handler = EthereumHandler()
            admin_address = eth_handler.w3.eth.accounts[0]
            contract_address = eth_handler.deploy_contract(admin_address)
            cache.set('voting_system_contract_simple', contract_address, 86400)
        
        eth_handler = EthereumHandler()
        contract = eth_handler.get_contract(contract_address)
        
        # Check if election exists on blockchain, create if not
        try:
            contract.functions.getCandidateCount(user_election.blockchain_id or 999).call()
        except:
            # Election doesn't exist, create it
            admin_address = eth_handler.w3.eth.accounts[0]
            tx_hash, receipt, new_blockchain_id = eth_handler.create_election(
                user_election.title, user_election.description, 0, 0, admin_address
            )
            user_election.blockchain_id = new_blockchain_id
            user_election.save()
            
            # Add candidates
            candidates = Candidate.objects.filter(election=user_election).order_by('id')
            for i, candidate in enumerate(candidates):
                eth_handler.add_candidate(new_blockchain_id, candidate.wallet_address, candidate.name, admin_address)
                candidate.blockchain_id = i + 1
                candidate.save()
        
        # Vote
        tx_hash, receipt = eth_handler.vote(user_election.blockchain_id, int(candidate_id), request.user.wallet_address)
        
        # Record in database
        from .models import Vote
        candidate = Candidate.objects.filter(
            election=user_election,
            blockchain_id=int(candidate_id)
        ).first()
        
        if candidate:
            Vote.objects.create(
                election=user_election,
                candidate=candidate,
                voter=request.user,
                transaction_hash=tx_hash,
                status='approved'
            )
        
        return Response({
            'message': 'Vote cast successfully!',
            'tx_hash': tx_hash,
            'user_has_voted': True
        })
        
    except Exception as e:
        return Response({'error': f'Vote failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    """Cast vote - WORKING VERSION"""
    if not request.user.is_elector or not request.user.approved:
        return Response({'error': 'Approved elector access required'}, status=status.HTTP_403_FORBIDDEN)
    
    if not request.user.selected_election:
        return Response({'error': 'No election selected. Please contact admin.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        candidate_id = request.data.get('candidate_id')
        if not candidate_id:
            return Response({'error': 'Candidate ID required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not request.user.wallet_address:
            return Response({'error': 'Wallet address not connected'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_election = request.user.selected_election
        
        # Get/create contract
        contract_address = cache.get('voting_system_contract_simple')
        if not contract_address:
            eth_handler = EthereumHandler()
            admin_address = eth_handler.w3.eth.accounts[0]
            contract_address = eth_handler.deploy_contract(admin_address)
            cache.set('voting_system_contract_simple', contract_address, 86400)
        
        eth_handler = EthereumHandler()
        contract = eth_handler.get_contract(contract_address)
        
        # Create election on blockchain if it doesn't exist
        if not user_election.blockchain_id:
            admin_address = eth_handler.w3.eth.accounts[0]
            tx_hash, receipt, blockchain_election_id = eth_handler.create_election(
                user_election.title,
                user_election.description,
                0, 0, admin_address
            )
            user_election.blockchain_id = blockchain_election_id
            user_election.save()
            
            # Add candidates
            candidates = Candidate.objects.filter(election=user_election).order_by('id')
            for i, candidate in enumerate(candidates):
                tx_hash, receipt, candidate_blockchain_id = eth_handler.add_candidate(
                    blockchain_election_id,
                    candidate.wallet_address,
                    candidate.name,
                    admin_address
                )
                candidate.blockchain_id = i + 1
                candidate.save()
        
        # Now vote
        tx_hash, receipt = eth_handler.vote(user_election.blockchain_id, int(candidate_id), request.user.wallet_address)
        
        # Record in database
        from .models import Vote
        candidate = Candidate.objects.filter(
            election=user_election,
            blockchain_id=int(candidate_id)
        ).first()
        
        if candidate:
            Vote.objects.create(
                election=user_election,
                candidate=candidate,
                voter=request.user,
                transaction_hash=tx_hash,
                status='approved'
            )
        
        return Response({
            'message': 'Vote cast successfully!',
            'tx_hash': tx_hash,
            'user_has_voted': True
        })
        
    except Exception as e:
        return Response({'error': f'Vote failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    """Cast vote and ACTUALLY record it properly"""
    if not request.user.is_elector or not request.user.approved:
        return Response({'error': 'Approved elector access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        candidate_id = request.data.get('candidate_id')
        user_election = request.user.selected_election
        
        # Setup blockchain if needed
        ensure_contract_and_election_exist(user_election.id)
        user_election.refresh_from_db()
        
        # Vote on blockchain
        eth_handler = EthereumHandler()
        contract_address = cache.get('voting_system_contract_simple')
        eth_handler.get_contract(contract_address)
        
        tx_hash, receipt = eth_handler.vote(user_election.blockchain_id, int(candidate_id), request.user.wallet_address)
        
        # CRITICAL: Record in database so results show up
        from .models import Vote
        candidate = Candidate.objects.filter(election=user_election).order_by('id')[int(candidate_id) - 1]
        
        Vote.objects.create(
            election=user_election,
            candidate=candidate,
            voter=request.user,
            transaction_hash=tx_hash,
            status='approved'
        )
        
        print(f"✅ Vote recorded: {request.user.username} -> {candidate.name}")
        
        return Response({
            'message': 'Vote cast successfully!',
            'tx_hash': tx_hash,
            'user_has_voted': True
        })
        
    except Exception as e:
        return Response({'error': f'Vote failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    """Cast vote - FIXED VERSION WITH PROPER DATABASE RECORDING"""
    if not request.user.is_elector or not request.user.approved:
        return Response({'error': 'Approved elector access required'}, status=status.HTTP_403_FORBIDDEN)
    
    if not request.user.selected_election:
        return Response({'error': 'No election selected. Please contact admin.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        candidate_id = request.data.get('candidate_id')
        if not candidate_id:
            return Response({'error': 'Candidate ID required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not request.user.wallet_address:
            return Response({'error': 'Wallet address not connected'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_election = request.user.selected_election
        
        print(f"=== VOTE CASTING DEBUG ===")
        print(f"User: {request.user.username}")
        print(f"Election: {user_election.title} (ID: {user_election.id})")
        print(f"Candidate Blockchain ID: {candidate_id}")
        print(f"Voter Wallet: {request.user.wallet_address}")
        
        # Check if user already voted in DATABASE first
        from .models import Vote
        existing_vote = Vote.objects.filter(
            election=user_election,
            voter=request.user
        ).first()
        
        if existing_vote:
            print(f"❌ User already voted in database")
            return Response({
                'error': 'You have already voted in this election',
                'user_has_voted': True
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure blockchain setup
        if not ensure_contract_and_election_exist(user_election.id):
            return Response({'error': 'Failed to setup blockchain election'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        user_election.refresh_from_db()
        
        eth_handler = EthereumHandler()
        if not eth_handler.is_connected():
            return Response({'error': 'Blockchain connection failed'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        contract_address = cache.get('voting_system_contract_simple')
        eth_handler.get_contract(contract_address)
        
        blockchain_election_id = user_election.blockchain_id
        
        # Check blockchain vote status
        has_voted = eth_handler.has_user_voted(blockchain_election_id, request.user.wallet_address)
        if has_voted:
            return Response({
                'error': 'You have already voted in this election',
                'user_has_voted': True
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate candidate exists
        candidate_count = eth_handler.contract.functions.getCandidateCount(blockchain_election_id).call()
        if int(candidate_id) > candidate_count or int(candidate_id) < 1:
            return Response({
                'error': f'Invalid candidate ID. Must be between 1 and {candidate_count}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Cast vote on blockchain
        print(f"🗳️ Casting blockchain vote...")
        tx_hash, receipt = eth_handler.vote(blockchain_election_id, int(candidate_id), request.user.wallet_address)
        
        print(f"✅ Blockchain vote successful!")
        print(f"TX Hash: {tx_hash}")
        
        # CRITICAL FIX: Record vote in database PROPERLY
        print(f"📝 Recording vote in database...")
        
        try:
            # Find the correct candidate by blockchain_id
            candidate = Candidate.objects.filter(
                election=user_election,
                blockchain_id=int(candidate_id)
            ).first()
            
            if not candidate:
                print(f"⚠️ No candidate found with blockchain_id={candidate_id}, trying to fix...")
                
                # Try to find by position (fallback)
                candidates = Candidate.objects.filter(election=user_election).order_by('id')
                if int(candidate_id) <= len(candidates):
                    candidate = candidates[int(candidate_id) - 1]  # blockchain IDs are 1-indexed
                    # Update the blockchain_id for future reference
                    candidate.blockchain_id = int(candidate_id)
                    candidate.save()
                    print(f"🔧 Fixed candidate mapping: {candidate.name} -> blockchain_id {candidate_id}")
                else:
                    print(f"❌ Could not find candidate at position {candidate_id}")
                    
            if candidate:
                # Create the vote record
                vote_record = Vote.objects.create(
                    election=user_election,
                    candidate=candidate,
                    voter=request.user,
                    transaction_hash=tx_hash,
                    status='approved'
                )
                print(f"✅ Vote recorded in database!")
                print(f"   Vote ID: {vote_record.id}")
                print(f"   Voter: {vote_record.voter.username}")
                print(f"   Candidate: {vote_record.candidate.name}")
                print(f"   Election: {vote_record.election.title}")
                print(f"   TX Hash: {vote_record.transaction_hash}")
            else:
                print(f"❌ Could not create database vote record - candidate not found")
                
        except Exception as db_error:
            print(f"❌ Database vote recording failed: {db_error}")
            import traceback
            traceback.print_exc()
            # Don't fail the whole vote, blockchain vote was successful
        
        return Response({
            'message': 'Vote cast successfully!',
            'tx_hash': tx_hash,
            'candidate_id': candidate_id,
            'election_title': user_election.title,
            'user_has_voted': True,
            'contract_address': contract_address,
            'blockchain_election_id': blockchain_election_id
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"❌ Voting failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({
            'error': f'Vote failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    """Cast vote - FIXED VERSION WITH PROPER DATABASE RECORDING"""
    if not request.user.is_elector or not request.user.approved:
        return Response({'error': 'Approved elector access required'}, status=status.HTTP_403_FORBIDDEN)
    
    if not request.user.selected_election:
        return Response({'error': 'No election selected. Please contact admin.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        candidate_id = request.data.get('candidate_id')
        if not candidate_id:
            return Response({'error': 'Candidate ID required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not request.user.wallet_address:
            return Response({'error': 'Wallet address not connected'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_election = request.user.selected_election
        
        print(f"=== VOTE CASTING DEBUG ===")
        print(f"User: {request.user.username}")
        print(f"Election: {user_election.title} (ID: {user_election.id})")
        print(f"Candidate Blockchain ID: {candidate_id}")
        print(f"Voter Wallet: {request.user.wallet_address}")
        
        # Check if user already voted in DATABASE first
        from .models import Vote
        existing_vote = Vote.objects.filter(
            election=user_election,
            voter=request.user
        ).first()
        
        if existing_vote:
            print(f"❌ User already voted in database")
            return Response({
                'error': 'You have already voted in this election',
                'user_has_voted': True
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure blockchain setup
        if not ensure_contract_and_election_exist(user_election.id):
            return Response({'error': 'Failed to setup blockchain election'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        user_election.refresh_from_db()
        
        eth_handler = EthereumHandler()
        if not eth_handler.is_connected():
            return Response({'error': 'Blockchain connection failed'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        contract_address = cache.get('voting_system_contract_simple')
        eth_handler.get_contract(contract_address)
        
        blockchain_election_id = user_election.blockchain_id
        
        # Check blockchain vote status
        has_voted = eth_handler.has_user_voted(blockchain_election_id, request.user.wallet_address)
        if has_voted:
            return Response({
                'error': 'You have already voted in this election',
                'user_has_voted': True
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate candidate exists
        candidate_count = eth_handler.contract.functions.getCandidateCount(blockchain_election_id).call()
        if int(candidate_id) > candidate_count or int(candidate_id) < 1:
            return Response({
                'error': f'Invalid candidate ID. Must be between 1 and {candidate_count}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Cast vote on blockchain
        print(f"🗳️ Casting blockchain vote...")
        tx_hash, receipt = eth_handler.vote(blockchain_election_id, int(candidate_id), request.user.wallet_address)
        
        print(f"✅ Blockchain vote successful!")
        print(f"TX Hash: {tx_hash}")
        
        # CRITICAL FIX: Record vote in database PROPERLY
        print(f"📝 Recording vote in database...")
        
        try:
            # Find the correct candidate by blockchain_id
            candidate = Candidate.objects.filter(
                election=user_election,
                blockchain_id=int(candidate_id)
            ).first()
            
            if not candidate:
                print(f"⚠️ No candidate found with blockchain_id={candidate_id}, trying to fix...")
                
                # Try to find by position (fallback)
                candidates = Candidate.objects.filter(election=user_election).order_by('id')
                if int(candidate_id) <= len(candidates):
                    candidate = candidates[int(candidate_id) - 1]  # blockchain IDs are 1-indexed
                    # Update the blockchain_id for future reference
                    candidate.blockchain_id = int(candidate_id)
                    candidate.save()
                    print(f"🔧 Fixed candidate mapping: {candidate.name} -> blockchain_id {candidate_id}")
                else:
                    print(f"❌ Could not find candidate at position {candidate_id}")
                    
            if candidate:
                # Create the vote record
                vote_record = Vote.objects.create(
                    election=user_election,
                    candidate=candidate,
                    voter=request.user,
                    transaction_hash=tx_hash,
                    status='approved'
                )
                print(f"✅ Vote recorded in database!")
                print(f"   Vote ID: {vote_record.id}")
                print(f"   Voter: {vote_record.voter.username}")
                print(f"   Candidate: {vote_record.candidate.name}")
                print(f"   Election: {vote_record.election.title}")
                print(f"   TX Hash: {vote_record.transaction_hash}")
            else:
                print(f"❌ Could not create database vote record - candidate not found")
                
        except Exception as db_error:
            print(f"❌ Database vote recording failed: {db_error}")
            import traceback
            traceback.print_exc()
            # Don't fail the whole vote, blockchain vote was successful
        
        return Response({
            'message': 'Vote cast successfully!',
            'tx_hash': tx_hash,
            'candidate_id': candidate_id,
            'election_title': user_election.title,
            'user_has_voted': True,
            'contract_address': contract_address,
            'blockchain_election_id': blockchain_election_id
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"❌ Voting failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({
            'error': f'Vote failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    """Cast vote within user's selected election - WITH FULL DEBUGGING"""
    if not request.user.is_elector or not request.user.approved:
        return Response({'error': 'Approved elector access required'}, status=status.HTTP_403_FORBIDDEN)
    
    if not request.user.selected_election:
        return Response({'error': 'No election selected. Please contact admin.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        candidate_id = request.data.get('candidate_id')
        if not candidate_id:
            return Response({'error': 'Candidate ID required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not request.user.wallet_address:
            return Response({'error': 'Wallet address not connected'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_election = request.user.selected_election
        
        print(f"=== ETHEREUM VOTING DEBUG ===")
        print(f"User: {request.user.username}")
        print(f"Election: {user_election.title} (DB ID: {user_election.id})")
        print(f"Election Blockchain ID: {user_election.blockchain_id}")
        print(f"Candidate ID: {candidate_id}")
        print(f"Voter Wallet: {request.user.wallet_address}")
        print(f"=============================")
        
        # FORCE RESET - THIS FIXES THE PROBLEM
        user_election.blockchain_id = None
        user_election.save()
        print(f"🔄 Reset election blockchain_id to None")
        
        # Now setup blockchain
        ensure_contract_and_election_exist(user_election.id)
        user_election.refresh_from_db()
        print(f"✅ Election setup complete, blockchain_id: {user_election.blockchain_id}")
        
        eth_handler = EthereumHandler()
        if not eth_handler.is_connected():
            return Response({'error': 'Blockchain connection failed'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        contract_address = cache.get('voting_system_contract_simple')
        eth_handler.get_contract(contract_address)
        print(f"📋 Using contract: {contract_address}")
        
        blockchain_election_id = user_election.blockchain_id
        
        # Check if already voted
        has_voted = eth_handler.has_user_voted(blockchain_election_id, request.user.wallet_address)
        if has_voted:
            return Response({
                'error': 'You have already voted in this election',
                'user_has_voted': True
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate candidate
        candidate_count = eth_handler.contract.functions.getCandidateCount(blockchain_election_id).call()
        print(f"📊 Candidate count on blockchain: {candidate_count}")
        
        if int(candidate_id) > candidate_count or int(candidate_id) < 1:
            return Response({
                'error': f'Invalid candidate ID. Must be between 1 and {candidate_count}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Cast vote on blockchain
        print(f"🗳️ Casting vote on blockchain: Election {blockchain_election_id}, Candidate {candidate_id}")
        tx_hash, receipt = eth_handler.vote(blockchain_election_id, int(candidate_id), request.user.wallet_address)
        
        print(f"✅ BLOCKCHAIN VOTE SUCCESSFUL!")
        print(f"TX Hash: {tx_hash}")
        print(f"Gas Used: {receipt.gasUsed if receipt else 'Unknown'}")
        
        # ENHANCED DATABASE RECORDING WITH FULL DEBUGGING
        print(f"🗳️ Vote successful on blockchain, now recording in database...")
        print(f"Looking for candidate with blockchain_id={candidate_id} in election={user_election.id}")
        
        try:
            # List all candidates for debugging BEFORE trying to find the one we want
            all_candidates = Candidate.objects.filter(election=user_election)
            print(f"📋 Available candidates in election '{user_election.title}':")
            for c in all_candidates:
                print(f"  - {c.name}: DB ID={c.id}, Blockchain ID={c.blockchain_id}, Wallet={c.wallet_address}")
            
            # Find candidate by blockchain_id
            candidate = Candidate.objects.get(
                election=user_election,
                blockchain_id=int(candidate_id)
            )
            print(f"✅ Found candidate: {candidate.name} (DB ID: {candidate.id}, Blockchain ID: {candidate.blockchain_id})")
            
            # Create vote record
            from .models import Vote
            vote_record = Vote.objects.create(
                election=user_election,
                candidate=candidate,
                voter=request.user,
                transaction_hash=tx_hash,
                status='approved'
            )
            print(f"✅ Vote recorded in database with ID: {vote_record.id}")
            print(f"📝 Database vote details: Voter={vote_record.voter.username}, Candidate={vote_record.candidate.name}, TX={vote_record.transaction_hash}")
            
        except Candidate.DoesNotExist:
            print(f"❌ ERROR: No candidate found with blockchain_id={candidate_id}")
            print(f"This means the candidate mapping is broken!")
            
            # Try to find ANY candidate with this name or user
            print(f"🔍 Attempting to find candidate by other means...")
            try:
                # Get candidate info from blockchain
                candidate_info = eth_handler.contract.functions.getCandidateInfo(blockchain_election_id, int(candidate_id)).call()
                candidate_name = candidate_info[0]
                candidate_address = candidate_info[1]
                print(f"📋 Blockchain candidate info: name='{candidate_name}', address='{candidate_address}'")
                
                # Try to find by wallet address
                candidate = Candidate.objects.filter(
                    election=user_election,
                    wallet_address=candidate_address
                ).first()
                
                if candidate:
                    print(f"🔧 Found candidate by wallet address: {candidate.name}")
                    # Update their blockchain_id
                    candidate.blockchain_id = int(candidate_id)
                    candidate.save()
                    print(f"✅ Updated candidate blockchain_id to {candidate_id}")
                    
                    # Now create the vote
                    from .models import Vote
                    vote_record = Vote.objects.create(
                        election=user_election,
                        candidate=candidate,
                        voter=request.user,
                        transaction_hash=tx_hash,
                        status='approved'
                    )
                    print(f"✅ Vote recorded in database with ID: {vote_record.id}")
                    
                else:
                    print(f"❌ Could not find candidate with wallet address {candidate_address}")
                    
            except Exception as fix_error:
                print(f"❌ Failed to fix candidate mapping: {fix_error}")
                
        except Exception as db_error:
            print(f"❌ Database error: {db_error}")
            import traceback
            traceback.print_exc()
        
        return Response({
            'message': 'Vote cast successfully!',
            'tx_hash': tx_hash,
            'candidate_id': candidate_id,
            'election_title': user_election.title,
            'user_has_voted': True,
            'contract_address': contract_address,
            'blockchain_election_id': blockchain_election_id
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"❌ Voting failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({
            'error': f'Vote failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    """Cast vote - FIXED VERSION THAT ACTUALLY WORKS"""
    if not request.user.is_elector or not request.user.approved:
        return Response({'error': 'Approved elector access required'}, status=status.HTTP_403_FORBIDDEN)
    
    if not request.user.selected_election:
        return Response({'error': 'No election selected. Please contact admin.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        candidate_id = request.data.get('candidate_id')
        if not candidate_id:
            return Response({'error': 'Candidate ID required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not request.user.wallet_address:
            return Response({'error': 'Wallet address not connected'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_election = request.user.selected_election
        
        # FORCE RESET - THIS FIXES THE PROBLEM
        user_election.blockchain_id = None
        user_election.save()
        
        # Now setup blockchain
        ensure_contract_and_election_exist(user_election.id)
        user_election.refresh_from_db()
        
        eth_handler = EthereumHandler()
        if not eth_handler.is_connected():
            return Response({'error': 'Blockchain connection failed'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        contract_address = cache.get('voting_system_contract_simple')
        eth_handler.get_contract(contract_address)
        
        blockchain_election_id = user_election.blockchain_id
        
        # Check if already voted
        has_voted = eth_handler.has_user_voted(blockchain_election_id, request.user.wallet_address)
        if has_voted:
            return Response({
                'error': 'You have already voted in this election',
                'user_has_voted': True
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate candidate
        candidate_count = eth_handler.contract.functions.getCandidateCount(blockchain_election_id).call()
        if int(candidate_id) > candidate_count or int(candidate_id) < 1:
            return Response({
                'error': f'Invalid candidate ID. Must be between 1 and {candidate_count}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Cast vote
        tx_hash, receipt = eth_handler.vote(blockchain_election_id, int(candidate_id), request.user.wallet_address)
        
        return Response({
            'message': 'Vote cast successfully!',
            'tx_hash': tx_hash,
            'candidate_id': candidate_id,
            'election_title': user_election.title,
            'user_has_voted': True
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Vote failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    """Cast vote - BACK TO BASICS"""
    if not request.user.is_elector or not request.user.approved:
        return Response({'error': 'Approved elector access required'}, status=status.HTTP_403_FORBIDDEN)
    
    if not request.user.selected_election:
        return Response({'error': 'No election selected. Please contact admin.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        candidate_id = request.data.get('candidate_id')
        if not candidate_id:
            return Response({'error': 'Candidate ID required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not request.user.wallet_address:
            return Response({'error': 'Wallet address not connected'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_election = request.user.selected_election
        
        # SIMPLE FIX: Just ensure the election exists on blockchain
        if not ensure_contract_and_election_exist(user_election.id):
            return Response({'error': 'Failed to setup blockchain election'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Refresh election to get updated blockchain_id
        user_election.refresh_from_db()
        
        eth_handler = EthereumHandler()
        if not eth_handler.is_connected():
            return Response({'error': 'Blockchain connection failed'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        contract_address = cache.get('voting_system_contract_simple')
        eth_handler.get_contract(contract_address)
        
        blockchain_election_id = user_election.blockchain_id
        
        # Check if already voted
        has_voted = eth_handler.has_user_voted(blockchain_election_id, request.user.wallet_address)
        if has_voted:
            return Response({
                'error': 'You have already voted in this election',
                'user_has_voted': True
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get candidate count and validate
        candidate_count = eth_handler.contract.functions.getCandidateCount(blockchain_election_id).call()
        if int(candidate_id) > candidate_count or int(candidate_id) < 1:
            return Response({
                'error': f'Invalid candidate ID. Must be between 1 and {candidate_count}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Vote
        tx_hash, receipt = eth_handler.vote(blockchain_election_id, int(candidate_id), request.user.wallet_address)
        
        return Response({
            'message': 'Vote cast successfully!',
            'tx_hash': tx_hash,
            'candidate_id': candidate_id,
            'election_title': user_election.title,
            'user_has_voted': True
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"❌ Voting failed: {str(e)}")
        return Response({
            'error': f'Vote failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# ============== HYPERLEDGER FABRIC INTEGRATION ==============


    """Ensure Django election exists on Hyperledger blockchain"""
    try:
        handler = get_hyperledger_handler()
        if not handler:
            return False
        
        db_election_id = str(user_election.id)
        
        print(f"🔄 Ensuring Hyperledger election exists: {user_election.title} (DB ID: {db_election_id})")
        
        # Get candidates from Django database
        candidates = Candidate.objects.filter(election=user_election).order_by('id')
        candidates_data = [
            {
                'name': candidate.name,
                'wallet_address': candidate.wallet_address,
                'user_id': candidate.user.id
            }
            for candidate in candidates
        ]
        
        # Use the handler method to ensure election and candidates exist
        setup_success = handler.ensure_election_and_candidates_exist(
            db_election_id=db_election_id,
            title=user_election.title,
            description=user_election.description or "Election",
            creator_id=str(request_user.id),
            candidates_data=candidates_data
        )
        
        if setup_success:
            print(f"✅ Hyperledger election setup complete: {len(candidates_data)} candidates")
            return True
        else:
            print(f"❌ Hyperledger election setup failed")
            return False
            
    except Exception as e:
        print(f"❌ Hyperledger election setup error: {e}")
        return False

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def hyperledger_create_election(request):
    """Create election using Hyperledger handler - ADMIN ONLY"""
    if not request.user.is_admin:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    if not HYPERLEDGER_AVAILABLE:
        return Response({'error': 'Hyperledger not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    try:
        handler = get_hyperledger_handler()
        if not handler:
            return Response({'error': 'Hyperledger not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Get data from request
        title = request.data.get('title')
        description = request.data.get('description')
        db_election_id = request.data.get('db_election_id')  # Django election ID
        start_time = int(request.data.get('start_time', 0))
        end_time = int(request.data.get('end_time', 0))
        creator_id = str(request.user.id)
        
        if not title or not db_election_id:
            return Response({'error': 'Title and db_election_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create election on Hyperledger
        result = handler.create_election(
            title=title, 
            description=description, 
            start_time=start_time, 
            end_time=end_time, 
            creator_id=creator_id,
            db_election_id=str(db_election_id)
        )
        
        return Response({
            'success': True,
            'hyperledger_election_id': result.get('electionId'),
            'db_election_id': result.get('dbElectionId'),
            'transaction_id': result.get('transactionId'),
            'message': f'Election "{title}" created on Hyperledger Fabric'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Hyperledger election creation failed: {e}")
        return Response({
            'error': f'Hyperledger election creation failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def hyperledger_add_candidate(request):
    """Add candidate to Hyperledger election - ADMIN ONLY"""
    if not request.user.is_admin:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    if not HYPERLEDGER_AVAILABLE:
        return Response({'error': 'Hyperledger not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    try:
        handler = get_hyperledger_handler()
        if not handler:
            return Response({'error': 'Hyperledger not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        election_id = request.data.get('election_id')  # Django election ID
        candidate_id = request.data.get('candidate_id')
        name = request.data.get('name')
        caller_id = str(request.user.id)
        
        if not all([election_id, candidate_id, name]):
            return Response({'error': 'election_id, candidate_id, and name required'}, status=status.HTTP_400_BAD_REQUEST)
        
        result = handler.add_candidate(str(election_id), str(candidate_id), name, caller_id)
        
        return Response({
            'success': True,
            'candidate_id': candidate_id,
            'transaction_id': result.get('transactionId'),
            'message': f'Candidate "{name}" added to Hyperledger election {election_id}'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Hyperledger candidate addition failed: {e}")
        return Response({
            'error': f'Failed to add candidate to Hyperledger: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# authentication/views.py - COMPLETE hyperledger_cast_vote function

# authentication/views.py - FIXED hyperledger_cast_vote with proper timeout handling

# authentication/views.py - FIXED hyperledger_election_results function
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def hyperledger_cast_vote(request):
    """Cast vote using Hyperledger - DEBUG VERSION with state verification"""
    if not request.user.is_elector or not request.user.approved:
        return Response({'error': 'Approved elector access required'}, status=status.HTTP_403_FORBIDDEN)
    
    if not HYPERLEDGER_AVAILABLE:
        return Response({'error': 'Hyperledger not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    try:
        handler = get_hyperledger_handler()
        if not handler:
            return Response({'error': 'Hyperledger handler not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        if not request.user.selected_election:
            return Response({'error': 'No election assigned'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_election = request.user.selected_election
        candidate_id = request.data.get('candidate_id')
        voter_id = str(request.user.id)
        election_id = str(user_election.id)
        
        print(f"=== SIMPLE HYPERLEDGER VOTING ===")
        print(f"User: {request.user.username}")
        print(f"Election: {user_election.title} (ID: {election_id})")
        print(f"Candidate: {candidate_id}")
        
        # Check if already voted in database first
        from .models import Vote
        existing_vote = Vote.objects.filter(
            election=user_election,
            voter=request.user
        ).first()
        
        if existing_vote:
            return Response({
                'error': 'You have already voted in this election',
                'election_title': user_election.title
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # SIMPLE APPROACH - exactly like your Ethereum
        print(f"Creating election...")
        
        # 1. Create election (ignore if exists)
        try:
            handler._invoke_chaincode('CreateElection', [
                election_id, 
                user_election.title, 
                user_election.description or "Election", 
                "0", 
                "999999999", 
                voter_id
            ])
            print(f"Election created or already exists")
        except Exception as e:
            if "already exists" not in str(e).lower():
                print(f"Election creation failed: {e}")
        
        # 2. Add candidates (ignore if exist)
        candidates = Candidate.objects.filter(election=user_election).order_by('id')
        print(f"DEBUG: Found {len(candidates)} candidates in database")
        for i, candidate in enumerate(candidates, 1):
            print(f"DEBUG: Database candidate {candidate.id}: {candidate.name} -> will be chaincode candidate {i}")
            try:
                handler._invoke_chaincode('AddCandidate', [
                    election_id, 
                    str(i), 
                    candidate.name, 
                    voter_id
                ])
                print(f"Added candidate {i}: {candidate.name}")
            except Exception as e:
                print(f"Candidate add: {e}")
        
        # 3. Wait for candidates to be committed
        print(f"Waiting for candidates to be committed to ledger...")
        import time
        time.sleep(5)
        
        # 4. DEBUG: Check actual chaincode state before voting
        print(f"Checking chaincode state before voting...")
        try:
            check_result = handler._query_chaincode('GetResults', [election_id])
            print(f"Current chaincode state: {check_result}")
            
            if check_result.get('data'):
                data = check_result.get('data')
                if isinstance(data, dict):
                    chaincode_candidates = data.get('candidates', [])
                    print(f"Candidates found in chaincode: {chaincode_candidates}")
                elif isinstance(data, str):
                    try:
                        parsed_data = json.loads(data)
                        chaincode_candidates = parsed_data.get('candidates', [])
                        print(f"Candidates found in chaincode (parsed): {chaincode_candidates}")
                    except:
                        print(f"Could not parse chaincode response: {data}")
        except Exception as e:
            print(f"Failed to check chaincode state: {e}")
        
        # 5. Show candidate mapping
        print(f"Trying to vote for candidate ID: {candidate_id}")
        print(f"Available candidates: {[c.id for c in candidates]}")
        print(f"Candidates mapping: {[(i+1, c.name, c.id) for i, c in enumerate(candidates)]}")
        
        # 6. Map Django candidate ID to chaincode candidate ID
        chaincode_candidate_id = None
        for i, candidate in enumerate(candidates, 1):
            if str(candidate.id) == str(candidate_id):
                chaincode_candidate_id = str(i)
                print(f"MAPPING: Django candidate {candidate_id} -> Chaincode candidate {chaincode_candidate_id}")
                break
        
        if not chaincode_candidate_id:
            return Response({
                'error': f'Invalid candidate ID: {candidate_id}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 7. Cast vote using the correct chaincode candidate ID
        print(f"Casting vote for chaincode candidate ID: {chaincode_candidate_id}")
        timestamp = str(int(time.time()))
        
        # DEBUG: Show exact parameters being sent to CastVote
        vote_params = [election_id, chaincode_candidate_id, voter_id, timestamp]
        print(f"CastVote parameters: {vote_params}")
        
        result = handler._invoke_chaincode('CastVote', vote_params)
        
        print(f"Vote cast successfully: {result}")
        
        # 8. Record in database (just like Ethereum)
        django_candidate = None
        for candidate in candidates:
            if str(candidate.id) == str(candidate_id):
                django_candidate = candidate
                break
        
        if django_candidate:
            vote_record = Vote.objects.create(
                election=user_election,
                candidate=django_candidate,
                voter=request.user,
                transaction_hash=f"hlf-{result.get('transactionId', 'unknown')}",
                status='approved'
            )
            print(f"Vote recorded: {request.user.username} -> {django_candidate.name}")
        
        return Response({
            'success': True,
            'message': 'Vote cast successfully on Hyperledger!',
            'transaction_id': result.get('transactionId'),
            'election_title': user_election.title,
            'candidate_name': django_candidate.name if django_candidate else 'Unknown'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        print(f"Voting failed: {e}")
        import traceback
        traceback.print_exc()
        return Response({
            'error': f'Voting failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    """Cast vote using Hyperledger - FIXED VERSION with proper candidate mapping"""
    if not request.user.is_elector or not request.user.approved:
        return Response({'error': 'Approved elector access required'}, status=status.HTTP_403_FORBIDDEN)
    
    if not HYPERLEDGER_AVAILABLE:
        return Response({'error': 'Hyperledger not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    try:
        handler = get_hyperledger_handler()
        if not handler:
            return Response({'error': 'Hyperledger handler not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        if not request.user.selected_election:
            return Response({'error': 'No election assigned'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_election = request.user.selected_election
        candidate_id = request.data.get('candidate_id')
        voter_id = str(request.user.id)
        election_id = str(user_election.id)
        
        print(f"=== SIMPLE HYPERLEDGER VOTING ===")
        print(f"User: {request.user.username}")
        print(f"Election: {user_election.title} (ID: {election_id})")
        print(f"Candidate: {candidate_id}")
        
        # Check if already voted in database first
        from .models import Vote
        existing_vote = Vote.objects.filter(
            election=user_election,
            voter=request.user
        ).first()
        
        if existing_vote:
            return Response({
                'error': 'You have already voted in this election',
                'election_title': user_election.title
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # SIMPLE APPROACH - exactly like your Ethereum
        print(f"Creating election...")
        
        # 1. Create election (ignore if exists)
        try:
            handler._invoke_chaincode('CreateElection', [
                election_id, 
                user_election.title, 
                user_election.description or "Election", 
                "0", 
                "999999999", 
                voter_id
            ])
            print(f"Election created or already exists")
        except Exception as e:
            if "already exists" not in str(e).lower():
                print(f"Election creation failed: {e}")
        
        # 2. Add candidates (ignore if exist)
        candidates = Candidate.objects.filter(election=user_election).order_by('id')
        print(f"DEBUG: Found {len(candidates)} candidates in database")
        for i, candidate in enumerate(candidates, 1):
            print(f"DEBUG: Database candidate {candidate.id}: {candidate.name} -> will be chaincode candidate {i}")
            try:
                handler._invoke_chaincode('AddCandidate', [
                    election_id, 
                    str(i), 
                    candidate.name, 
                    voter_id
                ])
                print(f"Added candidate {i}: {candidate.name}")
            except Exception as e:
                print(f"Candidate add: {e}")
        
        # 3. DEBUG: Show candidate mapping
        print(f"Trying to vote for candidate ID: {candidate_id}")
        print(f"Available candidates: {[c.id for c in candidates]}")
        print(f"Candidates mapping: {[(i+1, c.name, c.id) for i, c in enumerate(candidates)]}")
        
        # 4. IMPORTANT: Map Django candidate ID to chaincode candidate ID
        # The chaincode uses sequential IDs (1, 2, 3), but Django uses database IDs
        chaincode_candidate_id = None
        for i, candidate in enumerate(candidates, 1):
            if str(candidate.id) == str(candidate_id):
                chaincode_candidate_id = str(i)
                print(f"MAPPING: Django candidate {candidate_id} -> Chaincode candidate {chaincode_candidate_id}")
                break
        
        if not chaincode_candidate_id:
            return Response({
                'error': f'Invalid candidate ID: {candidate_id}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 5. Cast vote using the correct chaincode candidate ID
        print(f"Casting vote for chaincode candidate ID: {chaincode_candidate_id}")
        import time
        timestamp = str(int(time.time()))
        
        result = handler._invoke_chaincode('CastVote', [
            election_id, 
            chaincode_candidate_id,  # Use mapped ID
            voter_id, 
            timestamp
        ])
        
        print(f"Vote cast successfully: {result}")
        
        # 6. Record in database (just like Ethereum)
        django_candidate = None
        for candidate in candidates:
            if str(candidate.id) == str(candidate_id):
                django_candidate = candidate
                break
        
        if django_candidate:
            vote_record = Vote.objects.create(
                election=user_election,
                candidate=django_candidate,
                voter=request.user,
                transaction_hash=f"hlf-{result.get('transactionId', 'unknown')}",
                status='approved'
            )
            print(f"Vote recorded: {request.user.username} -> {django_candidate.name}")
        
        return Response({
            'success': True,
            'message': 'Vote cast successfully on Hyperledger!',
            'transaction_id': result.get('transactionId'),
            'election_title': user_election.title,
            'candidate_name': django_candidate.name if django_candidate else 'Unknown'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        print(f"Voting failed: {e}")
        import traceback
        traceback.print_exc()
        return Response({
            'error': f'Voting failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def hyperledger_election_results(request, election_id=None):
    """Get election results from Hyperledger"""
    if not HYPERLEDGER_AVAILABLE:
        return Response({'error': 'Hyperledger not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    try:
        handler = get_hyperledger_handler()
        if not handler:
            return Response({'error': 'Hyperledger not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Determine which election to get results for
        if election_id:
            db_election_id = str(election_id)
        else:
            if not request.user.selected_election:
                return Response({
                    'error': 'No election specified',
                    'results': {'candidates': []},
                    'election_id': None
                }, status=status.HTTP_200_OK)
            db_election_id = str(request.user.selected_election.id)
        
        print(f"Getting Hyperledger results for election: {db_election_id}")
        
        # Get results from Hyperledger
        try:
            raw_results = handler.get_election_results(db_election_id)
            
            candidates = raw_results.get('candidates', [])
            total_votes = raw_results.get('totalVotes', 0)
            
            return Response({
                'success': True,
                'results': {
                    'candidates': candidates,
                    'total_votes': total_votes,
                    'election_id': db_election_id
                },
                'election_id': db_election_id
            }, status=status.HTTP_200_OK)
            
        except Exception as handler_error:
            print(f"Hyperledger results error: {handler_error}")
            return Response({
                'success': True,
                'results': {'candidates': [], 'total_votes': 0, 'election_id': db_election_id},
                'election_id': db_election_id,
                'note': 'No results available'
            }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Failed to get Hyperledger results: {e}")
        return Response({
            'error': f'Failed to get results: {str(e)}',
            'results': {'candidates': []},
            'success': False
        }, status=status.HTTP_200_OK)
    """Get election results using Hyperledger handler - COMPLETE FIX"""
    if not HYPERLEDGER_AVAILABLE:
        return Response({'error': 'Hyperledger not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    try:
        handler = get_hyperledger_handler()
        if not handler:
            return Response({'error': 'Hyperledger not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Handle election_id - Use database ID consistently
        if election_id:
            election_id = str(election_id)
        else:
            if not request.user.selected_election:
                return Response({
                    'error': 'No election selected',
                    'results': {'candidates': []},
                    'election_id': None
                }, status=status.HTTP_200_OK)
            election_id = str(request.user.selected_election.id)
        
        print(f"🔍 Getting Hyperledger results for election_id: {election_id}")
        
        # Get results from Hyperledger using the correct function
        try:
            raw_results = handler.get_election_results(election_id)
            print(f"📊 RAW Hyperledger results: {json.dumps(raw_results, indent=2, default=str)}")
            
            # Your handler returns the correct format: {"candidates": [], "totalVotes": 0}
            candidates = raw_results.get('candidates', [])
            total_votes = raw_results.get('totalVotes', 0)
            
            print(f"🎯 Processed candidates: {len(candidates)} candidates, {total_votes} total votes")
            
            formatted_results = {
                'candidates': candidates,
                'total_votes': total_votes,
                'election_id': election_id
            }
            
            return Response({
                'success': True,
                'results': formatted_results,
                'election_id': election_id
            }, status=status.HTTP_200_OK)
            
        except Exception as handler_error:
            print(f"❌ Hyperledger handler error: {handler_error}")
            
            # Return empty results instead of error
            return Response({
                'success': True,
                'results': {'candidates': [], 'total_votes': 0, 'election_id': election_id},
                'election_id': election_id,
                'note': 'No results available yet'
            }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Failed to get Hyperledger results: {e}")
        print(f"❌ Hyperledger results error: {e}")
        
        return Response({
            'error': f'Failed to get Hyperledger results: {str(e)}',
            'results': {'candidates': []},
            'election_id': election_id if 'election_id' in locals() else None,
            'success': False
        }, status=status.HTTP_200_OK)

    """Check if user voted using Hyperledger handler - COMPLETE FIX"""
    if not HYPERLEDGER_AVAILABLE:
        return Response({
            'has_voted': False,
            'error': 'Hyperledger not available'
        }, status=status.HTTP_200_OK)
    
    try:
        handler = get_hyperledger_handler()
        if not handler:
            return Response({
                'has_voted': False,
                'error': 'Hyperledger not available'
            }, status=status.HTTP_200_OK)
        
        # Get election_id - Use database ID consistently
        election_id = request.GET.get('election_id')
        if not election_id:
            if not request.user.selected_election:
                return Response({
                    'has_voted': False,
                    'error': 'No election selected',
                    'voter_id': str(request.user.id),
                    'election_id': None,
                    'election_title': None
                }, status=status.HTTP_200_OK)
            election_id = str(request.user.selected_election.id)
        
        voter_id = str(request.user.id)
        
        print(f"🔍 Checking Hyperledger vote status: election_id={election_id}, voter_id={voter_id}")
        
        try:
            has_voted = handler.has_user_voted(election_id, voter_id)
            print(f"✅ Hyperledger vote status: {has_voted}")
        except Exception as e:
            print(f"⚠️ Could not check vote status: {e}")
            has_voted = False
        
        return Response({
            'has_voted': has_voted,
            'voter_id': voter_id,
            'election_id': election_id,
            'election_title': request.user.selected_election.title if request.user.selected_election else None
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Failed to check vote status: {e}")
        print(f"❌ Hyperledger vote status error: {e}")
        
        return Response({
            'has_voted': False,
            'error': f'Failed to check vote status: {str(e)}',
            'voter_id': str(request.user.id),
            'election_id': election_id if 'election_id' in locals() else None
        }, status=status.HTTP_200_OK)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def hyperledger_check_vote_status(request):
    """Check if user has voted on Hyperledger"""
    if not HYPERLEDGER_AVAILABLE:
        return Response({
            'has_voted': False,
            'error': 'Hyperledger not available'
        }, status=status.HTTP_200_OK)
    
    try:
        handler = get_hyperledger_handler()
        if not handler:
            return Response({
                'has_voted': False,
                'error': 'Hyperledger handler not available'
            }, status=status.HTTP_200_OK)
        
        # Get election ID
        election_id = request.GET.get('election_id')
        if not election_id:
            if not request.user.selected_election:
                return Response({
                    'has_voted': False,
                    'error': 'No election assigned',
                    'voter_id': str(request.user.id)
                }, status=status.HTTP_200_OK)
            election_id = str(request.user.selected_election.id)
        
        voter_id = str(request.user.id)
        
        try:
            has_voted = handler.has_user_voted(election_id, voter_id)
        except Exception:
            has_voted = False
        
        return Response({
            'has_voted': has_voted,
            'voter_id': voter_id,
            'election_id': election_id,
            'election_title': request.user.selected_election.title if request.user.selected_election else None
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'has_voted': False,
            'error': f'Check failed: {str(e)}',
            'voter_id': str(request.user.id)
        }, status=status.HTTP_200_OK)
# ============== ETHEREUM VOTE STATUS & RESULTS ==============

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_user_vote_status(request):
    """Check if current user has already voted in their selected election"""
    try:
        if not request.user.wallet_address:
            return Response({
                'has_voted': False,
                'can_vote': False,
                'reason': 'No wallet address connected'
            }, status=status.HTTP_200_OK)
        
        if not request.user.selected_election:
            return Response({
                'has_voted': False,
                'can_vote': False,
                'reason': 'No election selected'
            }, status=status.HTTP_200_OK)
        
        user_election = request.user.selected_election
        
        if not user_election.blockchain_id:
            return Response({
                'has_voted': False,
                'can_vote': True,
                'reason': 'Election will be created on blockchain when you vote',
                'election': user_election.title
            }, status=status.HTTP_200_OK)
        
        contract_address = cache.get('voting_system_contract_simple')
        if not contract_address:
            return Response({
                'has_voted': False,
                'can_vote': True,
                'reason': 'Contract will auto-deploy on first vote',
                'election': user_election.title
            }, status=status.HTTP_200_OK)
        
        eth_handler = EthereumHandler()
        if not eth_handler.is_connected():
            return Response({
                'has_voted': False,
                'can_vote': False,
                'reason': 'Ganache not connected'
            }, status=status.HTTP_200_OK)
        
        has_voted = eth_handler.has_user_voted(user_election.blockchain_id, request.user.wallet_address)
        
        return Response({
            'has_voted': has_voted,
            'can_vote': not has_voted and request.user.is_elector and request.user.approved,
            'reason': 'Already voted' if has_voted else 'Can vote',
            'election_id': user_election.id,
            'election_title': user_election.title,
            'wallet_address': request.user.wallet_address
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"❌ Check vote status failed: {e}")
        return Response({
            'has_voted': False,
            'can_vote': False,
            'reason': f'Error: {str(e)}'
        }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_election_results(request):
    """Get election results - CHECK UPDATE CONTRACT FIRST, then fallback to original"""
    try:
        election_id = request.GET.get('election_id')
        
        if election_id:
            try:
                election = Election.objects.get(id=election_id)
            except Election.DoesNotExist:
                return Response({'error': 'Election not found'}, status=status.HTTP_404_NOT_FOUND)
        elif request.user.selected_election:
            election = request.user.selected_election
        else:
            return Response({
                'error': 'No election specified',
                'results': [],
                'total_votes': 0
            }, status=status.HTTP_400_BAD_REQUEST)

        print(f"Getting results for election: {election.title} (ID: {election.id})")

        # PRIORITY 1: Check update contract first
        update_contract_address = cache.get('ethereum_update_contract')
        update_blockchain_id = cache.get(f'update_election_{election.id}')
        
        if update_contract_address and update_blockchain_id:
            try:
                print(f"Checking update contract for results...")
                from blockchain.ethereum_handler_update import EthereumUpdateHandler
                eth_handler = EthereumUpdateHandler()
                
                if eth_handler.is_connected():
                    eth_handler.get_contract(update_contract_address)
                    results = eth_handler.get_election_results(update_blockchain_id)
                    candidates = Candidate.objects.filter(election=election).order_by('id')
                    
                    formatted_results = []
                    for i, (candidate_id, name, vote_count) in enumerate(zip(
                        results['candidate_ids'], 
                        results['names'], 
                        results['vote_counts']
                    )):
                        candidate_obj = candidates[i] if i < len(candidates) else None
                        
                        formatted_results.append({
                            'blockchain_id': candidate_id,
                            'name': name,
                            'vote_count': vote_count,
                            'user_id': candidate_obj.user.id if candidate_obj else None,
                            'email': candidate_obj.user.email if candidate_obj else None,
                            'manifesto': candidate_obj.manifesto if candidate_obj else None,
                            'election_type': election.get_election_type_display()
                        })
                    
                    print(f"Update contract results found: {len(formatted_results)} candidates")
                    
                    return Response({
                        'election_id': election.id,
                        'election_title': election.title,
                        'election_type': election.get_election_type_display(),
                        'results': formatted_results,
                        'contract_address': update_contract_address,
                        'total_votes': results['total_votes'],
                        'source': 'update_contract',
                        'success': True
                    }, status=status.HTTP_200_OK)
                    
            except Exception as e:
                print(f"Update contract results failed: {e}")

        # FALLBACK: Check database votes first
        from .models import Vote
        db_votes = Vote.objects.filter(election=election)
        
        if db_votes.exists():
            print(f"Found {db_votes.count()} database votes, using those")
            
            results = []
            candidates = {}
            
            for vote in db_votes:
                candidate_name = vote.candidate.name
                if candidate_name not in candidates:
                    candidates[candidate_name] = {
                        'blockchain_id': vote.candidate.blockchain_id or 1,
                        'name': candidate_name,
                        'vote_count': 0,
                        'email': vote.candidate.user.email if vote.candidate.user else None,
                        'user_id': vote.candidate.user.id if vote.candidate.user else None,
                        'manifesto': vote.candidate.manifesto if hasattr(vote.candidate, 'manifesto') else None,
                        'election_type': election.get_election_type_display()
                    }
                candidates[candidate_name]['vote_count'] += 1
            
            results = list(candidates.values())
            total_votes = len(db_votes)
            
            print(f"Returning {len(results)} candidates with {total_votes} total votes from database")
            
            return Response({
                'election_id': election.id,
                'election_title': election.title,
                'election_type': election.get_election_type_display(),
                'results': results,
                'total_votes': total_votes,
                'source': 'database',
                'success': True
            }, status=status.HTTP_200_OK)

        # FALLBACK: Try original blockchain contract
        if not election.blockchain_id:
            print(f"Election {election.title} not on blockchain yet")
            return Response({
                'error': f'Election "{election.title}" not yet created on blockchain',
                'election': election.title,
                'results': [],
                'total_votes': 0,
                'source': 'none'
            }, status=status.HTTP_200_OK)
        
        contract_address = cache.get('voting_system_contract_simple')
        if not contract_address:
            print("Contract not found in cache, trying to redeploy...")
            ensure_contract_and_election_exist(election.id)
            contract_address = cache.get('voting_system_contract_simple')
        
        if not contract_address:
            print("Failed to deploy contract")
            return Response({
                'error': 'Failed to deploy voting contract for results',
                'election': election.title,
                'results': [],
                'total_votes': 0,
                'source': 'blockchain_failed'
            }, status=status.HTTP_200_OK)
        
        eth_handler = EthereumHandler()
        if not eth_handler.is_connected():
            print("Ganache not connected")
            return Response({
                'error': 'Ganache connection failed',
                'election': election.title,
                'results': [],
                'total_votes': 0,
                'source': 'ganache_failed'
            }, status=status.HTTP_200_OK)
        
        contract = eth_handler.get_contract(contract_address)
        if not contract:
            print("Failed to load contract")
            return Response({
                'error': 'Failed to load contract',
                'election': election.title,
                'results': [],
                'total_votes': 0,
                'source': 'contract_failed'
            }, status=status.HTTP_200_OK)
        
        # Get blockchain results from original contract
        blockchain_results = eth_handler.get_election_results(election.blockchain_id)
        candidates = Candidate.objects.filter(election=election).order_by('id')
        
        formatted_results = []
        for i, (candidate_id, name, vote_count) in enumerate(zip(
            blockchain_results['candidate_ids'], 
            blockchain_results['names'], 
            blockchain_results['vote_counts']
        )):
            candidate_obj = None
            if i < len(candidates):
                candidate_obj = candidates[i]
            
            formatted_results.append({
                'blockchain_id': candidate_id,
                'name': name,
                'vote_count': vote_count,
                'user_id': candidate_obj.user.id if candidate_obj else None,
                'email': candidate_obj.user.email if candidate_obj else None,
                'manifesto': candidate_obj.manifesto if candidate_obj else None,
                'election_type': election.get_election_type_display()
            })
        
        print(f"Returning {len(formatted_results)} original blockchain results")
        
        return Response({
            'election_id': election.id,
            'election_title': election.title,
            'election_type': election.get_election_type_display(),
            'results': formatted_results,
            'contract_address': contract_address,
            'total_votes': blockchain_results['total_votes'],
            'source': 'original_blockchain',
            'success': True
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Get results failed: {e}")
        import traceback
        traceback.print_exc()
        
        return Response({
            'error': str(e),
            'results': [],
            'total_votes': 0,
            'source': 'error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    """Get election results - FIXED VERSION"""
    try:
        election_id = request.GET.get('election_id')
        
        if election_id:
            try:
                election = Election.objects.get(id=election_id)
            except Election.DoesNotExist:
                return Response({'error': 'Election not found'}, status=status.HTTP_404_NOT_FOUND)
        elif request.user.selected_election:
            election = request.user.selected_election
        else:
            return Response({
                'error': 'No election specified',
                'results': [],
                'total_votes': 0
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not election.blockchain_id:
            return Response({
                'error': f'Election "{election.title}" not yet created on blockchain',
                'election': election.title,
                'results': [],
                'total_votes': 0
            }, status=status.HTTP_200_OK)
        
        # FIX: Auto-deploy contract if missing
        contract_address = cache.get('voting_system_contract_simple')
        if not contract_address:
            print("🔄 Contract not found in cache, trying to redeploy for results...")
            ensure_contract_and_election_exist(election.id)
            contract_address = cache.get('voting_system_contract_simple')
        
        if not contract_address:
            return Response({
                'error': 'Failed to deploy voting contract for results',
                'election': election.title,
                'results': [],
                'total_votes': 0
            }, status=status.HTTP_200_OK)
        
        eth_handler = EthereumHandler()
        if not eth_handler.is_connected():
            return Response({
                'error': 'Ganache connection failed',
                'election': election.title,
                'results': [],
                'total_votes': 0
            }, status=status.HTTP_200_OK)
        
        contract = eth_handler.get_contract(contract_address)
        if not contract:
            return Response({
                'error': 'Failed to load contract',
                'election': election.title,
                'results': [],
                'total_votes': 0
            }, status=status.HTTP_200_OK)
        
        results = eth_handler.get_election_results(election.blockchain_id)
        
        candidates = Candidate.objects.filter(election=election).order_by('id')
        
        formatted_results = []
        for i, (candidate_id, name, vote_count) in enumerate(zip(
            results['candidate_ids'], 
            results['names'], 
            results['vote_counts']
        )):
            candidate_obj = None
            if i < len(candidates):
                candidate_obj = candidates[i]
            
            formatted_results.append({
                'blockchain_id': candidate_id,
                'name': name,
                'vote_count': vote_count,
                'user_id': candidate_obj.user.id if candidate_obj else None,
                'email': candidate_obj.user.email if candidate_obj else None,
                'manifesto': candidate_obj.manifesto if candidate_obj else None,
                'election_type': election.get_election_type_display()
            })
        
        return Response({
            'election_id': election.id,
            'election_title': election.title,
            'election_type': election.get_election_type_display(),
            'results': formatted_results,
            'contract_address': contract_address,
            'total_votes': results['total_votes'],
            'success': True
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"❌ Get results failed: {e}")
        import traceback
        traceback.print_exc()
        
        return Response({
            'error': str(e),
            'results': [],
            'total_votes': 0
        }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_elections(request):
    """Get all elections (admin) or user's election (regular user)"""
    try:
        if request.user.is_admin:
            elections = Election.objects.all().order_by('-created_at')
        else:
            if request.user.selected_election:
                elections = Election.objects.filter(id=request.user.selected_election.id)
            else:
                elections = Election.objects.none()
        
        serializer = ElectionSerializer(elections, many=True)
        
        return Response({
            'elections': serializer.data,
            'count': elections.count()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    """Create new election (admin only)"""
    if not request.user.is_admin:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        data = request.data.copy()
        data['created_by'] = request.user.id
        
        serializer = ElectionSerializer(data=data)
        if serializer.is_valid():
            election = serializer.save()
            
            print(f"✅ Election created: {election.title} (ID: {election.id})")
            
            return Response({
                'message': 'Election created successfully',
                'election': ElectionSerializer(election).data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        print(f"❌ Election creation failed: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# ============== QUICK FIX ENDPOINT ==============

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def refresh_contract_address(request):
    """Manually refresh contract address and setup elections"""
    global DEPLOYED_CONTRACT_ADDRESS  # FIXED: Move to top
    
    if not request.user.is_admin:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        eth_handler = EthereumHandler()
        
        if not eth_handler.is_connected():
            return Response({'error': 'Ganache not connected'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        admin_address = eth_handler.w3.eth.accounts[0]
        contract_address = eth_handler.deploy_contract(admin_address)
        
        cache.set('voting_system_contract_simple', contract_address, 86400)
        DEPLOYED_CONTRACT_ADDRESS = contract_address
        
        print(f"🔄 Contract refreshed: {contract_address}")
        
        # Reset blockchain IDs since this is a fresh contract
        Election.objects.all().update(blockchain_id=None)
        print("🗑️ Reset all blockchain IDs")
        
        active_elections = Election.objects.filter(is_active=True)
        elections_created = 0
        
        for election in active_elections:
            try:
                tx_hash, receipt, blockchain_election_id = eth_handler.create_election(
                    election.title,
                    election.description,
                    0, 0, admin_address
                )
                
                election.blockchain_id = blockchain_election_id
                election.contract_address = contract_address
                election.save()
                
                elections_created += 1
                print(f"🗳️ Created blockchain election: {election.title} (ID: {blockchain_election_id})")
                
                candidates = Candidate.objects.filter(election=election).order_by('id')
                candidates_added = 0
                
                for candidate in candidates:
                    try:
                        tx_hash, receipt, candidate_blockchain_id = eth_handler.add_candidate(
                            blockchain_election_id,
                            candidate.wallet_address,
                            candidate.name,
                            admin_address
                        )
                        candidate.blockchain_id = candidate_blockchain_id
                        candidate.save()
                        candidates_added += 1
                    except Exception as e:
                        print(f"⚠️ Failed to add candidate {candidate.name}: {e}")
                
                print(f"   Added {candidates_added} candidates to {election.title}")
                
            except Exception as e:
                print(f"❌ Failed to create election {election.title}: {e}")
        
        return Response({
            'message': 'Contract and elections refreshed successfully',
            'contract_address': contract_address,
            'elections_created': elections_created,
            'ready_for_voting': True
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"❌ Refresh failed: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def debug_hyperledger_raw(request):
    """Debug endpoint to test Hyperledger connection and raw results"""
    if not HYPERLEDGER_AVAILABLE:
        return Response({'error': 'Hyperledger not available'})
    
    try:
        handler = get_hyperledger_handler()
        if not handler:
            return Response({'error': 'Handler not available'})
        
        # Test with election ID 1
        raw_results = handler.get_election_results("1")
        
        return Response({
            'raw_results': raw_results,
            'type': type(raw_results).__name__,
            'keys': list(raw_results.keys()) if isinstance(raw_results, dict) else 'not_dict'
        })
        
    except Exception as e:
        return Response({'error': str(e), 'traceback': traceback.format_exc()})



@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_ethereum_vote(request):
    """Update Ethereum vote - allow updating to same candidate"""
    if not request.user.is_elector or not request.user.approved:
        return Response({'error': 'Approved elector access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        new_candidate_id = request.data.get('candidate_id')
        if not new_candidate_id or not request.user.wallet_address:
            return Response({'error': 'Missing candidate ID or wallet'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_election = request.user.selected_election
        
        print(f"=== ETHEREUM UPDATE DEBUG ===")
        print(f"User: {request.user.username}")
        print(f"Election: {user_election.title} (ID: {user_election.id})")
        print(f"New Candidate ID: {new_candidate_id}")
        
        # Check for existing vote
        from .models import Vote
        existing_vote = Vote.objects.filter(
            election=user_election,
            voter=request.user
        ).exclude(transaction_hash__startswith='hlf-').first()
        
        if not existing_vote:
            return Response({'error': 'No Ethereum vote found to update'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find new candidate
        candidates = Candidate.objects.filter(election=user_election).order_by('id')
        new_candidate = candidates[int(new_candidate_id) - 1]
        
        # If updating to same candidate, just update timestamp and return success
        if existing_vote.candidate.id == new_candidate.id:
            print(f"User updating to same candidate: {new_candidate.name}")
            with transaction.atomic():
                existing_vote.voted_at = timezone.now()
                existing_vote.save()
            
            return Response({
                'success': True,
                'message': f'Vote confirmed for {new_candidate.name}!',
                'old_candidate': new_candidate.name,
                'new_candidate': new_candidate.name,
                'blockchain': 'ethereum',
                'same_candidate': True
            }, status=status.HTTP_200_OK)
        
        # Different candidate - proceed with blockchain update
        print(f"Updating from {existing_vote.candidate.name} to {new_candidate.name}")
        
        # Auto-deploy/load the update contract
        from blockchain.ethereum_handler_update import EthereumUpdateHandler
        eth_handler = EthereumUpdateHandler()
        
        if not eth_handler.is_connected():
            return Response({'error': 'Blockchain connection failed'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Get or deploy the update contract
        update_contract_address = cache.get('ethereum_update_contract')
        if not update_contract_address:
            print("Deploying update contract...")
            admin_address = eth_handler.get_accounts()[0]
            update_contract_address = eth_handler.deploy_contract(admin_address)
            cache.set('ethereum_update_contract', update_contract_address, 86400)
            print(f"Update contract deployed: {update_contract_address}")
        
        # Load the contract
        contract = eth_handler.get_contract(update_contract_address)
        if not contract:
            return Response({'error': 'Failed to load update contract'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # CREATE ELECTION ON UPDATE CONTRACT
        update_blockchain_id = cache.get(f'update_election_{user_election.id}')
        if not update_blockchain_id:
            print("Creating election on update contract...")
            admin_address = eth_handler.get_accounts()[0]
            
            # Create election on update contract
            tx_hash, receipt, update_blockchain_id = eth_handler.create_election(
                user_election.title,
                user_election.description,
                0, 0, admin_address
            )
            print(f"Election created on update contract: {update_blockchain_id}")
            
            # Add all candidates to update contract
            candidates_list = Candidate.objects.filter(election=user_election).order_by('id')
            for i, candidate in enumerate(candidates_list):
                eth_handler.add_candidate(
                    update_blockchain_id,
                    candidate.wallet_address,
                    candidate.name,
                    admin_address
                )
                print(f"Added candidate {i+1}: {candidate.name}")
            
            cache.set(f'update_election_{user_election.id}', update_blockchain_id, 86400)
        
        # Check if user has voted on update contract, if not cast initial vote
        has_voted = eth_handler.has_user_voted(update_blockchain_id, request.user.wallet_address)
        if not has_voted:
            print("User hasn't voted on update contract yet, casting initial vote...")
            current_candidate_blockchain_id = existing_vote.candidate.blockchain_id or 1
            eth_handler.vote(update_blockchain_id, current_candidate_blockchain_id, request.user.wallet_address)
            print(f"Initial vote cast for candidate {current_candidate_blockchain_id}")
        
        # Now update the vote on blockchain
        print(f"Updating vote to candidate {new_candidate_id}...")
        tx_hash, receipt, old_candidate_id = eth_handler.update_vote(
            update_blockchain_id,
            int(new_candidate_id),
            request.user.wallet_address
        )
        print(f"Vote updated on blockchain: {tx_hash}")
        
        # Update database record
        with transaction.atomic():
            old_candidate_name = existing_vote.candidate.name
            existing_vote.candidate = new_candidate
            existing_vote.transaction_hash = tx_hash
            existing_vote.voted_at = timezone.now()
            existing_vote.save()
            print(f"Database updated: {old_candidate_name} -> {new_candidate.name}")
        
        return Response({
            'success': True,
            'message': f'Vote updated from {old_candidate_name} to {new_candidate.name}!',
            'old_candidate': old_candidate_name,
            'new_candidate': new_candidate.name,
            'tx_hash': tx_hash,
            'blockchain': 'ethereum',
            'same_candidate': False
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Ethereum vote update failed: {e}")
        import traceback
        traceback.print_exc()
        return Response({
            'error': f'Vote update failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    """Update Ethereum vote - BLOCKCHAIN + DATABASE like cast_vote"""
    if not request.user.is_elector or not request.user.approved:
        return Response({'error': 'Approved elector access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        new_candidate_id = request.data.get('candidate_id')
        if not new_candidate_id or not request.user.wallet_address:
            return Response({'error': 'Missing candidate ID or wallet'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_election = request.user.selected_election
        
        # Check for existing vote
        from .models import Vote
        existing_vote = Vote.objects.filter(
            election=user_election,
            voter=request.user
        ).exclude(transaction_hash__startswith='hlf-').first()
        
        if not existing_vote:
            return Response({'error': 'No Ethereum vote found to update'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Auto-deploy/load the update contract
        from blockchain.ethereum_handler_update import EthereumUpdateHandler
        eth_handler = EthereumUpdateHandler()
        
        # Get or deploy the update contract
        update_contract_address = cache.get('ethereum_update_contract')
        if not update_contract_address:
            admin_address = eth_handler.get_accounts()[0]
            update_contract_address = eth_handler.deploy_contract(admin_address)
            cache.set('ethereum_update_contract', update_contract_address, 86400)
        
        eth_handler.get_contract(update_contract_address)
        
        # CREATE ELECTION ON UPDATE CONTRACT (like ensure_contract_and_election_exist does)
        update_blockchain_id = cache.get(f'update_election_{user_election.id}')
        if not update_blockchain_id:
            admin_address = eth_handler.get_accounts()[0]
            
            # Create election on update contract
            tx_hash, receipt, update_blockchain_id = eth_handler.create_election(
                user_election.title,
                user_election.description,
                0, 0, admin_address
            )
            
            # Add all candidates to update contract
            candidates = Candidate.objects.filter(election=user_election).order_by('id')
            for i, candidate in enumerate(candidates):
                eth_handler.add_candidate(
                    update_blockchain_id,
                    candidate.wallet_address,
                    candidate.name,
                    admin_address
                )
            
            cache.set(f'update_election_{user_election.id}', update_blockchain_id, 86400)
        
        # Cast initial vote if user hasn't voted on update contract yet
        has_voted = eth_handler.has_user_voted(update_blockchain_id, request.user.wallet_address)
        if not has_voted:
            current_candidate_blockchain_id = existing_vote.candidate.blockchain_id or 1
            eth_handler.vote(update_blockchain_id, current_candidate_blockchain_id, request.user.wallet_address)
        
        # Now update the vote
        tx_hash, receipt, old_candidate_id = eth_handler.update_vote(
            update_blockchain_id,
            int(new_candidate_id),
            request.user.wallet_address
        )
        
        # Update database
        candidates = Candidate.objects.filter(election=user_election).order_by('id')
        new_candidate = candidates[int(new_candidate_id) - 1]
        
        with transaction.atomic():
            old_candidate_name = existing_vote.candidate.name
            existing_vote.candidate = new_candidate
            existing_vote.transaction_hash = tx_hash
            existing_vote.voted_at = timezone.now()
            existing_vote.save()
        
        return Response({
            'success': True,
            'message': f'Vote updated from {old_candidate_name} to {new_candidate.name}!',
            'old_candidate': old_candidate_name,
            'new_candidate': new_candidate.name,
            'tx_hash': tx_hash,
            'blockchain': 'ethereum'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Ethereum vote update failed: {e}")
        import traceback
        traceback.print_exc()
        return Response({'error': f'Vote update failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def deploy_update_contract(request):
    """Deploy the update contract - Admin only"""
    if not request.user.is_admin:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        print("Deploying Ethereum update contract...")
        
        eth_handler = EthereumUpdateHandler()
        if not eth_handler.is_connected():
            return Response({'error': 'Blockchain connection failed'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Deploy the update contract
        admin_address = eth_handler.get_accounts()[0]
        contract_address = eth_handler.deploy_contract(admin_address)
        
        # Cache the contract address
        cache.set('ethereum_update_contract', contract_address, 86400)  # 24 hours
        
        return Response({
            'message': 'Update contract deployed successfully',
            'contract_address': contract_address,
            'blockchain': 'ethereum'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Update contract deployment failed: {e}")
        return Response({
            'error': f'Deployment failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_ethereum_update_status(request):
    """Check if user can update their Ethereum vote"""
    if not request.user.is_elector or not request.user.approved:
        return Response({'error': 'Approved elector access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user_election = request.user.selected_election
        if not user_election:
            return Response({
                'can_update': False,
                'reason': 'No election selected'
            })
        
        # Check for existing Ethereum vote
        existing_vote = Vote.objects.filter(
            election=user_election,
            voter=request.user,
            transaction_hash__isnull=False
        ).exclude(
            transaction_hash__startswith='hlf-'
        ).first()
        
        if not existing_vote:
            return Response({
                'can_update': False,
                'reason': 'No Ethereum vote found',
                'blockchain': 'ethereum'
            })
        
        # Check if update contract is deployed
        update_contract_address = cache.get('ethereum_update_contract')
        if not update_contract_address:
            return Response({
                'can_update': False,
                'reason': 'Update contract not deployed',
                'action_needed': 'deploy_update_contract',
                'blockchain': 'ethereum'
            })
        
        # Get current vote info
        candidates = Candidate.objects.filter(election=user_election).order_by('id')
        current_candidate = existing_vote.candidate
        
        available_candidates = []
        for i, candidate in enumerate(candidates):
            if candidate.id != current_candidate.id:
                available_candidates.append({
                    'blockchain_id': i + 1,
                    'name': candidate.name,
                    'user_id': candidate.user.id if candidate.user else None
                })
        
        return Response({
            'can_update': True,
            'current_vote': {
                'candidate_name': current_candidate.name,
                'candidate_id': existing_vote.candidate.blockchain_id or 1,
                'tx_hash': existing_vote.transaction_hash
            },
            'available_candidates': available_candidates,
            'blockchain': 'ethereum',
            'update_contract_address': update_contract_address
        })
        
    except Exception as e:
        return Response({
            'can_update': False,
            'reason': f'Error: {str(e)}',
            'blockchain': 'ethereum'
        })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_ethereum_results_updated(request):
    """Get UPDATED Ethereum results after vote changes"""
    try:
        election_id = request.GET.get('election_id')
        
        if election_id:
            try:
                election = Election.objects.get(id=election_id)
            except Election.DoesNotExist:
                return Response({'error': 'Election not found'}, status=status.HTTP_404_NOT_FOUND)
        elif request.user.selected_election:
            election = request.user.selected_election
        else:
            return Response({
                'error': 'No election specified',
                'results': [],
                'total_votes': 0
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get update contract results (these reflect vote changes)
        update_contract_address = cache.get('ethereum_update_contract')
        
        if not update_contract_address or not election.blockchain_id:
            # Fallback to database results
            from .models import Vote
            votes = Vote.objects.filter(
                election=election
            ).exclude(
                transaction_hash__startswith='hlf-'  # Only Ethereum votes
            )
            
            results = []
            candidates = {}
            
            for vote in votes:
                candidate_name = vote.candidate.name
                if candidate_name not in candidates:
                    candidates[candidate_name] = {
                        'blockchain_id': vote.candidate.blockchain_id or 1,
                        'name': candidate_name,
                        'vote_count': 0,
                        'email': vote.candidate.user.email if vote.candidate.user else None
                    }
                candidates[candidate_name]['vote_count'] += 1
            
            results = list(candidates.values())
            total_votes = len(votes)
            
            return Response({
                'election_id': election.id,
                'election_title': election.title,
                'results': results,
                'total_votes': total_votes,
                'source': 'database_ethereum_only',
                'blockchain': 'ethereum'
            })
        
        # Get fresh results from update contract
        eth_handler = EthereumUpdateHandler()
        if not eth_handler.is_connected():
            return Response({'error': 'Blockchain connection failed'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        contract = eth_handler.get_contract(update_contract_address)
        if not contract:
            return Response({'error': 'Failed to load update contract'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        blockchain_results = eth_handler.get_election_results(election.blockchain_id)
        candidates = Candidate.objects.filter(election=election).order_by('id')
        
        formatted_results = []
        for i, (candidate_id, name, vote_count) in enumerate(zip(
            blockchain_results['candidate_ids'], 
            blockchain_results['names'], 
            blockchain_results['vote_counts']
        )):
            candidate_obj = None
            if i < len(candidates):
                candidate_obj = candidates[i]
            
            formatted_results.append({
                'blockchain_id': candidate_id,
                'name': name,
                'vote_count': vote_count,
                'user_id': candidate_obj.user.id if candidate_obj else None,
                'email': candidate_obj.user.email if candidate_obj else None
            })
        
        return Response({
            'election_id': election.id,
            'election_title': election.title,
            'results': formatted_results,
            'contract_address': update_contract_address,
            'total_votes': blockchain_results['total_votes'],
            'source': 'blockchain_updated',
            'blockchain': 'ethereum',
            'vote_updates_reflected': True
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Get updated Ethereum results failed: {e}")
        return Response({
            'error': str(e),
            'results': [],
            'total_votes': 0,
            'source': 'error',
            'blockchain': 'ethereum'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_hyperledger_vote(request):
    """Update existing Hyperledger vote to different candidate"""
    if not request.user.is_elector or not request.user.approved:
        return Response({'error': 'Approved elector access required'}, status=status.HTTP_403_FORBIDDEN)
    
    if not HYPERLEDGER_AVAILABLE:
        return Response({'error': 'Hyperledger not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    try:
        new_candidate_id = request.data.get('candidate_id')
        if not new_candidate_id:
            return Response({'error': 'New candidate ID required'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_election = request.user.selected_election
        if not user_election:
            return Response({'error': 'No election assigned'}, status=status.HTTP_400_BAD_REQUEST)
        
        voter_id = str(request.user.id)
        db_election_id = str(user_election.id)
        
        # Check if user has voted on Hyperledger
        from .models import Vote
        existing_vote = Vote.objects.filter(
            election=user_election,
            voter=request.user,
            transaction_hash__startswith='hlf-'
        ).first()
        
        if not existing_vote:
            return Response({'error': 'No Hyperledger vote found to update'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find new candidate
        candidates = Candidate.objects.filter(election=user_election).order_by('id')
        if int(new_candidate_id) > len(candidates):
            return Response({'error': 'Invalid candidate ID'}, status=status.HTTP_400_BAD_REQUEST)
            
        new_candidate = candidates[int(new_candidate_id) - 1]
        
        if existing_vote.candidate.id == new_candidate.id:
            return Response({'error': 'Already voting for this candidate'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update vote on Hyperledger
        handler = get_hyperledger_handler()
        if not handler:
            return Response({'error': 'Hyperledger handler not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        result = handler.cast_vote(db_election_id, str(new_candidate_id), voter_id)
        
        # Update database record
        old_candidate_name = existing_vote.candidate.name
        existing_vote.candidate = new_candidate
        existing_vote.transaction_hash = f"hlf-{result.get('transactionId', 'unknown')}"
        existing_vote.voted_at = timezone.now()
        existing_vote.save()
        
        return Response({
            'success': True,
            'message': f'Hyperledger vote updated from {old_candidate_name} to {new_candidate.name}!',
            'old_candidate': old_candidate_name,
            'new_candidate': new_candidate.name,
            'transaction_id': result.get('transactionId'),
            'blockchain': 'hyperledger'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': f'Vote update failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    """Update/modify existing Hyperledger vote"""
    if not HYPERLEDGER_AVAILABLE:
        return Response({'error': 'Hyperledger not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    if not request.user.is_elector or not request.user.approved:
        return Response({'error': 'Approved elector access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        new_candidate_id = request.data.get('candidate_id')
        if not new_candidate_id:
            return Response({'error': 'New candidate ID required'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_election = request.user.selected_election
        voter_id = str(request.user.id)
        election_id = str(user_election.id)
        
        # Check if user has voted on Hyperledger
        from .models import Vote
        existing_vote = Vote.objects.filter(
            election=user_election,
            voter=request.user,
            transaction_hash__startswith='hlf-'  # Hyperledger votes start with hlf-
        ).first()
        
        if not existing_vote:
            return Response({'error': 'No Hyperledger vote found to update'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find new candidate
        candidates = Candidate.objects.filter(election=user_election).order_by('id')
        if int(new_candidate_id) > len(candidates):
            return Response({'error': 'Invalid candidate ID'}, status=status.HTTP_400_BAD_REQUEST)
            
        new_candidate = candidates[int(new_candidate_id) - 1]
        
        if existing_vote.candidate.id == new_candidate.id:
            return Response({'error': 'Already voting for this candidate'}, status=status.HTTP_400_BAD_REQUEST)
        
        print(f"=== HYPERLEDGER VOTE UPDATE ===")
        print(f"User: {request.user.username}")
        print(f"From: {existing_vote.candidate.name} → To: {new_candidate.name}")
        
        # Update vote on Hyperledger blockchain
        handler = get_hyperledger_handler()
        if not handler:
            return Response({'error': 'Hyperledger handler not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Cast new vote on Hyperledger (this updates the blockchain state)
        result = handler.cast_vote(election_id, str(new_candidate_id), voter_id)
        
        # Update database record
        old_candidate_name = existing_vote.candidate.name
        existing_vote.candidate = new_candidate
        existing_vote.transaction_hash = f"hlf-{result.get('transactionId', 'unknown')}"
        existing_vote.voted_at = timezone.now()
        existing_vote.save()
        
        print(f"✅ Hyperledger vote updated: {result.get('transactionId')}")
        
        return Response({
            'success': True,
            'message': f'Hyperledger vote updated from {old_candidate_name} to {new_candidate.name}!',
            'old_candidate': old_candidate_name,
            'new_candidate': new_candidate.name,
            'transaction_id': result.get('transactionId'),
            'blockchain': 'hyperledger'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"❌ Hyperledger vote update failed: {e}")
        return Response({'error': f'Hyperledger vote update failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    """Update/modify existing Hyperledger vote"""
    if not HYPERLEDGER_AVAILABLE:
        return Response({'error': 'Hyperledger not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    if not request.user.is_elector or not request.user.approved:
        return Response({'error': 'Approved elector access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        new_candidate_id = request.data.get('candidate_id')
        if not new_candidate_id:
            return Response({'error': 'New candidate ID required'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_election = request.user.selected_election
        voter_id = str(request.user.id)
        election_id = str(user_election.id)
        
        # Check if user has voted on Hyperledger
        existing_vote = Vote.objects.filter(
            election=user_election,
            voter=request.user,
            transaction_hash__startswith='hlf-'  # Hyperledger votes start with hlf-
        ).first()
        
        if not existing_vote:
            return Response({'error': 'No Hyperledger vote found to update'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find new candidate
        candidates = Candidate.objects.filter(election=user_election).order_by('id')
        new_candidate = candidates[int(new_candidate_id) - 1]
        
        if existing_vote.candidate.id == new_candidate.id:
            return Response({'error': 'Already voting for this candidate'}, status=status.HTTP_400_BAD_REQUEST)
        
        print(f"=== HYPERLEDGER VOTE UPDATE ===")
        print(f"User: {request.user.username}")
        print(f"From: {existing_vote.candidate.name} → To: {new_candidate.name}")
        
        # Update vote on Hyperledger blockchain
        handler = get_hyperledger_handler()
        if not handler:
            return Response({'error': 'Hyperledger handler not available'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Cast new vote on Hyperledger (this updates the blockchain state)
        result = handler.cast_vote(election_id, str(new_candidate_id), voter_id)
        
        # Update database record
        old_candidate_name = existing_vote.candidate.name
        existing_vote.candidate = new_candidate
        existing_vote.transaction_hash = f"hlf-{result.get('transactionId', 'unknown')}"
        existing_vote.voted_at = timezone.now()
        existing_vote.save()
        
        print(f"✅ Hyperledger vote updated: {result.get('transactionId')}")
        
        return Response({
            'success': True,
            'message': f'Hyperledger vote updated from {old_candidate_name} to {new_candidate.name}!',
            'old_candidate': old_candidate_name,
            'new_candidate': new_candidate.name,
            'transaction_id': result.get('transactionId'),
            'blockchain': 'hyperledger'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"❌ Hyperledger vote update failed: {e}")
        return Response({'error': f'Hyperledger vote update failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_user_current_votes(request):
    """Get user's current votes on both blockchains"""
    try:
        if not request.user.selected_election:
            return Response({'ethereum_vote': None, 'hyperledger_vote': None})
        
        user_election = request.user.selected_election
        
        # Get Ethereum vote
        from .models import Vote
        ethereum_vote = Vote.objects.filter(
            election=user_election,
            voter=request.user
        ).exclude(transaction_hash__startswith='hlf-').first()  # Ethereum votes don't start with hlf-
        
        # Get Hyperledger vote  
        hyperledger_vote = Vote.objects.filter(
            election=user_election,
            voter=request.user,
            transaction_hash__startswith='hlf-'
        ).first()
        
        eth_data = None
        if ethereum_vote:
            eth_data = {
                'candidate_id': ethereum_vote.candidate.blockchain_id or ethereum_vote.candidate.id,
                'candidate_name': ethereum_vote.candidate.name,
                'candidate_email': ethereum_vote.candidate.user.email,
                'voted_at': ethereum_vote.voted_at,
                'tx_hash': ethereum_vote.transaction_hash
            }
        
        hlf_data = None
        if hyperledger_vote:
            hlf_data = {
                'candidate_id': hyperledger_vote.candidate.blockchain_id or hyperledger_vote.candidate.id,
                'candidate_name': hyperledger_vote.candidate.name,
                'candidate_email': hyperledger_vote.candidate.user.email,
                'voted_at': hyperledger_vote.voted_at,
                'tx_hash': hyperledger_vote.transaction_hash
            }
        
        return Response({
            'ethereum_vote': eth_data,
            'hyperledger_vote': hlf_data,
            'election_title': user_election.title
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    """Get user's current votes on both blockchains"""
    try:
        if not request.user.selected_election:
            return Response({'ethereum_vote': None, 'hyperledger_vote': None})
        
        user_election = request.user.selected_election
        
        # Get Ethereum vote
        ethereum_vote = Vote.objects.filter(
            election=user_election,
            voter=request.user
        ).exclude(transaction_hash__startswith='hlf-').first()
        
        # Get Hyperledger vote  
        hyperledger_vote = Vote.objects.filter(
            election=user_election,
            voter=request.user,
            transaction_hash__startswith='hlf-'
        ).first()
        
        eth_data = None
        if ethereum_vote:
            eth_data = {
                'candidate_id': ethereum_vote.candidate.blockchain_id or ethereum_vote.candidate.id,
                'candidate_name': ethereum_vote.candidate.name,
                'candidate_email': ethereum_vote.candidate.user.email,
                'voted_at': ethereum_vote.voted_at,
                'tx_hash': ethereum_vote.transaction_hash
            }
        
        hlf_data = None
        if hyperledger_vote:
            hlf_data = {
                'candidate_id': hyperledger_vote.candidate.blockchain_id or hyperledger_vote.candidate.id,
                'candidate_name': hyperledger_vote.candidate.name,
                'candidate_email': hyperledger_vote.candidate.user.email,
                'voted_at': hyperledger_vote.voted_at,
                'tx_hash': hyperledger_vote.transaction_hash
            }
        
        return Response({
            'ethereum_vote': eth_data,
            'hyperledger_vote': hlf_data,
            'election_title': user_election.title
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
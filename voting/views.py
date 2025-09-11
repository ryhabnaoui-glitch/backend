from rest_framework.decorators import api_view
from rest_framework.response import Response
from blockchain.ethereum_handler import EthereumHandler
from blockchain.ipfs_handler import IPFSHandler
import time

# Your exact initialization
eth = EthereumHandler()
ipfs = IPFSHandler()

@api_view(['POST'])
def create_election(request):
    """Matches path('elections/', views.create_election)"""
    try:
        # Your exact admin assignment
        admin_address = eth.w3.eth.accounts[0]
        
        # Your blockchain call (assuming create_election exists in EthereumHandler)
        tx_hash = eth.create_election(
            admin_address=admin_address,
            title=request.data['title'],
            candidate_ids=request.data['candidates'],
            duration_seconds=request.data.get('duration', 3600)
        )
        
        return Response({
            'status': 'Election created',
            'tx_hash': tx_hash,
            'admin': admin_address
        })

    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['POST'])
def cast_vote(request, election_id):
    """Matches path('elections/<int:election_id>/vote/', views.cast_vote)"""
    try:
        # Your dynamic wallet assignment
        voter_address = request.session.get('wallet') or eth.w3.eth.accounts[len(request.session)]
        request.session['wallet'] = voter_address
        
        # Your IPFS proof
        ipfs_hash = ipfs.add_json({
            'election_id': election_id,  # Now from URL parameter
            'candidate_id': request.data['candidate_id'],
            'voter': voter_address,
            'timestamp': str(time.time())
        })
        
        # Your blockchain transaction
        tx_hash = eth.vote(
            election_id=election_id,  # Now from URL parameter
            candidate_id=request.data['candidate_id'],
            voter_address=voter_address
        )
        
        return Response({
            'status': 'Vote recorded',
            'tx_hash': tx_hash,
            'ipfs_hash': ipfs_hash,
            'voter': voter_address
        })

    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['GET'])
def election_results(request, election_id):
    """Matches path('elections/<int:election_id>/results/', views.election_results)"""
    try:
        # Your contract interaction
        contract = eth.get_contract()
        results = contract.functions.getResults(election_id).call()
        
        return Response({
            'election_id': election_id,
            'results': results
        })

    except Exception as e:
        return Response({'error': str(e)}, status=400)
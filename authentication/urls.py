# authentication/urls.py - COMPLETE FIXED VERSION
from django.urls import path
from . import views

urlpatterns = [
    # Authentication endpoints
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('verify-auth/', views.verify_auth, name='verify-auth'),

    # Election management endpoints
    path('elections/', views.get_elections, name='get-elections'),
    path('elections/available/', views.get_available_elections, name='get-available-elections'),
    path('elections/create/', views.create_election, name='create-election'),
    path('elections/<int:election_id>/delete/', views.delete_election, name='delete-election'),

    # User management endpoints (admin only)
    path('pending-users/', views.get_pending_users, name='pending-users'),
    path('approve-user/<int:user_id>/', views.approve_user, name='approve-user'),
    path('reject-user/<int:user_id>/', views.reject_user, name='reject-user'),

    # Blockchain and wallet endpoints
    path('ganache-accounts/', views.get_ganache_accounts, name='ganache-accounts'),
    path('connect-wallet/', views.connect_wallet, name='connect-wallet'),
    path('assign-ganache-address/', views.assign_ganache_address, name='assign-ganache-address'),
    path('contract-address/', views.get_contract_address, name='contract-address'),
    path('available-accounts/', views.get_available_accounts, name='available-accounts'),

    # Ethereum election and voting endpoints
    path('candidates/', views.get_approved_candidates, name='approved-candidates'),
    path('vote/', views.cast_vote, name='cast-vote'),  # Ethereum vote
    path('election-results/', views.get_election_results, name='election-results'),
    path('check-vote-status/', views.check_user_vote_status, name='check-vote-status'),
    
    # Quick fix endpoint
    path('refresh-contract/', views.refresh_contract_address, name='refresh-contract'),

    # ============================================
    # HYPERLEDGER FABRIC ENDPOINTS
    # ============================================
    
    # Hyperledger voting
    path('hyperledger/add-candidate/', views.hyperledger_add_candidate, name='hyperledger-add-candidate'),
    path('hyperledger/cast-vote/', views.hyperledger_cast_vote, name='hyperledger-cast-vote'),
    
    # Results - can be called with or without election_id (dynamic)
    path('hyperledger/election-results/', views.hyperledger_election_results, name='hyperledger-election-results-dynamic'),
    path('hyperledger/election-results/<str:election_id>/', views.hyperledger_election_results, name='hyperledger-election-results'),
    
    # Vote status - uses user's selected election dynamically
    path('hyperledger/check-vote-status/', views.hyperledger_check_vote_status, name='hyperledger-check-vote-status'),
    
    # Dual blockchain voting (both Ethereum + Hyperledger)

    path('hyperledger/debug-raw/', views.debug_hyperledger_raw, name='hyperledger-debug-raw'),
    
    # ============================================
    # VOTE UPDATE ENDPOINTS - NEW
    # ============================================
    # Add these new URL patterns to your existing urlpatterns list:

# Ethereum update endpoints (new)
    # Add these new URL patterns to your existing urlpatterns list:

# Ethereum update endpoints (new)
path('ethereum/update-vote/', views.update_ethereum_vote, name='update-ethereum-vote'),
path('ethereum/deploy-update-contract/', views.deploy_update_contract, name='deploy-update-contract'),
path('ethereum/update-status/', views.get_ethereum_update_status, name='ethereum-update-status'),
path('ethereum/results-updated/', views.get_ethereum_results_updated, name='ethereum-results-updated'),
    path('hyperledger/update-vote/', views.update_hyperledger_vote, name='update-hyperledger-vote'),
    path('current-votes/', views.get_user_current_votes, name='get-current-votes')
]
# management/commands/sync_elections_blockchain.py - NEW COMMAND TO FIX SEEDED ELECTIONS
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from authentication.models import Election, Candidate
from blockchain.ethereum_handler import EthereumHandler
from django.core.cache import cache

User = get_user_model()

class Command(BaseCommand):
    help = 'Sync existing database elections to blockchain (fixes seeded elections)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreate all elections on blockchain'
        )

    def handle(self, *args, **options):
        self.stdout.write("🔄 Syncing elections to blockchain...")
        
        try:
            # Initialize Ethereum handler
            eth_handler = EthereumHandler()
            if not eth_handler.is_connected():
                self.stdout.write(self.style.ERROR("❌ Ganache not connected!"))
                return
            
            # Deploy or get contract
            admin_address = eth_handler.w3.eth.accounts[0]
            contract_address = cache.get('voting_system_contract_simple')
            
            if not contract_address or options['force']:
                self.stdout.write("🚀 Deploying new voting contract...")
                contract_address = eth_handler.deploy_contract(admin_address)
                cache.set('voting_system_contract_simple', contract_address, 86400)
                self.stdout.write(f"✅ Contract deployed: {contract_address}")
            else:
                eth_handler.get_contract(contract_address)
                self.stdout.write(f"📋 Using existing contract: {contract_address}")
            
            # Get all elections that need blockchain setup
            elections_to_sync = Election.objects.filter(is_active=True)
            
            if options['force']:
                # Reset all blockchain IDs if forcing
                elections_to_sync.update(blockchain_id=None)
                Candidate.objects.all().update(blockchain_id=None)
                self.stdout.write("🔄 Reset all blockchain IDs")
            
            synced_count = 0
            
            for election in elections_to_sync:
                if not election.blockchain_id or options['force']:
                    try:
                        # Create election on blockchain
                        self.stdout.write(f"📝 Creating blockchain election: {election.title}")
                        
                        tx_hash, receipt, blockchain_election_id = eth_handler.create_election(
                            election.title,
                            election.description or "Election",
                            0, 0, admin_address
                        )
                        
                        election.blockchain_id = blockchain_election_id
                        election.contract_address = contract_address
                        election.save()
                        
                        self.stdout.write(f"✅ Election synced: {election.title} → Blockchain ID: {blockchain_election_id}")
                        
                        # Add candidates to blockchain
                        candidates = Candidate.objects.filter(election=election).order_by('id')
                        candidates_added = 0
                        
                        for candidate in candidates:
                            if candidate.wallet_address:
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
                                    
                                    self.stdout.write(f"  ✅ Added candidate: {candidate.name} → Blockchain ID: {candidate_blockchain_id}")
                                    
                                except Exception as e:
                                    self.stdout.write(f"  ⚠️ Failed to add candidate {candidate.name}: {e}")
                            else:
                                self.stdout.write(f"  ⚠️ Candidate {candidate.name} has no wallet address")
                        
                        self.stdout.write(f"  📊 Added {candidates_added}/{len(candidates)} candidates")
                        synced_count += 1
                        
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"❌ Failed to sync {election.title}: {e}"))
                else:
                    self.stdout.write(f"⏭️ {election.title} already synced (Blockchain ID: {election.blockchain_id})")
            
            self.stdout.write(self.style.SUCCESS(f"\n🎉 Sync complete! {synced_count} elections synced to blockchain"))
            self.stdout.write(f"📋 Contract Address: {contract_address}")
            
            # Verify setup
            self.stdout.write("\n🔍 Verification:")
            current_election_id = eth_handler.contract.functions.getCurrentElectionId().call()
            self.stdout.write(f"  📊 Elections on blockchain: {current_election_id}")
            
            for election in Election.objects.filter(is_active=True, blockchain_id__isnull=False):
                candidate_count = eth_handler.contract.functions.getCandidateCount(election.blockchain_id).call()
                self.stdout.write(f"  🗳️ {election.title}: {candidate_count} candidates")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Sync failed: {e}"))
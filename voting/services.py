from blockchain import EthereumHandler, HyperledgerHandler, IPFSHandler

class VotingService:
    def __init__(self):
        self.eth = EthereumHandler()
        self.hlf = HyperledgerHandler()
        self.ipfs = IPFSHandler()

    def get_wallet(self, session):
        """Dynamically assigns Ganache wallet to session"""
        if 'wallet' not in session:
            session['wallet'] = self.eth.w3.eth.accounts[len(session)]
        return session['wallet']
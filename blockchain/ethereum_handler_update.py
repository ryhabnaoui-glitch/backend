# blockchain/ethereum_handler_update.py - FOR SimpleVotingWithUpdate CONTRACT

from web3 import Web3
from web3.middleware import geth_poa_middleware
import json
import traceback
import os

class EthereumUpdateHandler:
    def __init__(self):
        # Same connection logic as your original
        ganache_url = self._get_ganache_url()
        
        self.w3 = Web3(Web3.HTTPProvider(ganache_url))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.contract = None
        self.contract_address = None
        
        print(f"🔗 Enhanced Ethereum Handler connecting to: {ganache_url}")
      
    def _get_ganache_url(self):
        """Auto-detect Ganache URL based on environment"""
        if os.getenv('DOCKER_ENV') or os.path.exists('/.dockerenv'):
            return 'http://ganache:8545'
        else:
            return 'http://localhost:8545'
    
    def is_connected(self):
        try:
            return self.w3.is_connected()
        except Exception as e:
            print(f"🔴 Enhanced Ganache connection failed: {e}")
            return False
    
    def get_accounts(self):
        try:
            accounts = self.w3.eth.accounts
            print(f"📊 Enhanced handler found {len(accounts)} accounts")
            return accounts
        except Exception as e:
            print(f"🔴 Failed to get enhanced accounts: {e}")
            return []
    
    def deploy_contract(self, deployer_address=None):
        """Deploy SimpleVotingWithUpdate contract"""
        try:
            print("🚀 Deploying SimpleVotingWithUpdate contract...")
            
            if not deployer_address:
                accounts = self.get_accounts()
                if not accounts:
                    raise Exception("No accounts available")
                deployer_address = accounts[0]
                
            deployer_address = self.w3.to_checksum_address(deployer_address)
            print(f"👤 Enhanced Deployer: {deployer_address}")
            
            balance = self.w3.eth.get_balance(deployer_address)
            print(f"💰 Enhanced Balance: {self.w3.from_wei(balance, 'ether')} ETH")
            
            # ABI from your compiled contract
            abi = [{"anonymous":False,"inputs":[{"indexed":True,"internalType":"uint256","name":"electionId","type":"uint256"},{"indexed":True,"internalType":"uint256","name":"candidateId","type":"uint256"},{"indexed":False,"internalType":"string","name":"name","type":"string"}],"name":"CandidateAdded","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"uint256","name":"electionId","type":"uint256"},{"indexed":False,"internalType":"string","name":"title","type":"string"}],"name":"ElectionCreated","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"uint256","name":"electionId","type":"uint256"},{"indexed":True,"internalType":"uint256","name":"candidateId","type":"uint256"},{"indexed":False,"internalType":"address","name":"voter","type":"address"}],"name":"VoteCast","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"uint256","name":"electionId","type":"uint256"},{"indexed":False,"internalType":"address","name":"voter","type":"address"},{"indexed":False,"internalType":"uint256","name":"oldCandidateId","type":"uint256"},{"indexed":False,"internalType":"uint256","name":"newCandidateId","type":"uint256"}],"name":"VoteUpdated","type":"event"},{"constant":False,"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"},{"internalType":"address","name":"candidateAddress","type":"address"},{"internalType":"string","name":"name","type":"string"}],"name":"addCandidate","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":False,"stateMutability":"nonpayable","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"candidateCounters","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"uint256","name":"","type":"uint256"}],"name":"candidates","outputs":[{"internalType":"uint256","name":"id","type":"uint256"},{"internalType":"string","name":"name","type":"string"},{"internalType":"address","name":"candidateAddress","type":"address"},{"internalType":"uint256","name":"voteCount","type":"uint256"},{"internalType":"bool","name":"exists","type":"bool"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":False,"inputs":[{"internalType":"string","name":"title","type":"string"},{"internalType":"string","name":"description","type":"string"},{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"uint256","name":"","type":"uint256"}],"name":"createElection","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":False,"stateMutability":"nonpayable","type":"function"},{"constant":True,"inputs":[],"name":"electionCounter","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"elections","outputs":[{"internalType":"uint256","name":"id","type":"uint256"},{"internalType":"string","name":"title","type":"string"},{"internalType":"string","name":"description","type":"string"},{"internalType":"address","name":"creator","type":"address"},{"internalType":"bool","name":"exists","type":"bool"},{"internalType":"uint256","name":"totalVotes","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"}],"name":"getCandidateCount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"},{"internalType":"uint256","name":"candidateId","type":"uint256"}],"name":"getCandidateInfo","outputs":[{"internalType":"string","name":"","type":"string"},{"internalType":"address","name":"","type":"address"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"},{"internalType":"uint256","name":"candidateId","type":"uint256"}],"name":"getCandidateVotes","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[],"name":"getCurrentElectionId","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"}],"name":"getElectionInfo","outputs":[{"internalType":"string","name":"","type":"string"},{"internalType":"string","name":"","type":"string"},{"internalType":"address","name":"","type":"address"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"}],"name":"getElectionResults","outputs":[{"internalType":"uint256[]","name":"candidateIds","type":"uint256[]"},{"internalType":"string[]","name":"names","type":"string[]"},{"internalType":"uint256[]","name":"voteCounts","type":"uint256[]"},{"internalType":"uint256","name":"totalVotes","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"}],"name":"getTotalVotes","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"},{"internalType":"address","name":"user","type":"address"}],"name":"getUserVote","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"hasElectionEnded","outputs":[{"internalType":"bool","name":"","type":"bool"}],"payable":False,"stateMutability":"pure","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"},{"internalType":"address","name":"user","type":"address"}],"name":"hasUserVoted","outputs":[{"internalType":"bool","name":"","type":"bool"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"address","name":"","type":"address"}],"name":"hasVoted","outputs":[{"internalType":"bool","name":"","type":"bool"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"isElectionActive","outputs":[{"internalType":"bool","name":"","type":"bool"}],"payable":False,"stateMutability":"pure","type":"function"},{"constant":False,"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"},{"internalType":"uint256","name":"newCandidateId","type":"uint256"}],"name":"updateVote","outputs":[],"payable":False,"stateMutability":"nonpayable","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"address","name":"","type":"address"}],"name":"userVotes","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":False,"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"},{"internalType":"uint256","name":"candidateId","type":"uint256"},{"internalType":"string","name":"","type":"string"}],"name":"vote","outputs":[],"payable":False,"stateMutability":"nonpayable","type":"function"}]
            
            # Bytecode directly embedded (no file needed)
            bytecode = "0x608060405234801561001057600080fd5b50611b22806100206000396000f3fe608060405234801561001057600080fd5b50600436106101375760003560e01c80637ad36e84116100b8578063ce99b5df1161007c578063ce99b5df146102a4578063dc296ae1146102c6578063e1f8792b146102d9578063e8ededa6146102ec578063fe2b536b1461030f578063fe5b3e3b1461031757610137565b80637ad36e84146102345780637de14242146102475780638f15b7c61461026b578063a1bbfc051461027e578063cadc68e91461029157610137565b80635e6fef01116100ff5780635e6fef01146101be57806361e37417146101e35780636ee17f6f146101eb57806371275c4a146101fe57806373a12f5a1461021357610137565b806303c7881a1461013c578063112d26a91461016557806326f6a2aa146101785780632ce35e111461018b578063438596321461019e575b600080fd5b61014f61014a3660046113fb565b61032a565b60405161015c9190611921565b60405180910390f35b61014f61017336600461149a565b6103d8565b61014f6101863660046113dd565b61046d565b61014f6101993660046113dd565b6104b8565b6101b16101ac3660046113fb565b610506565b60405161015c919061183e565b6101d16101cc3660046113dd565b610526565b60405161015c96959493929190611982565b61014f610680565b6101b16101f93660046113dd565b610686565b61021161020c36600461149a565b61068c565b005b61022661022136600461149a565b6107ff565b60405161015c92919061185d565b61014f61024236600461134d565b610939565b61025a61025536600461149a565b610a5f565b60405161015c95949392919061192f565b61014f6102793660046113dd565b610b2b565b61021161028c3660046114ca565b610b3d565b6101b161029f3660046113dd565b610c96565b6102b76102b23660046113dd565b610c9c565b60405161015c9392919061187d565b6101b16102d43660046113fb565b610e2a565b61014f6102e7366004611435565b610e8e565b6102ff6102fa3660046113dd565b611006565b60405161015c94939291906117ed565b61014f611227565b61014f6103253660046113fb565b61122e565b600082815260016020526040812060030154600160a01b900460ff1661036b5760405162461bcd60e51b8152600401610362906118d1565b60405180910390fd5b60008381526004602090815260408083206001600160a01b038616845290915290205460ff166103ad5760405162461bcd60e51b815260040161036290611911565b5060008281526005602090815260408083206001600160a01b03851684529091529020545b92915050565b600082815260016020526040812060030154600160a01b900460ff166104105760405162461bcd60e51b8152600401610362906118d1565b600083815260026020908152604080832085845290915290206004015460ff1661044c5760405162461bcd60e51b8152600401610362906118f1565b50600091825260026020908152604080842092845291905290206003015490565b600081815260016020526040812060030154600160a01b900460ff166104a55760405162461bcd60e51b8152600401610362906118d1565b5060009081526003602052604090205490565b600081815260016020526040812060030154600160a01b900460ff166104f05760405162461bcd60e51b8152600401610362906118d1565b5060009081526001602052604090206004015490565b600460209081526000928352604080842090915290825290205460ff1681565b600160208181526000928352604092839020805481840180548651600296821615610100026000190190911695909504601f810185900485028601850190965285855290949193929091908301828280156105c25780601f10610597576101008083540402835291602001916105c2565b820191906000526020600020905b8154815290600101906020018083116105a557829003601f168201915b50505060028085018054604080516020601f60001961010060018716150201909416959095049283018590048502810185019091528181529596959450909250908301828280156106545780601f1061062957610100808354040283529160200191610654565b820191906000526020600020905b81548152906001019060200180831161063757829003601f168201915b50505050600383015460049093015491926001600160a01b03811692600160a01b90910460ff16915086565b60005481565b50600190565b600082815260016020526040902060030154600160a01b900460ff166106c45760405162461bcd60e51b8152600401610362906118d1565b600082815260026020908152604080832084845290915290206004015460ff166107005760405162461bcd60e51b8152600401610362906118f1565b600082815260046020908152604080832033845290915290205460ff166107395760405162461bcd60e51b815260040161036290611901565b6000828152600560209081526040808320338452909152902054818114156107735760405162461bcd60e51b8152600401610362906118e1565b600083815260026020908152604080832084845282528083206003908101805460001901905585845281842001805460010190558583526005825280832033808552925291829020849055905184917f01fb0ee4a348bf16ac66945e04d443749388cb6214cb35b266626c263db216a5916107f29190859087906117c5565b60405180910390a2505050565b60008281526001602052604081206003015460609190600160a01b900460ff1661083b5760405162461bcd60e51b8152600401610362906118d1565b600084815260026020908152604080832086845290915290206004015460ff166108775760405162461bcd60e51b8152600401610362906118f1565b600084815260026020818152604080842087855282529283902080830154600191820180548651601f600019958316156101000295909501909116959095049283018490048402850184019095528184526001600160a01b031692918491908301828280156109275780601f106108fc57610100808354040283529160200191610927565b820191906000526020600020905b81548152906001019060200180831161090a57829003601f168201915b50505050509150915091509250929050565b6000805460019081018083556040805160c08101825282815260208082018a81528284018a90523360608401526080830186905260a0830187905293865284815291852081518155925180519194610997939085019291019061124b565b50604082015180516109b391600284019160209091019061124b565b5060608201516003808301805460808601511515600160a01b0260ff60a01b196001600160a01b039095166001600160a01b031990921691909117939093169290921790915560a0909201516004909101556000805481526020919091526040808220829055905490517f52be7c4e77b4de76b7607d621492061fe13b58597e72dfb5e51ab8f6187ed14190610a4a90889061184c565b60405180910390a2506000545b949350505050565b600260208181526000938452604080852082529284529282902080546001808301805486519281161561010002600019011694909404601f810187900487028201870190955284815290949193909291830182828015610b005780601f10610ad557610100808354040283529160200191610b00565b820191906000526020600020905b815481529060010190602001808311610ae357829003601f168201915b505050506002830154600384015460049094015492936001600160a01b039091169290915060ff1685565b60036020526000908152604090205481565b600083815260016020526040902060030154600160a01b900460ff16610b755760405162461bcd60e51b8152600401610362906118d1565b600083815260026020908152604080832085845290915290206004015460ff16610bb15760405162461bcd60e51b8152600401610362906118f1565b600083815260046020908152604080832033845290915290205460ff1615610beb5760405162461bcd60e51b8152600401610362906118c1565b6000838152600260209081526040808320858452825280832060030180546001908101909155868452600480845282852033808752908552838620805460ff191684179055888652828552838620909101805490920190915560058352818420818552909252918290208490559051839185917f7fe1d4e6b34e228b5dc059fcdc037c71b216fb2417f47c171e505144a5e4f5fc91610c89916117b7565b60405180910390a3505050565b50600090565b6000818152600160205260408120600301546060918291600160a01b900460ff16610cd95760405162461bcd60e51b8152600401610362906118d1565b6000848152600160208181526040928390206003810154818401805486516002610100978316159790970260001901909116869004601f8101869004860282018601909752868152909594909201936001600160a01b0390911692859190830182828015610d885780601f10610d5d57610100808354040283529160200191610d88565b820191906000526020600020905b815481529060010190602001808311610d6b57829003601f168201915b5050855460408051602060026001851615610100026000190190941693909304601f810184900484028201840190925281815295985087945092508401905082828015610e165780601f10610deb57610100808354040283529160200191610e16565b820191906000526020600020905b815481529060010190602001808311610df957829003601f168201915b505050505091509250925092509193909250565b600082815260016020526040812060030154600160a01b900460ff16610e625760405162461bcd60e51b8152600401610362906118d1565b5060009182526004602090815260408084206001600160a01b0393909316845291905290205460ff1690565b600083815260016020526040812060030154600160a01b900460ff16610ec65760405162461bcd60e51b8152600401610362906118d1565b6000848152600160205260409020600301546001600160a01b03163314610eff5760405162461bcd60e51b8152600401610362906118b1565b60008481526003602090815260408083208054600190810191829055825160a0810184528281528085018881526001600160a01b038a168286015260608201879052608082018390528a8752600286528487208488528652939095208551815592518051929594610f76939285019291019061124b565b506040828101516002830180546001600160a01b0319166001600160a01b03909216919091179055606083015160038301556080909201516004909101805460ff191691151591909117905551819086907fed8911b3df733b7d5f75724158e54478ea12e30f49c9d31b5261879f5b76586f90610ff490879061184c565b60405180910390a390505b9392505050565b6000818152600160205260408120600301546060918291829190600160a01b900460ff166110465760405162461bcd60e51b8152600401610362906118d1565b6000858152600360209081526040918290205482518181528183028101909201909252818015611080578160200160208202803883390190505b509450806040519080825280602002602001820160405280156110b757816020015b60608152602001906001900390816110a25790505b509350806040519080825280602002602001820160405280156110e4578160200160208202803883390190505b50925060015b81811161120b578086600183038151811061110157fe5b6020908102919091018101919091526000888152600280835260408083208584528452918290206001908101805484519281161561010002600019011692909204601f8101859004850282018501909352828152929091908301828280156111aa5780601f1061117f576101008083540402835291602001916111aa565b820191906000526020600020905b81548152906001019060200180831161118d57829003601f168201915b50505050508560018303815181106111be57fe5b602090810291909101810191909152600088815260028252604080822084835290925220600301548451859060001984019081106111f857fe5b60209081029190910101526001016110ea565b5050506000848152600160205260409020600401549193509193565b6000545b90565b600560209081526000928352604080842090915290825290205481565b828054600181600116156101000203166002900490600052602060002090601f016020900481019282601f1061128c57805160ff19168380011785556112b9565b828001600101855582156112b9579182015b828111156112b957825182559160200191906001019061129e565b506112c59291506112c9565b5090565b61122b91905b808211156112c557600081556001016112cf565b80356103d281611abf565b600082601f8301126112ff57600080fd5b813561131261130d82611a11565b6119ea565b9150808252602083016020830185838301111561132e57600080fd5b611339838284611a79565b50505092915050565b80356103d281611ad6565b6000806000806080858703121561136357600080fd5b843567ffffffffffffffff81111561137a57600080fd5b611386878288016112ee565b945050602085013567ffffffffffffffff8111156113a357600080fd5b6113af878288016112ee565b93505060406113c087828801611342565b92505060606113d187828801611342565b91505092959194509250565b6000602082840312156113ef57600080fd5b6000610a578484611342565b6000806040838503121561140e57600080fd5b600061141a8585611342565b925050602061142b858286016112e3565b9150509250929050565b60008060006060848603121561144a57600080fd5b60006114568686611342565b9350506020611467868287016112e3565b925050604084013567ffffffffffffffff81111561148457600080fd5b611490868287016112ee565b9150509250925092565b600080604083850312156114ad57600080fd5b60006114b98585611342565b925050602061142b85828601611342565b6000806000606084860312156114df57600080fd5b60006114eb8686611342565b935050602061146786828701611342565b6000610fff8383611604565b600061151483836117ae565b505060200190565b61152581611a68565b82525050565b61152581611a4c565b600061153f82611a3f565b6115498185611a43565b93508360208202850161155b85611a39565b8060005b85811015611595578484038952815161157885826114fc565b945061158383611a39565b60209a909a019992505060010161155f565b5091979650505050505050565b60006115ad82611a3f565b6115b78185611a43565b93506115c283611a39565b8060005b838110156115f05781516115da8882611508565b97506115e583611a39565b9250506001016115c6565b509495945050505050565b61152581611a57565b600061160f82611a3f565b6116198185611a43565b9350611629818560208601611a85565b61163281611ab5565b9093019392505050565b6000611649601f83611a43565b7f4f6e6c792063726561746f722063616e206164642063616e6469646174657300815260200192915050565b6000611682600d83611a43565b6c105b1c9958591e481d9bdd1959609a1b815260200192915050565b60006116ab601783611a43565b7f456c656374696f6e20646f6573206e6f74206578697374000000000000000000815260200192915050565b60006116e4602183611a43565b7f416c726561647920766f74696e6720666f7220746869732063616e64696461748152606560f81b602082015260400192915050565b6000611727601883611a43565b7f43616e64696461746520646f6573206e6f742065786973740000000000000000815260200192915050565b6000611760601183611a43565b704e6f20766f746520746f2075706461746560781b815260200192915050565b600061178d601283611a43565b71155cd95c881a185cc81b9bdd081d9bdd195960721b815260200192915050565b6115258161122b565b602081016103d2828461151c565b606081016117d3828661151c565b6117e060208301856117ae565b610a5760408301846117ae565b608080825281016117fe81876115a2565b905081810360208301526118128186611534565b9050818103604083015261182681856115a2565b905061183560608301846117ae565b95945050505050565b602081016103d282846115fb565b60208082528101610fff8184611604565b6040808252810161186e8185611604565b9050610fff602083018461152b565b6060808252810161188e8186611604565b905081810360208301526118a28185611604565b9050610a57604083018461152b565b602080825281016103d28161163c565b602080825281016103d281611675565b602080825281016103d28161169e565b602080825281016103d2816116d7565b602080825281016103d28161171a565b602080825281016103d281611753565b602080825281016103d281611780565b602081016103d282846117ae565b60a0810161193d82886117ae565b818103602083015261194f8187611604565b905061195e604083018661152b565b61196b60608301856117ae565b61197860808301846115fb565b9695505050505050565b60c0810161199082896117ae565b81810360208301526119a28188611604565b905081810360408301526119b68187611604565b90506119c5606083018661152b565b6119d260808301856115fb565b6119df60a08301846117ae565b979650505050505050565b60405181810167ffffffffffffffff81118282101715611a0957600080fd5b604052919050565b600067ffffffffffffffff821115611a2857600080fd5b506020601f91909101601f19160190565b60200190565b5190565b90815260200190565b60006103d282611a5c565b151590565b6001600160a01b031690565b60006103d28260006103d282611a4c565b82818337506000910152565b60005b83811015611aa0578181015183820152602001611a88565b83811115611aaf576000848401525b50505050565b601f01601f191690565b611ac881611a4c565b8114611ad357600080fd5b50565b611ac88161122b56fea365627a7a72315820abad42331ee6e6835dee541424f9e9f636b21815279babccd643ec0d48a45dec6c6578706572696d656e74616cf564736f6c63430005100040"
            
            print("🔨 Deploying SimpleVotingWithUpdate contract...")
            
            # Create contract
            contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
            
            # Deploy with conservative settings
            tx_hash = contract.constructor().transact({
                'from': deployer_address,
                'gas': 4000000,  # Increased gas for new contract
                'gasPrice': self.w3.to_wei('1', 'gwei')
            })
            
            print(f"📤 Enhanced TX: {tx_hash.hex()}")
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            
            print(f"📋 Enhanced Status: {receipt.status}")
            print(f"⛽ Enhanced Gas used: {receipt.gasUsed}")
            
            if receipt.status != 1:
                raise Exception(f"Enhanced deployment failed with status: {receipt.status}")
            
            self.contract_address = self.w3.to_checksum_address(receipt.contractAddress)
            self.contract = self.w3.eth.contract(address=self.contract_address, abi=abi)
            
            print(f"✅ SimpleVotingWithUpdate deployed: {self.contract_address}")
            return self.contract_address
            
        except Exception as e:
            print(f"❌ Enhanced deployment failed: {e}")
            traceback.print_exc()
            raise e
    
    def get_contract(self, contract_address):
        """Load existing SimpleVotingWithUpdate contract"""
        try:
            self.contract_address = self.w3.to_checksum_address(contract_address)
            
            # Same ABI as above
            abi = [{"anonymous":False,"inputs":[{"indexed":True,"internalType":"uint256","name":"electionId","type":"uint256"},{"indexed":True,"internalType":"uint256","name":"candidateId","type":"uint256"},{"indexed":False,"internalType":"string","name":"name","type":"string"}],"name":"CandidateAdded","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"uint256","name":"electionId","type":"uint256"},{"indexed":False,"internalType":"string","name":"title","type":"string"}],"name":"ElectionCreated","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"uint256","name":"electionId","type":"uint256"},{"indexed":True,"internalType":"uint256","name":"candidateId","type":"uint256"},{"indexed":False,"internalType":"address","name":"voter","type":"address"}],"name":"VoteCast","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"uint256","name":"electionId","type":"uint256"},{"indexed":False,"internalType":"address","name":"voter","type":"address"},{"indexed":False,"internalType":"uint256","name":"oldCandidateId","type":"uint256"},{"indexed":False,"internalType":"uint256","name":"newCandidateId","type":"uint256"}],"name":"VoteUpdated","type":"event"},{"constant":False,"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"},{"internalType":"address","name":"candidateAddress","type":"address"},{"internalType":"string","name":"name","type":"string"}],"name":"addCandidate","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":False,"stateMutability":"nonpayable","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"candidateCounters","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"uint256","name":"","type":"uint256"}],"name":"candidates","outputs":[{"internalType":"uint256","name":"id","type":"uint256"},{"internalType":"string","name":"name","type":"string"},{"internalType":"address","name":"candidateAddress","type":"address"},{"internalType":"uint256","name":"voteCount","type":"uint256"},{"internalType":"bool","name":"exists","type":"bool"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":False,"inputs":[{"internalType":"string","name":"title","type":"string"},{"internalType":"string","name":"description","type":"string"},{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"uint256","name":"","type":"uint256"}],"name":"createElection","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":False,"stateMutability":"nonpayable","type":"function"},{"constant":True,"inputs":[],"name":"electionCounter","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"elections","outputs":[{"internalType":"uint256","name":"id","type":"uint256"},{"internalType":"string","name":"title","type":"string"},{"internalType":"string","name":"description","type":"string"},{"internalType":"address","name":"creator","type":"address"},{"internalType":"bool","name":"exists","type":"bool"},{"internalType":"uint256","name":"totalVotes","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"}],"name":"getCandidateCount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"},{"internalType":"uint256","name":"candidateId","type":"uint256"}],"name":"getCandidateInfo","outputs":[{"internalType":"string","name":"","type":"string"},{"internalType":"address","name":"","type":"address"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"},{"internalType":"uint256","name":"candidateId","type":"uint256"}],"name":"getCandidateVotes","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[],"name":"getCurrentElectionId","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"}],"name":"getElectionInfo","outputs":[{"internalType":"string","name":"","type":"string"},{"internalType":"string","name":"","type":"string"},{"internalType":"address","name":"","type":"address"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"}],"name":"getElectionResults","outputs":[{"internalType":"uint256[]","name":"candidateIds","type":"uint256[]"},{"internalType":"string[]","name":"names","type":"string[]"},{"internalType":"uint256[]","name":"voteCounts","type":"uint256[]"},{"internalType":"uint256","name":"totalVotes","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"}],"name":"getTotalVotes","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"},{"internalType":"address","name":"user","type":"address"}],"name":"getUserVote","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"hasElectionEnded","outputs":[{"internalType":"bool","name":"","type":"bool"}],"payable":False,"stateMutability":"pure","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"},{"internalType":"address","name":"user","type":"address"}],"name":"hasUserVoted","outputs":[{"internalType":"bool","name":"","type":"bool"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"address","name":"","type":"address"}],"name":"hasVoted","outputs":[{"internalType":"bool","name":"","type":"bool"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"isElectionActive","outputs":[{"internalType":"bool","name":"","type":"bool"}],"payable":False,"stateMutability":"pure","type":"function"},{"constant":False,"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"},{"internalType":"uint256","name":"newCandidateId","type":"uint256"}],"name":"updateVote","outputs":[],"payable":False,"stateMutability":"nonpayable","type":"function"},{"constant":True,"inputs":[{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"address","name":"","type":"address"}],"name":"userVotes","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":False,"stateMutability":"view","type":"function"},{"constant":False,"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"},{"internalType":"uint256","name":"candidateId","type":"uint256"},{"internalType":"string","name":"","type":"string"}],"name":"vote","outputs":[],"payable":False,"stateMutability":"nonpayable","type":"function"}]
            
            code = self.w3.eth.get_code(contract_address)
            if code == b'':
                raise Exception(f"No enhanced contract at address: {contract_address}")
            
            self.contract = self.w3.eth.contract(address=contract_address, abi=abi)
            print(f"✅ Enhanced contract loaded: {contract_address}")
            return self.contract
            
        except Exception as e:
            print(f"❌ Enhanced load failed: {e}")
            return None
    
    # ALL THE SAME FUNCTIONS AS YOUR ORIGINAL + NEW UPDATE FUNCTIONS
    
    def create_election(self, title, description, start_time, end_time, creator_address):
        """Create election - same as original"""
        try:
            if not self.contract:
                raise Exception("Enhanced contract not loaded")
            
            creator_address = self.w3.to_checksum_address(creator_address)
            print(f"🗳️ Enhanced creating election: {title}")
            
            tx_hash = self.contract.functions.createElection(
                title, description, start_time, end_time
            ).transact({
                'from': creator_address,
                'gas': 500000,
                'gasPrice': self.w3.to_wei('1', 'gwei')
            })
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status != 1:
                raise Exception("Enhanced create election failed")
            
            election_id = self.contract.functions.getCurrentElectionId().call()
            print(f"✅ Enhanced election created: {election_id}")
            
            return tx_hash.hex(), receipt, election_id
            
        except Exception as e:
            print(f"❌ Enhanced create election failed: {e}")
            raise e
    
    def add_candidate(self, election_id, candidate_address, name, creator_address):
        """Add candidate - same as original"""
        try:
            if not self.contract:
                raise Exception("Enhanced contract not loaded")
            
            candidate_address = self.w3.to_checksum_address(candidate_address)
            creator_address = self.w3.to_checksum_address(creator_address)
            print(f"👤 Enhanced adding candidate: {name}")
            
            tx_hash = self.contract.functions.addCandidate(
                election_id, candidate_address, name
            ).transact({
                'from': creator_address,
                'gas': 300000,
                'gasPrice': self.w3.to_wei('1', 'gwei')
            })
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status != 1:
                raise Exception("Enhanced add candidate failed")
            
            candidate_count = self.contract.functions.getCandidateCount(election_id).call()
            print(f"✅ Enhanced candidate added: {candidate_count}")
            
            return tx_hash.hex(), receipt, candidate_count
            
        except Exception as e:
            print(f"❌ Enhanced add candidate failed: {e}")
            raise e
    
    def vote(self, election_id, candidate_id, voter_address):
        """Cast vote - same as original"""
        try:
            if not self.contract:
                raise Exception("Enhanced contract not loaded")
            
            voter_address = self.w3.to_checksum_address(voter_address)
            print(f"🗳️ Enhanced voting: election {election_id}, candidate {candidate_id}")
            
            self.fund_voter_account(voter_address)
            
            tx_hash = self.contract.functions.vote(
                election_id, candidate_id, ""
            ).transact({
                'from': voter_address,
                'gas': 200000,
                'gasPrice': self.w3.to_wei('1', 'gwei')
            })
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status != 1:
                raise Exception("Enhanced vote failed")
            
            print(f"✅ Enhanced vote cast! Gas used: {receipt.gasUsed}")
            return tx_hash.hex(), receipt
            
        except Exception as e:
            print(f"❌ Enhanced vote failed: {e}")
            raise e
    
    # NEW: Update vote function
    def update_vote(self, election_id, new_candidate_id, voter_address):
        """Update existing vote - NEW FUNCTION"""
        try:
            if not self.contract:
                raise Exception("Enhanced contract not loaded")
            
            voter_address = self.w3.to_checksum_address(voter_address)
            print(f"🔄 Enhanced updating vote: election {election_id}, new candidate {new_candidate_id}")
            
            # Fund voter if needed
            self.fund_voter_account(voter_address)
            
            # Get current vote
            current_vote = self.get_user_vote(election_id, voter_address)
            print(f"📋 Current vote: {current_vote} → New vote: {new_candidate_id}")
            
            tx_hash = self.contract.functions.updateVote(
                election_id, new_candidate_id
            ).transact({
                'from': voter_address,
                'gas': 200000,
                'gasPrice': self.w3.to_wei('1', 'gwei')
            })
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status != 1:
                raise Exception("Enhanced vote update failed")
            
            print(f"✅ Enhanced vote updated! Gas used: {receipt.gasUsed}")
            return tx_hash.hex(), receipt, current_vote
            
        except Exception as e:
            print(f"❌ Enhanced vote update failed: {e}")
            raise e
    
    # NEW: Get user's current vote
    def get_user_vote(self, election_id, user_address):
        """Get what user voted for - NEW FUNCTION"""
        try:
            if not self.contract:
                return None
            user_address = self.w3.to_checksum_address(user_address)
            return self.contract.functions.getUserVote(election_id, user_address).call()
        except Exception as e:
            print(f"❌ Get user vote failed: {e}")
            return None
    
    # ALL OTHER FUNCTIONS SAME AS ORIGINAL
    def has_user_voted(self, election_id, user_address):
        """Check if voted - same as original"""
        try:
            if not self.contract:
                return False
            user_address = self.w3.to_checksum_address(user_address)
            return self.contract.functions.hasUserVoted(election_id, user_address).call()
        except:
            return False
    
    def get_election_results(self, election_id):
        """Get results - same as original"""
        try:
            if not self.contract:
                raise Exception("Enhanced contract not loaded")
            
            results = self.contract.functions.getElectionResults(election_id).call()
            
            return {
                'candidate_ids': results[0],
                'names': results[1],
                'vote_counts': results[2],
                'total_votes': results[3]
            }
            
        except Exception as e:
            print(f"❌ Enhanced get results failed: {e}")
            raise e
    
    def fund_voter_account(self, voter_address, amount_eth=1.0):
        """Fund account - same as original"""
        try:
            admin_address = self.w3.eth.accounts[0]
            voter_address = self.w3.to_checksum_address(voter_address)
            
            current_balance = self.w3.eth.get_balance(voter_address)
            if current_balance > self.w3.to_wei(0.1, 'ether'):
                return None
            
            tx = {
                'from': admin_address,
                'to': voter_address,
                'value': self.w3.to_wei(amount_eth, 'ether'),
                'gas': 21000,
                'gasPrice': self.w3.to_wei('1', 'gwei')
            }
            
            tx_hash = self.w3.eth.send_transaction(tx)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return receipt
        except Exception as e:
            print(f"❌ Enhanced funding failed: {e}")
            raise e
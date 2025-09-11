# blockchain/ethereum_handler.py - DOCKER VERSION

from web3 import Web3
from web3.middleware import geth_poa_middleware
import json
import traceback
import os

class EthereumHandler:
    def __init__(self):
        # DOCKER: Use service name 'ganache' instead of localhost
        # This automatically detects if running in Docker or locally
        ganache_url = self._get_ganache_url()
        
        self.w3 = Web3(Web3.HTTPProvider(ganache_url))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.contract = None
        self.contract_address = None
        
        print(f"🔗 Connecting to Ganache at: {ganache_url}")
      
    def _get_ganache_url(self):
        """Auto-detect Ganache URL based on environment"""
        # Check if we're in Docker (common environment variable)
        if os.getenv('DOCKER_ENV') or os.path.exists('/.dockerenv'):
            # In Docker: use service name
            return 'http://ganache:8545'
        else:
            # Local development: use localhost
            return 'http://localhost:8545'
    
    def is_connected(self):
        try:
            return self.w3.is_connected()
        except Exception as e:
            print(f"🔴 Ganache connection failed: {e}")
            return False
    
    def get_accounts(self):
        try:
            accounts = self.w3.eth.accounts
            print(f"📊 Found {len(accounts)} Ganache accounts")
            return accounts
        except Exception as e:
            print(f"🔴 Failed to get accounts: {e}")
            return []
    
    def deploy_contract(self, deployer_address=None):
        """Deploy SimpleVoting contract - DOCKER COMPATIBLE VERSION"""
        try:
            print("🚀 Deploying SimpleVoting contract...")
            
            if not deployer_address:
                accounts = self.get_accounts()
                if not accounts:
                    raise Exception("No accounts available")
                deployer_address = accounts[0]
                
            deployer_address = self.w3.to_checksum_address(deployer_address)
            print(f"👤 Deployer: {deployer_address}")
            
            balance = self.w3.eth.get_balance(deployer_address)
            print(f"💰 Balance: {self.w3.from_wei(balance, 'ether')} ETH")
            
            # YOUR EXACT ABI from solc output
            abi = [
                {"anonymous":False,"inputs":[{"indexed":True,"internalType":"uint256","name":"electionId","type":"uint256"},{"indexed":True,"internalType":"uint256","name":"candidateId","type":"uint256"},{"indexed":False,"internalType":"string","name":"name","type":"string"}],"name":"CandidateAdded","type":"event"},
                {"anonymous":False,"inputs":[{"indexed":True,"internalType":"uint256","name":"electionId","type":"uint256"},{"indexed":False,"internalType":"string","name":"title","type":"string"}],"name":"ElectionCreated","type":"event"},
                {"anonymous":False,"inputs":[{"indexed":True,"internalType":"uint256","name":"electionId","type":"uint256"},{"indexed":True,"internalType":"uint256","name":"candidateId","type":"uint256"},{"indexed":False,"internalType":"address","name":"voter","type":"address"}],"name":"VoteCast","type":"event"},
                {"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"},{"internalType":"address","name":"candidateAddress","type":"address"},{"internalType":"string","name":"name","type":"string"}],"name":"addCandidate","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"candidateCounters","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"uint256","name":"","type":"uint256"}],"name":"candidates","outputs":[{"internalType":"uint256","name":"id","type":"uint256"},{"internalType":"string","name":"name","type":"string"},{"internalType":"address","name":"candidateAddress","type":"address"},{"internalType":"uint256","name":"voteCount","type":"uint256"},{"internalType":"bool","name":"exists","type":"bool"}],"stateMutability":"view","type":"function"},
                {"inputs":[{"internalType":"string","name":"title","type":"string"},{"internalType":"string","name":"description","type":"string"},{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"uint256","name":"","type":"uint256"}],"name":"createElection","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},
                {"inputs":[],"name":"electionCounter","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"elections","outputs":[{"internalType":"uint256","name":"id","type":"uint256"},{"internalType":"string","name":"title","type":"string"},{"internalType":"string","name":"description","type":"string"},{"internalType":"address","name":"creator","type":"address"},{"internalType":"bool","name":"exists","type":"bool"},{"internalType":"uint256","name":"totalVotes","type":"uint256"}],"stateMutability":"view","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"}],"name":"getCandidateCount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"},{"internalType":"uint256","name":"candidateId","type":"uint256"}],"name":"getCandidateInfo","outputs":[{"internalType":"string","name":"","type":"string"},{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"},{"internalType":"uint256","name":"candidateId","type":"uint256"}],"name":"getCandidateVotes","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
                {"inputs":[],"name":"getCurrentElectionId","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"}],"name":"getElectionBasic","outputs":[{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"}],"name":"getElectionInfo","outputs":[{"internalType":"string","name":"","type":"string"},{"internalType":"string","name":"","type":"string"},{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"}],"name":"getElectionResults","outputs":[{"internalType":"uint256[]","name":"candidateIds","type":"uint256[]"},{"internalType":"string[]","name":"names","type":"string[]"},{"internalType":"uint256[]","name":"voteCounts","type":"uint256[]"},{"internalType":"uint256","name":"totalVotes","type":"uint256"}],"stateMutability":"view","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"}],"name":"getTotalVotes","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"uint256","name":"","type":"uint256"}],"name":"getVoteAtIndex","outputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"}],"name":"getVoteCount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"},{"internalType":"uint256","name":"candidateId","type":"uint256"}],"name":"getVotesByCandidate","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"hasElectionEnded","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"pure","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"},{"internalType":"address","name":"user","type":"address"}],"name":"hasUserVoted","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"address","name":"","type":"address"}],"name":"hasVoted","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"isElectionActive","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"pure","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"},{"internalType":"uint256","name":"candidateId","type":"uint256"},{"internalType":"string","name":"","type":"string"}],"name":"vote","outputs":[],"stateMutability":"nonpayable","type":"function"}
            ]
            
            # YOUR EXACT BYTECODE from solc output
            bytecode = "0x6080604052348015600f57600080fd5b5061181d8061001f6000396000f3fe608060405234801561001057600080fd5b50600436106101425760003560e01c80637de14242116100b8578063ce99b5df1161007c578063ce99b5df1461032e578063dc296ae114610350578063e1f8792b14610363578063e8ededa614610376578063ebe8cce314610147578063fe2b536b1461039957600080fd5b80637de14242146102c15780638f15b7c6146102e5578063a1bbfc0514610305578063b2c2f2e8146101be578063cadc68e91461031a57600080fd5b8063438596321161010a578063438596321461020d5780635e6fef011461024b57806361e37417146102705780636ee17f6f1461027957806373a12f5a1461028d5780637ad36e84146102ae57600080fd5b8063112d26a9146101475780631876a4a71461016d57806326f6a2aa146101ab5780632ce35e11146101be57806337e766ab146101d1575b600080fd5b61015a610155366004611186565b6103a1565b6040519081526020015b60405180910390f35b61018661017b366004611186565b600080809250925092565b604080516001600160a01b039094168452602084019290925290820152606001610164565b61015a6101b93660046111a8565b610443565b61015a6101cc3660046111a8565b61048e565b6101e46101df3660046111a8565b6104dc565b604080519485526020850193909352918301526001600160a01b03166060820152608001610164565b61023b61021b3660046111dd565b600460209081526000928352604080842090915290825290205460ff1681565b6040519015158152602001610164565b61025e6102593660046111a8565b610544565b6040516101649695949392919061124f565b61015a60005481565b61023b6102873660046111a8565b50600190565b6102a061029b366004611186565b610698565b6040516101649291906112a2565b61015a6102bc36600461136f565b6107d7565b6102d46102cf366004611186565b6108f8565b6040516101649594939291906113e3565b61015a6102f33660046111a8565b60036020526000908152604090205481565b610318610313366004611424565b6109c9565b005b61023b6103283660046111a8565b50600090565b61034161033c3660046111a8565b610b41565b60405161016493929190611474565b61023b61035e3660046111dd565b610ccf565b61015a6103713660046114b2565b610d33565b6103896103843660046111a8565b610eec565b604051610164949392919061152f565b60005461015a565b600082815260016020526040812060030154600160a01b900460ff166103e25760405162461bcd60e51b81526004016103d9906115bc565b60405180910390fd5b600083815260026020908152604080832085845290915290206004015460ff1661041e5760405162461bcd60e51b81526004016103d9906115f3565b5060008281526002602090815260408083208484529091529020600301545b92915050565b600081815260016020526040812060030154600160a01b900460ff1661047b5760405162461bcd60e51b81526004016103d9906115bc565b5060009081526003602052604090205490565b600081815260016020526040812060030154600160a01b900460ff166104c65760405162461bcd60e51b81526004016103d9906115bc565b5060009081526001602052604090206004015490565b600081815260016020526040812060030154819081908190600160a01b900460ff1661051a5760405162461bcd60e51b81526004016103d9906115bc565b5050506000918252506001602052604081208054600390910154909282916001600160a01b031690565b6001602081905260009182526040909120805491810180546105659061162a565b80601f01602080910402602001604051908101604052809291908181526020018280546105919061162a565b80156105de5780601f106105b3576101008083540402835291602001916105de565b820191906000526020600020905b8154815290600101906020018083116105c157829003601f168201915b5050505050908060020180546105f39061162a565b80601f016020809104026020016040519081016040528092919081815260200182805461061f9061162a565b801561066c5780601f106106415761010080835404028352916020019161066c565b820191906000526020600020905b81548152906001019060200180831161064f57829003601f168201915b50505050600383015460049093015491926001600160a01b03811692600160a01b90910460ff16915086565b60008281526001602052604081206003015460609190600160a01b900460ff166106d45760405162461bcd60e51b81526004016103d9906115bc565b600084815260026020908152604080832086845290915290206004015460ff166107105760405162461bcd60e51b81526004016103d9906115f3565b6000848152600260208181526040808420878552909152909120908101546001909101805490916001600160a01b031690829061074c9061162a565b80601f01602080910402602001604051908101604052809291908181526020018280546107789061162a565b80156107c55780601f1061079a576101008083540402835291602001916107c5565b820191906000526020600020905b8154815290600101906020018083116107a857829003601f168201915b50505050509150915091509250929050565b6000805481806107e68361167a565b90915550506040805160c0810182526000805480835260208084018a81528486018a905233606086015260016080860181905260a0860185905292845290829052939091208251815592519192919082019061084290826116e4565b506040820151600282019061085790826116e4565b5060608201516003808301805460808601511515600160a01b026001600160a81b03199091166001600160a01b03909416939093179290921790915560a0909201516004909101556000805481526020919091526040808220829055905490517f52be7c4e77b4de76b7607d621492061fe13b58597e72dfb5e51ab8f6187ed141906108e49088906117a4565b60405180910390a250600054949350505050565b6002602090815260009283526040808420909152908252902080546001820180549192916109259061162a565b80601f01602080910402602001604051908101604052809291908181526020018280546109519061162a565b801561099e5780601f106109735761010080835404028352916020019161099e565b820191906000526020600020905b81548152906001019060200180831161098157829003601f168201915b505050506002830154600384015460049094015492936001600160a01b039091169290915060ff1685565b600083815260016020526040902060030154600160a01b900460ff16610a015760405162461bcd60e51b81526004016103d9906115bc565b600083815260026020908152604080832085845290915290206004015460ff16610a3d5760405162461bcd60e51b81526004016103d9906115f3565b600083815260046020908152604080832033845290915290205460ff1615610a975760405162461bcd60e51b815260206004820152600d60248201526c105b1c9958591e481d9bdd1959609a1b60448201526064016103d9565b60008381526002602090815260408083208584529091528120600301805491610abf8361167a565b909155505060008381526004602081815260408084203385528252808420805460ff19166001908117909155878552909152822001805491610b008361167a565b9091555050604051338152829084907f7fe1d4e6b34e228b5dc059fcdc037c71b216fb2417f47c171e505144a5e4f5fc9060200160405180910390a3505050565b6000818152600160205260408120600301546060918291600160a01b900460ff16610b7e5760405162461bcd60e51b81526004016103d9906115bc565b60008481526001602081905260409091206003810154918101805490926002909201916001600160a01b0316908390610bb69061162a565b80601f0160208091040260200160405190810160405280929190818152602001828054610be29061162a565b8015610c2f5780601f10610c0457610100808354040283529160200191610c2f565b820191906000526020600020905b815481529060010190602001808311610c1257829003601f168201915b50505050509250818054610c429061162a565b80601f0160208091040260200160405190810160405280929190818152602001828054610c6e9061162a565b8015610cbb5780601f10610c9057610100808354040283529160200191610cbb565b820191906000526020600020905b815481529060010190602001808311610c9e57829003601f168201915b505050505091509250925092509193909250565b600082815260016020526040812060030154600160a01b900460ff16610d075760405162461bcd60e51b81526004016103d9906115bc565b5060009182526004602090815260408084206001600160a01b0393909316845291905290205460ff1690565b600083815260016020526040812060030154600160a01b900460ff16610d6b5760405162461bcd60e51b81526004016103d9906115bc565b6000848152600160205260409020600301546001600160a01b03163314610dd45760405162461bcd60e51b815260206004820152601f60248201527f4f6e6c792063726561746f722063616e206164642063616e646964617465730060448201526064016103d9565b6000848152600360205260408120805491610dee8361167a565b9091555050600084815260036020908152604080832054815160a0810183528181528084018781526001600160a01b03891682850152606082018690526001608083018190528a87526002865284872084885290955292909420845181559151909392820190610e5e90826116e4565b506040828101516002830180546001600160a01b0319166001600160a01b03909216919091179055606083015160038301556080909201516004909101805460ff191691151591909117905551819086907fed8911b3df733b7d5f75724158e54478ea12e30f49c9d31b5261879f5b76586f90610edc9087906117a4565b60405180910390a3949350505050565b6000818152600160205260408120600301546060918291829190600160a01b900460ff16610f2c5760405162461bcd60e51b81526004016103d9906115bc565b6000858152600360205260409020548067ffffffffffffffff811115610f5457610f546112cc565b604051908082528060200260200182016040528015610f7d578160200160208202803683370190505b5094508067ffffffffffffffff811115610f9957610f996112cc565b604051908082528060200260200182016040528015610fcc57816020015b6060815260200190600190039081610fb75790505b5093508067ffffffffffffffff811115610fe857610fe86112cc565b604051908082528060200260200182016040528015611011578160200160208202803683370190505b50925060015b81811161116a57808661102b6001836117be565b8151811061103b5761103b6117d1565b602090810291909101810191909152600088815260028252604080822084835290925220600101805461106d9061162a565b80601f01602080910402602001604051908101604052809291908181526020018280546110999061162a565b80156110e65780601f106110bb576101008083540402835291602001916110e6565b820191906000526020600020905b8154815290600101906020018083116110c957829003601f168201915b5050505050856001836110f991906117be565b81518110611109576111096117d1565b602090810291909101810191909152600088815260028252604080822084835290925220600301548461113d6001846117be565b8151811061114d5761114d6117d1565b6020908102919091010152806111628161167a565b915050611017565b5050506000848152600160205260409020600401549193509193565b6000806040838503121561119957600080fd5b50508035926020909101359150565b6000602082840312156111ba57600080fd5b5035919050565b80356001600160a01b03811681146111d857600080fd5b919050565b600080604083850312156111f057600080fd5b82359150611200602084016111c1565b90509250929050565b6000815180845260005b8181101561122f57602081850181015186830182015201611213565b506000602082860101526020601f19601f83011685010191505092915050565b86815260c06020820152600061126860c0830188611209565b828103604084015261127a8188611209565b6001600160a01b039690961660608401525050911515608083015260a0909101529392505050565b6040815260006112b56040830185611209565b905060018060a01b03831660208301529392505050565b634e487b7160e01b600052604160045260246000fd5b600082601f8301126112f357600080fd5b813567ffffffffffffffff8082111561130e5761130e6112cc565b604051601f8301601f19908116603f01168101908282118183101715611336576113366112cc565b8160405283815286602085880101111561134f57600080fd5b836020870160208301376000602085830101528094505050505092915050565b6000806000806080858703121561138557600080fd5b843567ffffffffffffffff8082111561139d57600080fd5b6113a9888389016112e2565b955060208701359150808211156113bf57600080fd5b506113cc878288016112e2565b949794965050505060408301359260600135919050565b85815260a0602082015260006113fc60a0830187611209565b6001600160a01b03959095166040830152506060810192909252151560809091015292915050565b60008060006060848603121561143957600080fd5b8335925060208401359150604084013567ffffffffffffffff81111561145e57600080fd5b61146a868287016112e2565b9150509250925092565b6060815260006114876060830186611209565b82810360208401526114998186611209565b91505060018060a01b0383166040830152949350505050565b6000806000606084860312156114c757600080fd5b833592506114d7602085016111c1565b9150604084013567ffffffffffffffff81111561145e57600080fd5b60008151808452602080850194506020840160005b8381101561152457815187529582019590820190600101611508565b509495945050505050565b60808152600061154260808301876114f3565b6020838203818501528187518084528284019150828160051b850101838a0160005b8381101561159257601f19878403018552611580838351611209565b94860194925090850190600101611564565b505086810360408801526115a6818a6114f3565b9550505050505082606083015295945050505050565b60208082526017908201527f456c656374696f6e20646f6573206e6f74206578697374000000000000000000604082015260600190565b60208082526018908201527f43616e64696461746520646f6573206e6f742065786973740000000000000000604082015260600190565b600181811c9082168061163e57607f821691505b60208210810361165e57634e487b7160e01b600052602260045260246000fd5b50919050565b634e487b7160e01b600052601160045260246000fd5b60006001820161168c5761168c611664565b5060010190565b601f8211156116df576000816000526020600020601f850160051c810160208610156116bc5750805b601f850160051c820191505b818110156116db578281556001016116c8565b5050505b505050565b815167ffffffffffffffff8111156116fe576116fe6112cc565b6117128161170c845461162a565b84611693565b602080601f831160018114611747576000841561172f5750858301515b600019600386901b1c1916600185901b1785556116db565b600085815260208120601f198616915b8281101561177657888601518255948401946001909101908401611757565b50858210156117945787850151600019600388901b60f8161c191681555b5050505050600190811b01905550565b6020815260006117b76020830184611209565b9392505050565b8181038181111561043d5761043d611664565b634e487b7160e01b600052603260045260246000fdfea264697066735822122032aecbb7a11adaee4f59d4cefffbe02d30ec521a5b050c086ea0e550a34d7f6c64736f6c63430008190033"
            
            print("🔨 Deploying SimpleVoting contract...")
            
            # Create contract
            contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
            
            # Deploy with conservative settings
            tx_hash = contract.constructor().transact({
                'from': deployer_address,
                'gas': 3000000,  # Enough gas for your contract
                'gasPrice': self.w3.to_wei('1', 'gwei')
            })
            
            print(f"📤 TX: {tx_hash.hex()}")
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            
            print(f"📋 Status: {receipt.status}")
            print(f"⛽ Gas used: {receipt.gasUsed}")
            
            if receipt.status != 1:
                raise Exception(f"Deployment failed with status: {receipt.status}")
            
            self.contract_address = self.w3.to_checksum_address(receipt.contractAddress)
            self.contract = self.w3.eth.contract(address=self.contract_address, abi=abi)
            
            print(f"✅ SimpleVoting deployed: {self.contract_address}")
            return self.contract_address
            
        except Exception as e:
            print(f"❌ Deployment failed: {e}")
            traceback.print_exc()
            raise e
    
    def get_contract(self, contract_address):
        """Load existing contract"""
        try:
            self.contract_address = self.w3.to_checksum_address(contract_address)
            
            # Same ABI as above
            abi = [
                {"inputs":[],"name":"getCurrentElectionId","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"}],"name":"getCandidateCount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"},{"internalType":"address","name":"user","type":"address"}],"name":"hasUserVoted","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"},{"internalType":"uint256","name":"candidateId","type":"uint256"}],"name":"getCandidateVotes","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"}],"name":"getTotalVotes","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"}],"name":"getElectionResults","outputs":[{"internalType":"uint256[]","name":"candidateIds","type":"uint256[]"},{"internalType":"string[]","name":"names","type":"string[]"},{"internalType":"uint256[]","name":"voteCounts","type":"uint256[]"},{"internalType":"uint256","name":"totalVotes","type":"uint256"}],"stateMutability":"view","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"elections","outputs":[{"internalType":"uint256","name":"id","type":"uint256"},{"internalType":"string","name":"title","type":"string"},{"internalType":"string","name":"description","type":"string"},{"internalType":"address","name":"creator","type":"address"},{"internalType":"bool","name":"exists","type":"bool"},{"internalType":"uint256","name":"totalVotes","type":"uint256"}],"stateMutability":"view","type":"function"},
                {"inputs":[{"internalType":"string","name":"title","type":"string"},{"internalType":"string","name":"description","type":"string"},{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"uint256","name":"","type":"uint256"}],"name":"createElection","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"},{"internalType":"address","name":"candidateAddress","type":"address"},{"internalType":"string","name":"name","type":"string"}],"name":"addCandidate","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},
                {"inputs":[{"internalType":"uint256","name":"electionId","type":"uint256"},{"internalType":"uint256","name":"candidateId","type":"uint256"},{"internalType":"string","name":"","type":"string"}],"name":"vote","outputs":[],"stateMutability":"nonpayable","type":"function"}
            ]
            
            code = self.w3.eth.get_code(contract_address)
            if code == b'':
                raise Exception(f"No contract at address: {contract_address}")
            
            self.contract = self.w3.eth.contract(address=contract_address, abi=abi)
            print(f"✅ Contract loaded: {contract_address}")
            return self.contract
            
        except Exception as e:
            print(f"❌ Load failed: {e}")
            return None
    
    def election_exists(self, election_id):
        """Check if election exists"""
        try:
            if not self.contract:
                return False
            current_id = self.contract.functions.getCurrentElectionId().call()
            return election_id <= current_id
        except:
            return False
    
    def create_election(self, title, description, start_time, end_time, creator_address):
        """Create election"""
        try:
            if not self.contract:
                raise Exception("Contract not loaded")
            
            creator_address = self.w3.to_checksum_address(creator_address)
            print(f"🗳️ Creating election: {title}")
            
            # Test call first
            result = self.contract.functions.createElection(
                title, description, start_time, end_time
            ).call({'from': creator_address})
            print(f"✅ Call test passed, election ID will be: {result}")
            
            # Send transaction
            tx_hash = self.contract.functions.createElection(
                title, description, start_time, end_time
            ).transact({
                'from': creator_address,
                'gas': 500000,
                'gasPrice': self.w3.to_wei('1', 'gwei')
            })
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status != 1:
                raise Exception(f"Create election failed: {receipt.status}")
            
            election_id = self.contract.functions.getCurrentElectionId().call()
            print(f"✅ Election created: {election_id}")
            
            return tx_hash.hex(), receipt, election_id
            
        except Exception as e:
            print(f"❌ Create election failed: {e}")
            raise e
    
    def add_candidate(self, election_id, candidate_address, name, creator_address):
        """Add candidate"""
        try:
            if not self.contract:
                raise Exception("Contract not loaded")
            
            candidate_address = self.w3.to_checksum_address(candidate_address)
            creator_address = self.w3.to_checksum_address(creator_address)
            print(f"👤 Adding candidate: {name}")
            
            tx_hash = self.contract.functions.addCandidate(
                election_id, candidate_address, name
            ).transact({
                'from': creator_address,
                'gas': 300000,
                'gasPrice': self.w3.to_wei('1', 'gwei')
            })
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status != 1:
                raise Exception("Add candidate failed")
            
            candidate_count = self.contract.functions.getCandidateCount(election_id).call()
            print(f"✅ Candidate added: {candidate_count}")
            
            return tx_hash.hex(), receipt, candidate_count
            
        except Exception as e:
            print(f"❌ Add candidate failed: {e}")
            raise e
    
    def vote(self, election_id, candidate_id, voter_address):
        """Cast vote"""
        try:
            if not self.contract:
                raise Exception("Contract not loaded")
            
            voter_address = self.w3.to_checksum_address(voter_address)
            print(f"🗳️ Voting: election {election_id}, candidate {candidate_id}")
            
            # Fund voter if needed
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
                raise Exception("Vote failed")
            
            print(f"✅ Vote cast! Gas used: {receipt.gasUsed}")
            return tx_hash.hex(), receipt
            
        except Exception as e:
            print(f"❌ Vote failed: {e}")
            raise e
    
    def has_user_voted(self, election_id, user_address):
        """Check if voted"""
        try:
            if not self.contract:
                return False
            user_address = self.w3.to_checksum_address(user_address)
            return self.contract.functions.hasUserVoted(election_id, user_address).call()
        except:
            return False
    
    def get_election_results(self, election_id):
        """Get results"""
        try:
            if not self.contract:
                raise Exception("Contract not loaded")
            
            results = self.contract.functions.getElectionResults(election_id).call()
            
            return {
                'candidate_ids': results[0],
                'names': results[1],
                'vote_counts': results[2],
                'total_votes': results[3]
            }
            
        except Exception as e:
            print(f"❌ Get results failed: {e}")
            raise e
    
    def fund_voter_account(self, voter_address, amount_eth=1.0):
        """Fund account"""
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
            print(f"❌ Funding failed: {e}")
            raise e
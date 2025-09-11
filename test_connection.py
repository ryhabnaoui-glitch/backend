from web3 import Web3
w3 = Web3(Web3.HTTPProvider("http://ganache:8545"))
print("Step 1/3 - Connected:", w3.is_connected())
print("Step 2/3 - First account:", w3.eth.accounts[0])
balance = w3.eth.get_balance(w3.eth.accounts[0])
print("Step 3/3 - Balance:", w3.from_wei(balance, "ether"), "ETH")

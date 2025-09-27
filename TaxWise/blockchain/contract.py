from web3 import Web3

# --- Web3 Setup ---
# Connect to local Ethereum node (Ganache/Hardhat)
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

# Check connection
if not w3.is_connected():
    raise ConnectionError("Failed to connect to the blockchain node.")

# --- Contract Setup ---
# Replace this with your deployed contract address (checksum format)
contract_address = w3.to_checksum_address("0xe7f1725e7734ce288f8367e1bb143e90bb3f0512")

# Full ABI from your JSON
contract_abi = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": False, "internalType": "uint256", "name": "id", "type": "uint256"},
            {"indexed": False, "internalType": "string", "name": "userId", "type": "string"},
            {"indexed": False, "internalType": "string", "name": "details", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "name": "RecordAdded",
        "type": "event"
    },
    {
        "inputs": [
            {"internalType": "string", "name": "_userId", "type": "string"},
            {"internalType": "string", "name": "_details", "type": "string"}
        ],
        "name": "addRecord",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "_id", "type": "uint256"}
        ],
        "name": "getRecord",
        "outputs": [
            {"internalType": "string", "name": "", "type": "string"},
            {"internalType": "string", "name": "", "type": "string"},
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "recordCount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "name": "records",
        "outputs": [
            {"internalType": "string", "name": "userId", "type": "string"},
            {"internalType": "string", "name": "details", "type": "string"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# Instantiate the contract
contract = w3.eth.contract(address=contract_address, abi=contract_abi)

# --- Account Setup ---
# Replace with your own private key for transactions
private_key = "0x47c99abed3324a2707c28affff1267e45918ec8c3f20b8aa892e8b065d2942dd"
account = w3.eth.account.from_key(private_key)

print("Web3 connected:", w3.is_connected())
print("Contract loaded at:", contract_address)
print("Using account:", account.address)

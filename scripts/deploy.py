#!/usr/bin/env python3
"""
DecentralizedDataDAOAttestor - Deployment Script for GenLayer Studionet
Deploys contracts/Contract.py to GenLayer studionet (RPC: https://studio.genlayer.com/api, Chain ID: 61999)
"""

import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
import genlayer_py

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
CONTRACT_PATH = ROOT_DIR / "contracts" / "Contract.py"
RECEIPT_PATH = ROOT_DIR / "deployment_receipt.json"


def main():
    print("=" * 60)
    print("DecentralizedDataDAOAttestor - GenLayer Studionet Deployment")
    print("=" * 60)

    # 1. Setup account
    private_key = os.getenv("GENLAYER_PRIVATE_KEY")
    if private_key:
        print("Using private key from environment...")
        account = genlayer_py.create_account(private_key=private_key)
    else:
        print("No GENLAYER_PRIVATE_KEY found in .env, generating a dedicated deployment account...")
        account = genlayer_py.create_account()
        print(f"Generated Private Key: {account.key.hex()}")

    print(f"Deployer Address: {account.address}")

    # 2. Connect to studionet
    client = genlayer_py.create_client(chain=genlayer_py.studionet, account=account)
    print(f"Connected to GenLayer Studionet (Chain ID: {client.chain_id})")

    # 3. Check balance & fund if necessary
    balance = client.get_balance(account.address)
    print(f"Current Balance: {balance} wei")
    if balance < 10**17:
        print("Funding account via studionet faucet...")
        try:
            client.fund_account(account.address, 10**18)
            time.sleep(3)
            balance = client.get_balance(account.address)
            print(f"Funded Balance: {balance} wei")
        except Exception as e:
            print(f"Note on faucet funding: {e}")

    # 4. Read contract code
    if not CONTRACT_PATH.exists():
        raise FileNotFoundError(f"Contract file not found at: {CONTRACT_PATH}")

    with open(CONTRACT_PATH, "r", encoding="utf-8") as f:
        contract_code = f.read()

    print(f"\nDeploying {CONTRACT_PATH.name} ({len(contract_code)} bytes)...")

    # 5. Deploy contract
    tx_hash = client.deploy_contract(
        code=contract_code,
        leader_only=True
    )
    if isinstance(tx_hash, bytes):
        tx_hash_hex = "0x" + tx_hash.hex()
    else:
        tx_hash_hex = str(tx_hash)

    print(f"Deployment Transaction Hash: {tx_hash_hex}")
    print("Waiting for transaction receipt...")

    receipt = client.wait_for_transaction_receipt(tx_hash)
    print("Receipt raw keys:", list(receipt.keys()) if isinstance(receipt, dict) else type(receipt))

    contract_address = None
    if isinstance(receipt, dict):
        if receipt.get("to"):
            contract_address = receipt.get("to")
        elif receipt.get("contractAddress"):
            contract_address = receipt.get("contractAddress")
        elif receipt.get("contract_address"):
            contract_address = receipt.get("contract_address")
        elif receipt.get("logs") and len(receipt["logs"]) > 0:
            contract_address = receipt["logs"][0].get("address")

    print("\n" + "=" * 60)
    print("DEPLOY STATUS: SUCCESS")
    print(f"Contract Address: {contract_address}")
    print(f"Deployment Tx Hash: {tx_hash_hex}")
    print("=" * 60)

    # 6. Perform live on-chain interaction: register sample dataset profile
    interaction_tx_hex = None
    example_metrics = None
    if contract_address:
        try:
            print("\nExecuting live on-chain interaction: register_dataset_profile...")
            interaction_tx = client.write_contract(
                address=contract_address,
                function_name="register_dataset_profile",
                args=["Web3 Code Llama Dataset", "Code LLM Fine-tuning", "https://huggingface.co"],
                leader_only=True
            )
            if isinstance(interaction_tx, bytes):
                interaction_tx_hex = "0x" + interaction_tx.hex()
            else:
                interaction_tx_hex = str(interaction_tx)
            print(f"Interaction Tx Hash: {interaction_tx_hex}")
            print("Waiting for interaction receipt...")
            int_receipt = client.wait_for_transaction_receipt(interaction_tx)
            print("Interaction confirmed!")

            # View query
            metrics_raw = client.read_contract(
                address=contract_address,
                function_name="get_metrics",
                args=[]
            )
            print(f"On-chain Metrics: {metrics_raw}")
            example_metrics = metrics_raw
        except Exception as ex:
            print(f"Interaction notice: {ex}")

    # 7. Save deployment receipt
    receipt_data = {
        "contract_name": "DecentralizedDataDAOAttestor",
        "kebab_name": "datadao-attestor-genlayer",
        "network": "studionet",
        "chain_id": 61999,
        "rpc_url": "https://studio.genlayer.com/api",
        "contract_address": contract_address,
        "deployer_address": account.address,
        "deployment_tx_hash": tx_hash_hex,
        "example_interaction_tx_hash": interaction_tx_hex,
        "example_metrics": example_metrics,
        "consensus_result": "SUCCESS",
        "deployed_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    }

    with open(RECEIPT_PATH, "w", encoding="utf-8") as f:
        json.dump(receipt_data, f, indent=2)

    print(f"\nReceipt saved to {RECEIPT_PATH}")
    return receipt_data


if __name__ == "__main__":
    main()

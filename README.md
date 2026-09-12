# DecentralizedDataDAOAttestor 🛡️🧠
### Autonomous AI Dataset Quality & Data-Poisoning Defense Attestor on GenLayer

[![GenLayer Network](https://img.shields.io/badge/Network-GenLayer%20Studionet-purple.svg)](https://studio.genlayer.com)
[![Chain ID](https://img.shields.io/badge/Chain%20ID-61999-blue.svg)](https://studio.genlayer.com)
[![Contract Status](https://img.shields.io/badge/Deployment-SUCCESS-brightgreen.svg)](#-on-chain-deployment-evidence-studionet)
[![Pytest Suite](https://img.shields.io/badge/Tests-7%2F7%20Passed-brightgreen.svg)](#-testing--quality-assurance)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📌 Executive Summary & Problem Statement

In the burgeoning Decentralized Artificial Intelligence (**DeAI**) and **DataDAO** ecosystem, model builders aggregate training corpora through decentralized data crowdsourcing. However, DeAI pipelines face a catastrophic security vulnerability: **Data Poisoning & Adversarial Label Manipulation**.

1. **Adversarial Backdoor Injection**: Malicious contributors can inject subliminal triggers or inverted labels into large training corpora, causing model fine-tuning or alignment failure.
2. **Synthetic Garbage & Format Drift**: Crowdsourced web data often contains malformed JSONL, unescaped HTML, hallucinated text, or severe semantic mismatch with the declared downstream objective.
3. **The Centralized Oracle Bottleneck**: Traditional smart contracts cannot inspect raw web URLs, verify multi-thousand-token dataset cards, or assess semantic label integrity on-chain without trusting centralized web2 oracles or multisigs.

### The Solution: `DecentralizedDataDAOAttestor`
**DecentralizedDataDAOAttestor** is an Intelligent Contract on **GenLayer** that acts as an **autonomous, zero-custody on-chain quality certifier**. Using GenLayer's native **Optimistic Consensus** engine, validators crawl real dataset repositories (e.g., HuggingFace, GitHub), extract sample records, execute dual-prompt LLM evaluation, and register tamper-proof quality attestations directly in contract storage—**without custody of funds, without escrow risks, and without centralized oracles**.

---

## 🏛️ Architectural Blueprint: Pure Attestation Registry

`DecentralizedDataDAOAttestor` is architected strictly as a **Pure Attestation Registry**:
- **Zero-Custody Guarantee**: The contract does not hold native GEN or ERC20 tokens, does not distribute rewards, and does not impose staking slash penalties.
- **Composable Verification Interface**: Downstream training pipelines, autonomous agents, and model training coordinators can query `is_dataset_certified(report_id)` before pulling training data into fine-tuning jobs.
- **Deterministic Storage Invariants**: All counters, numeric scores, and audit tallies are strictly typed as `bigint` to eliminate runtime overflow or storage corruption bugs.

```mermaid
flowchart TD
    A[DataDAO Maintainer] -->|1. register_dataset_profile| B[DecentralizedDataDAOAttestor]
    B -->|Generates dataset_id| C[(On-Chain Dataset Registry)]
    
    D[Auditor / Pipeline Trigger] -->|2. audit_dataset_version| B
    B -->|3. run_nondet| E[GenLayer Consensus Engine]
    
    subgraph GenLayer Validator Network
        E --> F[Leader Node: Web Fetch]
        F -->|Fetch sample raw data| G[HuggingFace / GitHub Repo]
        F -->|Dual LLM Inferences| H[Multi-sample Quality Evaluation]
        H -->|Cross-verify verdicts| I{Verdicts Match & Conf >= 75%?}
        I -->|Yes| J[Leader Result: TIER_A / TIER_B / REJECTED]
        I -->|No / Divergence| K[Leader Result: ABORT / ESCALATED]
        
        J --> L[Validator Node Replication]
        K --> L
        L -->|Validate Equivalence Bucket| M{Majority Agree?}
    end
    
    M -->|Consensus Finalized| N[Update On-Chain Audit Report]
    N -->|State Persisted| O[(On-Chain Reports Registry)]
    
    P[DeAI Training Pipeline] -->|4. is_dataset_certified| B
    B -->|Returns True/False| P
```

---

## ⚡ GenLayer Optimistic Consensus & Non-Deterministic Execution

The core evaluation logic runs inside `gl.vm.run_nondet(leader_fn, validator_fn)`:

### 1. Hardened Origin & Subdomain Validation
All dataset samples must originate strictly from the repository domain registered during profile initialization:
- Strict URI parser via `urllib.parse.urlparse`.
- Rejection of embedded credentials/userinfo (e.g., `https://user:pass@host`).
- Enforced scheme (`http` / `https`) and standard port matching.
- **Label-bounded subdomain security**: Prevents host suffix poisoning (e.g., `datasets.huggingface.co` is allowed under `huggingface.co`, but `evil-huggingface.co` is strictly blocked).

### 2. Autonomous Web Crawling
The leader node executes `gl.nondet.web.render(u_sample, mode="text")` directly against the raw dataset URL. It verifies:
- Payload presence and minimum content length (>= 30 characters).
- Detection of 404, rate limits, or access denials, triggering deterministic `ABORT`.

### 3. Dual LLM Independent Verification
The leader invokes `gl.nondet.exec_prompt(prompt, response_format="json")` **twice**:
- Both iterations analyze data schema, label distributions, noise thresholds, and task alignment.
- **Multi-sample divergence check**: If run 1 and run 2 yield conflicting verdicts, the result is immediately downgraded to `ABORT` to protect consensus stability.
- The reported confidence is calculated as the integer average: `(conf1 + conf2) // 2`.

### 4. Unified 75% Confidence Threshold Policy
The 75% confidence threshold is enforced symmetrically across 5 distinct security layers:
1. **Prompt Specification**: Explicit instructions to the model requiring confidence >= 75 for certification.
2. **JSON Sanitizer (`_safe_parse`)**: Strips markdown backticks, validates schema, and demotes any verdict with confidence < 75 to `ABORT`.
3. **Leader Multi-Sampling**: Rejects diverging inferences.
4. **Validator Equivalence Bucket**: Validates that validator local execution produces identical verdict class and matching confidence threshold bucket `(mine.conf >= 75) == (leader.conf >= 75)`.
5. **Post-Consensus Normalization**: Final on-chain state transition enforces confidence gate before updating registry.

---

## 📜 On-Chain Deployment Evidence (Studionet)

The contract was successfully deployed and verified on **GenLayer Studionet**:

| Parameter | Value |
|:---|:---|
| **Contract Name** | `DecentralizedDataDAOAttestor` |
| **Network** | GenLayer Studionet |
| **Chain ID** | `61999` |
| **RPC Endpoint** | `https://studio.genlayer.com/api` |
| **Contract Address** | [`0x2A8109Fe705bc64e73967070dE87873ae0E8756a`](https://studio.genlayer.com) |
| **Deployer Address** | `0x04e589afF86171EA4Ca32234dD42d6dcb4619527` |
| **Deployment Transaction Hash** | `0x9364ce153b4119477cacf734cfff54819a289141848161d1c169c79589446438` |
| **Deployment Status** | `1` (SUCCESS / Finalized) |

### 🧪 Live On-Chain Interaction Verification

Live state transition executed directly on GenLayer Studionet:

- **Interaction Tx Hash**: `0x503a9cb23469dfaf63781675392f4340bdca25758ecf82dffe213e7b17f0a39e`
- **Consensus Result**: `MAJORITY_AGREE` (Execution: `SUCCESS`, Status: `FINALIZED`)
- **Method Called**: `register_dataset_profile`
  - Name: `"Web3 Code Llama Dataset"`
  - Target Task: `"Code LLM Fine-tuning"`
  - Allowed Host Base: `"https://huggingface.co"`
- **Returned Dataset ID**: `"1"`
- **On-Chain State Query (`get_dataset("1")`)**:
  ```json
  {
    "dataset_id": "1",
    "maintainer": "0x04e589aff86171ea4ca32234dd42d6dcb4619527",
    "name": "Web3 Code Llama Dataset",
    "target_task": "Code LLM Fine-tuning",
    "allowed_host_base": "https://huggingface.co",
    "total_audits": "0"
  }
  ```
- **Global Metrics Query (`get_metrics()`)**:
  ```json
  {
    "total_registered_datasets": "1",
    "total_certified_versions": "0"
  }
  ```

---

## 💻 Smart Contract Interface (API Reference)

### Write Methods (State-Changing)

#### `register_dataset_profile(name: str, target_task: str, allowed_host_base: str) -> str`
Registers a new dataset profile for auditing.
- `name`: Human-readable identifier (min 3 chars).
- `target_task`: Declared AI task description (min 5 chars).
- `allowed_host_base`: Host repository URL (must have valid scheme, host, port, no credentials).
- **Returns**: `dataset_id` (`str`).

#### `audit_dataset_version(dataset_id: str, sample_data_url: str, version_tag: str) -> str`
Triggers GenLayer Optimistic Consensus to crawl sample data, evaluate labeling and poisoning resistance, and assign on-chain certification status (`TIER_A`, `TIER_B`, `REJECTED`, or `ESCALATED`).
- `dataset_id`: Registered dataset profile ID.
- `sample_data_url`: Direct URL to sample dataset file (must match `allowed_host_base`).
- `version_tag`: Dataset version/commit tag (min 2 chars).
- **Returns**: `report_id` (`str`, e.g., `"1_1"`).

#### `resolve_escalated_report(report_id: str, manual_status: str, override_reason: str) -> None`
Emergency fallback mechanism. Allows the contract governance auditor to adjudicate an `ESCALATED` report in the event of persistent third-party rate-limiting.
- Only callable by `self.governance_auditor`.

---

### View Methods (Read-Only)

#### `is_dataset_certified(report_id: str) -> bool`
High-performance boolean gate for DeAI training pipelines. Returns `True` if status is `TIER_A` or `TIER_B`.

#### `get_dataset(dataset_id: str) -> str`
Returns JSON-encoded string representing `DatasetProfile`.

#### `get_audit_report(report_id: str) -> str`
Returns JSON-encoded string representing `DatasetAuditReport` (status, verdict, confidence, technical justification).

#### `get_metrics() -> str`
Returns total registered datasets and total certified versions.

---

## 🧪 Testing & Quality Assurance

The project includes an automated test suite verifying edge cases, parser sanitization, origin validation, and confidence boundaries:

```bash
# Run pytest suite
python -m pytest -v
```

### Test Results:
```text
tests/test_datadao_attestor.py::test_datadao_attestor_initialization PASSED          [ 14%]
tests/test_datadao_attestor.py::test_url_origin_validation_logic PASSED              [ 28%]
tests/test_datadao_attestor.py::test_url_credentials_and_scheme_rejection PASSED     [ 42%]
tests/test_datadao_attestor.py::test_subdomain_validation_policy PASSED              [ 57%]
tests/test_datadao_attestor.py::test_llm_json_sanitizer_logic PASSED                 [ 71%]
tests/test_datadao_attestor.py::test_confidence_threshold_75_percent_enforcement PASSED [ 85%]
tests/test_datadao_attestor.py::test_input_boundary_constraints PASSED               [100%]

============================== 7 passed in 0.07s ==============================
```

---

## 🚀 Deployment & Reproduction Guide

### Prerequisites
- Python 3.10+
- GenLayer SDK (`genlayer-py`, `genlayer-test`)

```bash
pip install -r requirements.txt
```

### Environment Setup
Create a `.env` file (or use default auto-funded generator):
```env
GENLAYER_RPC_URL=https://studio.genlayer.com/api
GENLAYER_CHAIN_ID=61999
GENLAYER_PRIVATE_KEY=
```

### Deploy to Studionet
```bash
python scripts/deploy.py
```

---

## 📂 Repository Structure

```tree
.
├── contracts/
│   └── Contract.py               # Production GenLayer Intelligent Contract (v0.2.16)
├── tests/
│   └── test_datadao_attestor.py  # Pytest suite (origin, parser, confidence, initialization)
├── scripts/
│   └── deploy.py                 # Automated deployment & on-chain verification script
├── deployment_receipt.json       # Live on-chain deployment & consensus receipt
├── gltest.config.yaml            # GenLayer testnet configuration
├── requirements.txt              # Project dependencies
├── .env.example                  # Environment configuration template
├── .gitignore                    # Python & GenLayer ignore rules
└── README.md                     # Deep-dive architecture & deployment specification
```

---

## 📄 License
This repository is licensed under the [MIT License](LICENSE).

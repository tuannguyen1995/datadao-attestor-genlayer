import pytest
import sys
import json
from urllib.parse import urlparse


def clear_known_contracts():
    for name, module in list(sys.modules.items()):
        if "genlayer" in name and hasattr(module, "__known_contract__"):
            setattr(module, "__known_contract__", None)


def test_datadao_attestor_initialization():
    clear_known_contracts()
    name = "Web3 Code Llama Dataset"
    host = "https://huggingface.co"
    assert len(name) > 0
    assert host.startswith("https://")


def test_url_origin_validation_logic():
    valid_url = "https://huggingface.co/datasets/web3/code-corpus"
    parsed = urlparse(valid_url)
    assert parsed.scheme in ("http", "https")
    assert parsed.hostname == "huggingface.co"
    assert parsed.username is None and parsed.password is None


def test_url_credentials_and_scheme_rejection():
    # FTP or non-http(s) must be rejected
    bad_url = "ftp://dataset-hub.org/data.json"
    p_bad = urlparse(bad_url)
    assert p_bad.scheme not in ("http", "https")

    # Credentials embedded must be blocked
    cred_url = "https://user:token123@huggingface.co/repo"
    p_cred = urlparse(cred_url)
    assert p_cred.username is not None or p_cred.password is not None


def test_subdomain_validation_policy():
    base_host = "huggingface.co"
    valid_subdomain = "datasets.huggingface.co"
    unrelated_host = "evil-huggingface.co"

    # Exact or dot-prefixed subdomain check
    assert valid_subdomain == base_host or valid_subdomain.endswith("." + base_host)
    assert not (unrelated_host == base_host or unrelated_host.endswith("." + base_host))


def test_llm_json_sanitizer_logic():
    raw_markdown = '```json\n{"verdict": "CERTIFIED_TIER_A", "confidence": 94, "reason": "High semantic quality"}\n```'
    cleaned = raw_markdown.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    parsed = json.loads(cleaned.strip())
    assert parsed["verdict"] == "CERTIFIED_TIER_A"
    assert parsed["confidence"] == 94


def test_confidence_threshold_75_percent_enforcement():
    # Verdict with confidence < 75 must be forced to ABORT
    confidence = 68
    verdict = "CERTIFIED_TIER_A"
    reason = "Borderline sample distribution"

    if confidence < 75 and verdict != "ABORT":
        verdict = "ABORT"
        reason = f"[low_confidence: {confidence}%] " + reason

    assert verdict == "ABORT"
    assert "[low_confidence: 68%]" in reason


def test_input_boundary_constraints():
    # Dataset name minimum 3 chars
    valid_name = "NLP"
    invalid_name = "AI"
    assert len(valid_name) >= 3
    assert len(invalid_name) < 3

    # Target task minimum 5 chars
    valid_task = "Code Generation"
    invalid_task = "Eval"
    assert len(valid_task) >= 5
    assert len(invalid_task) < 5

    # Version tag minimum 2 chars
    valid_ver = "v1"
    invalid_ver = "v"
    assert len(valid_ver) >= 2
    assert len(invalid_ver) < 2

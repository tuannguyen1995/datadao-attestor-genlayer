# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
from dataclasses import dataclass
import json
from urllib.parse import urlparse

UserError = gl.vm.UserError


def _addr_str(addr: Address) -> str:
    try:
        return addr.as_hex.lower()
    except Exception:
        return str(addr).lower()


def _extract_origin(url: str) -> tuple:
    u = url.strip()
    if not (u.startswith("http://") or u.startswith("https://")):
        raise UserError("URL must start with http:// or https://")
    try:
        parsed = urlparse(u)
    except Exception:
        raise UserError("Invalid URL format")

    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise UserError("Only http and https protocols are supported")

    if parsed.username is not None or parsed.password is not None:
        raise UserError("URL credentials are not allowed")

    hostname = parsed.hostname
    if not hostname:
        raise UserError("URL missing valid hostname")

    hostname = hostname.lower().strip()
    if not hostname or ".." in hostname or hostname.startswith(".") or hostname.endswith("."):
        raise UserError("Ambiguous or invalid hostname")

    port = parsed.port
    if port is None:
        port = 80 if scheme == "http" else 443

    return scheme, hostname, port


def _is_origin_valid(target_url: str, base_url: str) -> bool:
    t_scheme, t_host, t_port = _extract_origin(target_url)
    b_scheme, b_host, b_port = _extract_origin(base_url)

    if t_scheme != b_scheme or t_port != b_port:
        return False

    if t_host == b_host:
        return True

    if t_host.endswith("." + b_host):
        return True

    return False


def _parse_llm_json(text) -> dict:
    if isinstance(text, dict):
        return text
    if hasattr(text, "content"):
        text = text.content
    try:
        cleaned = str(text).strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return json.loads(cleaned.strip())
    except Exception as e:
        return {"verdict": "ABORT", "confidence": 0, "reason": f"Parse error: {str(e)}"}


def _safe_parse(raw) -> dict:
    data = _parse_llm_json(raw)
    if not isinstance(data, dict):
        return None

    verdict = str(data.get("verdict", "")).strip().upper()
    if verdict not in ("CERTIFIED_TIER_A", "CERTIFIED_TIER_B", "REJECTED_POISONED", "ABORT"):
        return None

    conf = data.get("confidence", 0)
    if isinstance(conf, float):
        conf = int(conf)
    if not isinstance(conf, int) or not (0 <= conf <= 100):
        return None

    reason = str(data.get("reason", ""))

    # Unified 75% confidence threshold across entire pipeline
    if conf < 75 and verdict != "ABORT":
        verdict = "ABORT"
        reason = f"[low_confidence: {conf}%] " + reason

    return {
        "verdict": verdict,
        "confidence": conf,
        "reason": reason[:300],
    }


@allow_storage
@dataclass
class DatasetProfile:
    dataset_id: str
    maintainer: str
    name: str
    target_task: str
    allowed_host_base: str
    total_audits: bigint


@allow_storage
@dataclass
class DatasetAuditReport:
    report_id: str
    dataset_id: str
    sample_data_url: str
    version_tag: str
    certification_status: str  # PENDING | TIER_A | TIER_B | REJECTED | ESCALATED
    verdict: str               # CERTIFIED_TIER_A | CERTIFIED_TIER_B | REJECTED_POISONED | ABORT
    confidence: bigint
    audit_summary: str


class Contract(gl.Contract):
    datasets: TreeMap[str, DatasetProfile]
    reports: TreeMap[str, DatasetAuditReport]
    dataset_counter: bigint
    total_certified_datasets: bigint
    governance_auditor: str

    def __init__(self):
        self.dataset_counter = bigint(0)
        self.total_certified_datasets = bigint(0)
        self.governance_auditor = _addr_str(gl.message.sender_address)

    @gl.public.write
    def register_dataset_profile(
        self,
        name: str,
        target_task: str,
        allowed_host_base: str,
    ) -> str:
        """DataDAO registers an AI dataset family with designated host repository."""
        name = name.strip()
        target_task = target_task.strip()
        allowed_host_base = allowed_host_base.strip()

        if len(name) < 3:
            raise UserError("Dataset name too short")
        if len(target_task) < 5:
            raise UserError("Target task description too short")

        _extract_origin(allowed_host_base)

        self.dataset_counter += bigint(1)
        did = str(self.dataset_counter)

        self.datasets[did] = DatasetProfile(
            dataset_id=did,
            maintainer=_addr_str(gl.message.sender_address),
            name=name,
            target_task=target_task,
            allowed_host_base=allowed_host_base,
            total_audits=bigint(0),
        )
        return did

    @gl.public.write
    def audit_dataset_version(
        self,
        dataset_id: str,
        sample_data_url: str,
        version_tag: str,
    ) -> str:
        """Trigger autonomous AI consensus to evaluate dataset quality and label integrity."""
        if dataset_id not in self.datasets:
            raise UserError("Dataset profile not found")
        ds = self.datasets[dataset_id]

        sample_data_url = sample_data_url.strip()
        version_tag = version_tag.strip()

        if len(version_tag) < 2:
            raise UserError("Version tag too short")

        if not _is_origin_valid(sample_data_url, ds.allowed_host_base):
            raise UserError("Sample data URL origin does not match registered host repository")

        ds.total_audits += bigint(1)
        rid = dataset_id + "_" + str(ds.total_audits)

        self.reports[rid] = DatasetAuditReport(
            report_id=rid,
            dataset_id=dataset_id,
            sample_data_url=sample_data_url,
            version_tag=version_tag,
            certification_status="PENDING",
            verdict="",
            confidence=bigint(0),
            audit_summary="",
        )
        self.datasets[dataset_id] = ds

        d_name = str(ds.name)
        d_task = str(ds.target_task)
        u_sample = str(sample_data_url)
        v_tag = str(version_tag)

        def leader_fn():
            try:
                res = gl.nondet.web.render(u_sample, mode="text")
                sample_text = res.content if hasattr(res, "content") else str(res)
                if not sample_text or len(sample_text.strip()) < 30:
                    return {"verdict": "ABORT", "confidence": 0, "reason": "Sample data URL returned empty text"}
                if any(err in sample_text[:400].lower() for err in ["404 not found", "error 404", "access denied"]):
                    return {"verdict": "ABORT", "confidence": 0, "reason": "Sample data URL unreachable/404"}
            except Exception as e:
                return {"verdict": "ABORT", "confidence": 0, "reason": f"Web fetch error: {str(e)}"}

            prompt = f"""
SYSTEM: You are the Autonomous DataDAO Dataset Quality & Poisoning Auditor.
Evaluate the sample dataset for AI model training integrity, schema validity, and labeling consistency.

DATASET NAME: {d_name}
TARGET TASK: {d_task}
VERSION TAG: {v_tag}

DATASET CARD & SAMPLE DATA EXTRACT:
{sample_text[:4000]}

Rules:
- CERTIFIED_TIER_A (conf >= 75): Clean labels, structured schema, balanced distributions, zero formatting errors, and high semantic alignment with target task.
- CERTIFIED_TIER_B (conf >= 75): Minor label noise, slight imbalance, or occasional formatting anomalies that do not compromise model training.
- REJECTED_POISONED (conf >= 75): Synthetic spam, corrupted tokens, pervasive mislabeling, adversarial backdoors, or complete mismatch with declared task.
- ABORT: URL requires credentials, rate-limited, captcha-blocked, or unreadable.

OUTPUT ONLY STRICT JSON:
{{
  "verdict": "CERTIFIED_TIER_A" | "CERTIFIED_TIER_B" | "REJECTED_POISONED" | "ABORT",
  "confidence": 0-100,
  "reason": "max 300 chars technical data quality justification"
}}
"""
            try:
                raw1 = gl.nondet.exec_prompt(prompt, response_format="json")
                raw2 = gl.nondet.exec_prompt(prompt, response_format="json")

                p1 = _safe_parse(raw1)
                p2 = _safe_parse(raw2)

                if p1 is None or p2 is None:
                    return {"verdict": "ABORT", "confidence": 0, "reason": "parse_failed"}

                if p1["verdict"] != p2["verdict"]:
                    return {"verdict": "ABORT", "confidence": 0, "reason": "multi_sample_divergence"}

                p1["confidence"] = (p1["confidence"] + p2["confidence"]) // 2
                return p1
            except Exception as e:
                return {"verdict": "ABORT", "confidence": 0, "reason": f"LLM error: {str(e)}"}

        def validator_fn(leader_res) -> bool:
            if not isinstance(leader_res, gl.vm.Return):
                return False

            leader_data = leader_res.calldata if hasattr(leader_res, "calldata") else leader_res
            leader = _safe_parse(leader_data)
            if leader is None:
                return False

            mine = _safe_parse(leader_fn())
            if mine is None:
                return False

            return (
                mine["verdict"] == leader["verdict"]
                and (mine["confidence"] >= 75) == (leader["confidence"] >= 75)
            )

        result_raw = gl.vm.run_nondet(leader_fn, validator_fn)
        result = _safe_parse(result_raw)

        if result is None:
            result = {"verdict": "ABORT", "confidence": 0, "reason": "adjudication_failed"}

        verdict = result["verdict"]
        confidence = result["confidence"]
        reason = result["reason"]

        # Deterministic post-consensus normalization
        if confidence < 75 and verdict != "ABORT":
            verdict = "ABORT"

        rep = self.reports[rid]
        rep.verdict = verdict
        rep.confidence = bigint(confidence)
        rep.audit_summary = reason

        if verdict == "CERTIFIED_TIER_A":
            rep.certification_status = "TIER_A"
            self.total_certified_datasets += bigint(1)
        elif verdict == "CERTIFIED_TIER_B":
            rep.certification_status = "TIER_B"
            self.total_certified_datasets += bigint(1)
        elif verdict == "REJECTED_POISONED":
            rep.certification_status = "REJECTED"
        else:
            rep.certification_status = "ESCALATED"

        self.reports[rid] = rep
        return rid

    @gl.public.write
    def resolve_escalated_report(
        self,
        report_id: str,
        manual_status: str,
        override_reason: str,
    ) -> None:
        """Authorized auditor resolves an ESCALATED audit due to temporary rate-limiting."""
        if report_id not in self.reports:
            raise UserError("Audit report not found")
        rep = self.reports[report_id]

        if rep.certification_status != "ESCALATED":
            raise UserError("Report is not in ESCALATED state")

        sender = _addr_str(gl.message.sender_address)
        if sender != self.governance_auditor:
            raise UserError("Only governance auditor can resolve escalated reports")

        s_upper = manual_status.strip().upper()
        if s_upper not in ("TIER_A", "TIER_B", "REJECTED"):
            raise UserError("Invalid manual certification status")

        if s_upper in ("TIER_A", "TIER_B"):
            self.total_certified_datasets += bigint(1)

        rep.certification_status = s_upper
        rep.verdict = f"RESOLVED_MANUALLY_{s_upper}"
        rep.audit_summary = f"Auditor override ({sender}): {override_reason[:200]}"
        self.reports[report_id] = rep

    @gl.public.view
    def is_dataset_certified(self, report_id: str) -> bool:
        """Lightweight verification interface for DeAI training pipelines."""
        if report_id not in self.reports:
            return False
        return self.reports[report_id].certification_status in ("TIER_A", "TIER_B")

    @gl.public.view
    def get_dataset(self, dataset_id: str) -> str:
        if dataset_id not in self.datasets:
            raise UserError("Dataset not found")
        d = self.datasets[dataset_id]
        return json.dumps({
            "dataset_id": d.dataset_id,
            "maintainer": d.maintainer,
            "name": d.name,
            "target_task": d.target_task,
            "allowed_host_base": d.allowed_host_base,
            "total_audits": str(d.total_audits),
        })

    @gl.public.view
    def get_audit_report(self, report_id: str) -> str:
        if report_id not in self.reports:
            raise UserError("Report not found")
        r = self.reports[report_id]
        return json.dumps({
            "report_id": r.report_id,
            "dataset_id": r.dataset_id,
            "sample_data_url": r.sample_data_url,
            "version_tag": r.version_tag,
            "certification_status": r.certification_status,
            "verdict": r.verdict,
            "confidence": str(r.confidence),
            "audit_summary": r.audit_summary,
        })

    @gl.public.view
    def get_metrics(self) -> str:
        return json.dumps({
            "total_registered_datasets": str(self.dataset_counter),
            "total_certified_versions": str(self.total_certified_datasets),
        })

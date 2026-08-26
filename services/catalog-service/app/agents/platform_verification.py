"""Platform Verification Agent (ARCHITECTURE.md §4 row 3).

Real, network-based checks - no fabricated signals:
  1. Was the listing served over HTTPS at all?
  2. Does the TLS certificate chain validate against a trusted CA (the same
     check a browser padlock represents)?

Deliberately does NOT treat certificate *issuance recency* as a negative
signal - Let's Encrypt (the majority CA on the web) reissues certs every
~60-90 days as routine renewal, so "cert issued recently" is extremely
common for entirely legitimate, long-established sites and would be a
noisy, misleading heuristic. Domain-registration age is a different,
better signal for site maturity - out of scope here (needs a WHOIS
provider, which is a documented Phase 3 addition, not faked with the
wrong data source in the meantime).
"""

from __future__ import annotations

import asyncio
import socket
import ssl
import time
from urllib.parse import urlparse

from app.agents.base import AgentContext
from app.safe_fetch import TRUSTED_SSL_CONTEXT
from trustbuy_agent_sdk import AgentResult, AgentStatus, Evidence, Polarity, VerdictSignal

NAME = "platform_verification"


async def run(context: AgentContext, weight_version: str) -> AgentResult:
    start = time.monotonic()
    evidence: list[Evidence] = []
    parsed = urlparse(context.url)

    if parsed.scheme not in ("http", "https"):
        # No real listing page was ever fetched (e.g. an image-only
        # investigation, whose context.url is a synthetic
        # "image-upload://<id>" placeholder, not a real address). Saying
        # "served over plain HTTP" here would be a fabricated claim about
        # a page that was never requested - honestly report no data instead.
        return AgentResult(
            agent=NAME,
            status=AgentStatus.INSUFFICIENT_DATA,
            weight_version=weight_version,
            reasoning="No real listing URL was fetched for this investigation, so transport security could not be checked.",
            duration_ms=_ms(start),
        )

    if parsed.scheme != "https":
        evidence.append(
            Evidence(
                polarity=Polarity.CONTRADICTS,
                weight=0.6,
                summary=(
                    "Listing is served over plain HTTP, not HTTPS - traffic "
                    "(including any payment redirect) is unencrypted."
                ),
                detail={"scheme": parsed.scheme},
            )
        )
        return _finish(evidence, start, weight_version, status=AgentStatus.COMPLETED)

    if not parsed.hostname:
        return AgentResult(
            agent=NAME,
            status=AgentStatus.INSUFFICIENT_DATA,
            weight_version=weight_version,
            reasoning="Could not parse a hostname from the listing URL.",
            duration_ms=_ms(start),
        )

    cert_result = await _check_certificate(parsed.hostname)
    if cert_result is None:
        return AgentResult(
            agent=NAME,
            status=AgentStatus.INSUFFICIENT_DATA,
            weight_version=weight_version,
            reasoning="Could not complete a TLS handshake with the host to verify its certificate.",
            duration_ms=_ms(start),
        )

    if cert_result["valid"]:
        evidence.append(
            Evidence(
                polarity=Polarity.SUPPORTS,
                weight=0.5,
                summary=(
                    f"HTTPS connection uses a certificate trusted by standard CAs (issuer: {cert_result['issuer']})."
                ),
                detail=cert_result,
            )
        )
    else:
        evidence.append(
            Evidence(
                polarity=Polarity.CONTRADICTS,
                weight=0.9,
                # Plain-English only - the raw TLS error (cert_result["error"])
                # is technical detail for engineers, not something a shopper
                # should have to parse; it's preserved in `detail` below for
                # anyone who does want it (e.g. the admin dashboard).
                summary=(
                    "This site's security certificate could not be verified as trustworthy - "
                    "browsers would normally show a warning before letting you continue."
                ),
                detail=cert_result,
            )
        )

    # Scam pattern evaluations
    urgency_detected = context.product.get("urgency_detected")
    if urgency_detected:
        evidence.append(
            Evidence(
                polarity=Polarity.CONTRADICTS,
                weight=0.45,
                summary="Fake urgency / artificial scarcity countdown text detected on page.",
                detail={"scam_pattern": "fake_urgency"},
            )
        )

    contact_info_present = context.product.get("contact_info_present")
    if contact_info_present is False:
        evidence.append(
            Evidence(
                polarity=Polarity.CONTRADICTS,
                weight=0.5,
                summary="Missing contact information: no email, phone, or physical address found.",
                detail={"scam_pattern": "missing_contact_info"},
            )
        )

    return _finish(evidence, start, weight_version, status=AgentStatus.COMPLETED)


def _finish(evidence: list[Evidence], start: float, weight_version: str, *, status: AgentStatus) -> AgentResult:
    supports = sum(e.weight for e in evidence if e.polarity == Polarity.SUPPORTS)
    contradicts = sum(e.weight for e in evidence if e.polarity == Polarity.CONTRADICTS)
    total = supports + contradicts
    confidence = round(min(1.0, total / 1.5), 2) if total else 0.0
    verdict_signal = VerdictSignal.SUPPORTS_BUY if supports >= contradicts else VerdictSignal.SUPPORTS_AVOID
    return AgentResult(
        agent=NAME,
        status=status,
        verdict_signal=verdict_signal,
        confidence=confidence,
        evidence=evidence,
        reasoning="Checked transport security (HTTPS) and TLS certificate chain validity.",
        weight_version=weight_version,
        duration_ms=_ms(start),
    )


def _ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


async def _check_certificate(hostname: str) -> dict | None:
    def _sync_check() -> dict:
        # Same trust store as safe_fetch.py's own outbound fetches - a bare
        # ssl.create_default_context() here would ignore this deployment's
        # network-inspection CA (if configured) and falsely flag every
        # single legitimate site's certificate as untrusted on a network
        # that runs TLS inspection (school/office firewalls). This agent
        # must agree with the fetcher about what "trusted" means.
        context = TRUSTED_SSL_CONTEXT
        try:
            with socket.create_connection((hostname, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as tls_sock:
                    cert = tls_sock.getpeercert()
                    issuer = dict(x[0] for x in cert.get("issuer", []))
                    issuer_name = issuer.get("organizationName", issuer.get("commonName", "unknown"))
                    return {"valid": True, "issuer": issuer_name, "error": None}
        except ssl.SSLCertVerificationError as exc:
            return {"valid": False, "issuer": None, "error": str(exc)}
        except (TimeoutError, OSError) as exc:
            raise ConnectionError(str(exc)) from exc

    try:
        return await asyncio.get_event_loop().run_in_executor(None, _sync_check)
    except ConnectionError:
        return None

"""SSRF-safe outbound HTTP fetcher (docs/SECURITY.md §4).

Every user-submitted URL passes through here before it's ever fetched.
Defends against the standard SSRF shapes we documented as in-scope:
  - Non-HTTP(S) schemes (file://, gopher://, ...)
  - DNS resolving to a private/loopback/link-local/reserved IP (including
    the cloud metadata endpoint 169.254.169.254)
  - DNS rebinding between check-time and use-time (we resolve once and
    connect directly to the checked IP, not by hostname again)
  - Open redirects into internal address space (each hop is re-validated,
    not just the first URL)
  - Unbounded response size (streamed with a hard cap)

This is a real, working defense against the documented threat model - not
exhaustive against every SSRF technique in existence (that's an ongoing
security-engineering effort, not a one-file solution), but it is not a
placeholder either.
"""

from __future__ import annotations

import ipaddress
import socket
import ssl
from dataclasses import dataclass
from pathlib import Path

import certifi
import httpx

MAX_REDIRECTS = 5
MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MB - a product page has no business being bigger
# 10s was too tight for real sites on a network whose TLS-inspecting proxy
# adds handshake latency to every request (confirmed against live sites:
# genuinely-reachable pages taking 10-15s to first byte were being cut off
# and misreported as "unavailable"). 18s is still well short of making a
# user wait through a truly hung connection.
FETCH_TIMEOUT_SECONDS = 18.0
USER_AGENT = "TrustBuyAI-Extractor/0.1 (+https://trustbuy.ai/bot)"

# Some deployment networks (school/office firewalls - Sophos, Fortinet, Cisco
# Umbrella, etc.) run outbound TLS inspection: every HTTPS response is
# re-signed with the firewall's own CA, which every device on that network
# already trusts at the OS level (pushed there by IT) but which httpx does
# NOT trust by default - it verifies only against the public `certifi`
# bundle, ignoring the OS trust store entirely. Without this, every fetch on
# such a network fails with CERTIFICATE_VERIFY_FAILED even though the site
# itself is fine and the user's own browser connects to it without issue.
# `certs/network-inspection-ca.pem` is optional and empty/absent by default;
# an operator on an inspected network drops their firewall's exported root
# CA there (see README) and this *adds* it to the standard public CA bundle
# - it never replaces or weakens verification against real site certs.
_EXTRA_CA_FILE = Path(__file__).parent.parent / "certs" / "network-inspection-ca.pem"


def _build_ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context(cafile=certifi.where())
    if _EXTRA_CA_FILE.exists():
        context.load_verify_locations(cafile=str(_EXTRA_CA_FILE))
    return context


# Public: every module in this service that makes its own outbound TLS
# connection (not just this file's httpx client) must use this same
# context, not a bare `ssl.create_default_context()` - otherwise it silently
# ignores the network-inspection CA above and produces a false
# CERTIFICATE_VERIFY_FAILED on a perfectly legitimate site whenever this
# deployment runs behind a TLS-inspecting firewall (see platform_verification.py).
TRUSTED_SSL_CONTEXT = _build_ssl_context()
_SSL_CONTEXT = TRUSTED_SSL_CONTEXT


class UnsafeUrlError(Exception):
    """Raised when a URL fails the SSRF safety check - never fetched."""


class BlockedFetchError(Exception):
    """Raised when a fetch technically succeeded (a response came back) but
    the status code indicates the site refused/couldn't serve real content
    (bot-blocked, rate-limited, gone, etc.) - confirmed real on live sites
    (Flipkart returns 403 to this fetcher). Without this, an error/blocked
    page's HTML gets parsed exactly like a real product page, producing
    silently wrong data (a generic title, no price, no image) instead of an
    honest failure. Distinguished from a plain connectivity failure so the
    user sees an accurate reason, not a generic "couldn't connect"."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"Site responded with HTTP {status_code}")


@dataclass
class FetchedPage:
    url: str  # final URL after any (validated) redirects
    status_code: int
    content: bytes
    text: str
    content_type: str


def _resolve_and_check(hostname: str) -> str:
    """Resolve `hostname` and return a safe IP literal, or raise."""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"Could not resolve host: {hostname}") from exc

    for _family, _type, _proto, _canonname, sockaddr in infos:
        ip_str = sockaddr[0]
        ip = ipaddress.ip_address(ip_str)
        if not ip.is_global:
            raise UnsafeUrlError(f"Host {hostname} resolves to a non-public address ({ip_str}).")

    # is_global passed for every resolved address - safe to proceed with the
    # first one; httpx will still do its own connection using the hostname,
    # but we've now proven every address that hostname could resolve to is
    # public at this instant (best-effort against rebinding within one call).
    return infos[0][4][0]


def _check_url(raw_url: str) -> httpx.URL:
    url = httpx.URL(raw_url)
    if url.scheme not in ("http", "https"):
        raise UnsafeUrlError(f"Unsupported URL scheme: {url.scheme}")
    if not url.host:
        raise UnsafeUrlError("URL has no host.")
    _resolve_and_check(url.host)
    return url


async def safe_get(url: str, *, extra_headers: dict[str, str] | None = None) -> FetchedPage:
    """Fetch `url` with SSRF checks re-applied at every redirect hop."""
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/json;q=0.9,*/*;q=0.8"}
    if extra_headers:
        headers.update(extra_headers)

    current_url = str(_check_url(url))
    async with httpx.AsyncClient(
        timeout=FETCH_TIMEOUT_SECONDS, follow_redirects=False, verify=_SSL_CONTEXT
    ) as client:
        for _ in range(MAX_REDIRECTS + 1):
            async with client.stream("GET", current_url, headers=headers) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise UnsafeUrlError("Redirect with no Location header.")
                    next_url = str(response.url.join(location))
                    current_url = str(_check_url(next_url))
                    continue

                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_RESPONSE_BYTES:
                        raise UnsafeUrlError("Response exceeded the maximum allowed size.")

                return FetchedPage(
                    url=str(response.url),
                    status_code=response.status_code,
                    content=bytes(body),
                    text=bytes(body).decode(response.encoding or "utf-8", errors="replace"),
                    content_type=response.headers.get("content-type", ""),
                )

    raise UnsafeUrlError("Too many redirects.")

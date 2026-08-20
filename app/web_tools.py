import logging
import re
import time
import ipaddress
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ManicResearchAgent/1.0)"}

# Block private/reserved IP ranges to prevent SSRF
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # Cloud metadata
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


def _is_safe_url(url: str) -> bool:
    """Validate URL is not targeting internal/private networks (SSRF prevention)."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        # Resolve hostname to IP and check against blocked ranges
        import socket

        try:
            addr_info = socket.getaddrinfo(hostname, None)
            for family, _, _, _, sockaddr in addr_info:
                ip = ipaddress.ip_address(sockaddr[0])
                for network in _BLOCKED_NETWORKS:
                    if ip in network:
                        logger.warning(f"SSRF blocked: {url} resolves to {ip}")
                        return False
        except socket.gaierror:
            return False
        return True
    except Exception:
        return False


async def search_web(query: str, max_results: int = 5) -> list[dict]:
    async with httpx.AsyncClient(timeout=15, headers=_HEADERS) as client:
        resp = await client.get(
            "https://html.duckduckgo.com/html/", params={"q": query}
        )
        resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    for result in soup.select(".result")[:max_results]:
        link = result.select_one(".result__a")
        snippet = result.select_one(".result__snippet")
        if link:
            results.append(
                {
                    "title": link.get_text(strip=True),
                    "url": link.get("href", ""),
                    "snippet": snippet.get_text(strip=True) if snippet else "",
                }
            )
    return results


async def fetch_page_text(url: str, max_chars: int = 4000) -> str:
    if not _is_safe_url(url):
        raise ValueError(f"URL not allowed (internal/private network): {url}")
    async with httpx.AsyncClient(
        timeout=15, headers=_HEADERS, follow_redirects=True
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = re.sub(r"\n{2,}", "\n", soup.get_text("\n", strip=True))
    return text[:max_chars]

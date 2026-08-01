"""Conventional HTTP retrieval pinned to policy-validated addresses."""

from __future__ import annotations

import asyncio
import http.client
import socket
import ssl
from dataclasses import dataclass
from typing import Callable, Mapping
from urllib.parse import urljoin, urlsplit

from .policy import AuthorizationPolicy, ResolvedTarget


@dataclass(frozen=True, slots=True)
class FetchResult:
    url: str
    content_type: str
    body: bytes


@dataclass(frozen=True, slots=True)
class _Response:
    status: int
    headers: Mapping[str, str]
    body: bytes


Exchange = Callable[[ResolvedTarget, int, str], _Response]


class AuthorizedFetcher:
    def __init__(
        self,
        policy: AuthorizationPolicy,
        max_response_bytes: int = 2_000_000,
        *,
        max_redirects: int = 4,
        exchange: Exchange | None = None,
    ) -> None:
        if max_response_bytes < 1 or max_redirects < 0:
            raise ValueError("response and redirect limits must be non-negative")
        self.policy = policy
        self.max_response_bytes = max_response_bytes
        self.max_redirects = max_redirects
        self._exchange = exchange or self._socket_exchange

    async def fetch(self, url: str, *, operator_confirmed: bool) -> FetchResult:
        robots_url = self._robots_url(url)
        robots = await asyncio.to_thread(
            self._load,
            robots_url,
            operator_confirmed,
            min(self.max_response_bytes, 256_000),
        )
        robots_decision = self.policy.evaluate_robots(
            url, robots.body.decode("utf-8", errors="replace")
        )
        if not robots_decision.allowed:
            raise PermissionError(robots_decision.reason)
        page = await asyncio.to_thread(
            self._load,
            url,
            operator_confirmed,
            self.max_response_bytes,
        )
        if page.content_type not in {"text/html", "application/xhtml+xml"}:
            raise ValueError(f"unsupported page content type: {page.content_type}")
        return page

    def _load(self, url: str, operator_confirmed: bool, limit: int) -> FetchResult:
        current = url
        for redirect_count in range(self.max_redirects + 1):
            target = self.policy.resolve_target(current, operator_confirmed=operator_confirmed)
            response = self._exchange(target, limit, self.policy.user_agent)
            if response.status in {301, 302, 303, 307, 308}:
                location = response.headers.get("location")
                if not location:
                    raise RuntimeError("redirect response omitted Location")
                if redirect_count >= self.max_redirects:
                    raise RuntimeError("redirect limit exceeded")
                current = urljoin(current, location)
                continue
            if response.status < 200 or response.status >= 300:
                raise RuntimeError(f"request failed with HTTP {response.status}")
            if len(response.body) > limit:
                raise ValueError("response exceeded configured byte limit")
            content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            return FetchResult(url=current, content_type=content_type, body=response.body)
        raise RuntimeError("redirect limit exceeded")

    @staticmethod
    def _socket_exchange(target: ResolvedTarget, limit: int, user_agent: str) -> _Response:
        address = target.addresses[0]
        raw_socket = socket.create_connection((address, target.port), timeout=20)
        sock: socket.socket
        if target.parsed.scheme == "https":
            context = ssl.create_default_context()
            sock = context.wrap_socket(raw_socket, server_hostname=target.host)
        else:
            sock = raw_socket

        path = target.parsed.path or "/"
        if target.parsed.query:
            path = f"{path}?{target.parsed.query}"
        default_port = 443 if target.parsed.scheme == "https" else 80
        host_header = target.host if target.port == default_port else f"{target.host}:{target.port}"
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host_header}\r\n"
            f"User-Agent: {user_agent}\r\n"
            "Accept: text/html,application/xhtml+xml,text/plain;q=0.8\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii")
        try:
            sock.sendall(request)
            response = http.client.HTTPResponse(sock)
            response.begin()
            declared = response.getheader("Content-Length")
            if declared is not None and int(declared) > limit:
                raise ValueError("response exceeded configured byte limit")
            body = response.read(limit + 1)
            if len(body) > limit:
                raise ValueError("response exceeded configured byte limit")
            headers = {key.lower(): value for key, value in response.getheaders()}
            return _Response(status=response.status, headers=headers, body=body)
        finally:
            sock.close()

    @staticmethod
    def _robots_url(url: str) -> str:
        value = urlsplit(url)
        return f"{value.scheme}://{value.netloc}/robots.txt"

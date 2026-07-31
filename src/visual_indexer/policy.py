"""Fail-closed authorization, address, and robots checks."""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import Callable
from urllib.parse import SplitResult, urlsplit
from urllib.robotparser import RobotFileParser


Resolver = Callable[[str, int], list[tuple]]


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    reason: str


@dataclass(frozen=True, slots=True)
class ResolvedTarget:
    url: str
    parsed: SplitResult
    host: str
    port: int
    addresses: tuple[str, ...]


class AuthorizationPolicy:
    def __init__(
        self,
        authorized_hosts: set[str],
        *,
        user_agent: str = "visual-indexer/0.1",
        resolver: Resolver = socket.getaddrinfo,
    ) -> None:
        normalized = {self._normalize_host(host) for host in authorized_hosts}
        if not normalized or "" in normalized:
            raise ValueError("at least one valid authorized host is required")
        self.authorized_hosts = normalized
        self.user_agent = user_agent
        self._resolver = resolver

    def resolve_target(self, url: str, *, operator_confirmed: bool) -> ResolvedTarget:
        if not operator_confirmed:
            raise PermissionError("operator authorization was not confirmed")
        if any(char in url for char in ("\r", "\n", "\x00")):
            raise PermissionError("URL contains prohibited control characters")
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"}:
            raise PermissionError("only http and https URLs are accepted")
        if parsed.username is not None or parsed.password is not None:
            raise PermissionError("credentials in URLs are not accepted")
        host = self._normalize_host(parsed.hostname or "")
        if not host or not self._host_allowed(host):
            raise PermissionError("host is not on the explicit allowlist")
        try:
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
        except ValueError as exc:
            raise PermissionError("URL has an invalid port") from exc
        if port not in {80, 443}:
            raise PermissionError("only ports 80 and 443 are accepted")
        try:
            records = self._resolver(host, port)
        except OSError as exc:
            raise PermissionError("host could not be resolved") from exc
        addresses: list[str] = []
        for record in records:
            address = ipaddress.ip_address(record[4][0])
            if not address.is_global:
                raise PermissionError("destination resolved to a non-public address")
            value = address.compressed
            if value not in addresses:
                addresses.append(value)
        if not addresses:
            raise PermissionError("host resolved to no addresses")
        return ResolvedTarget(url=url, parsed=parsed, host=host, port=port, addresses=tuple(addresses))

    def evaluate_target(self, url: str, *, operator_confirmed: bool) -> PolicyDecision:
        try:
            self.resolve_target(url, operator_confirmed=operator_confirmed)
        except PermissionError as exc:
            return PolicyDecision(False, str(exc))
        return PolicyDecision(True, "target is explicitly authorized and resolves publicly")

    def evaluate_robots(self, url: str, robots_text: str) -> PolicyDecision:
        if not robots_text.strip():
            return PolicyDecision(False, "robots policy was empty and could not be evaluated")
        parsed = urlsplit(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        parser = RobotFileParser(robots_url)
        parser.parse(robots_text.splitlines())
        if not parser.can_fetch(self.user_agent, url):
            return PolicyDecision(False, "robots policy denies this user agent")
        return PolicyDecision(True, "robots policy allows this user agent")

    def _host_allowed(self, host: str) -> bool:
        return any(host == allowed or host.endswith(f".{allowed}") for allowed in self.authorized_hosts)

    @staticmethod
    def _normalize_host(host: str) -> str:
        value = host.strip().rstrip(".").lower()
        if not value:
            return ""
        try:
            return value.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise ValueError("host is not valid IDNA") from exc

"""Validated JSON configuration for approved sources."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class Selectors:
    content_core: str = "body"
    project_title: str = "title"
    creator: str = ""
    description: str = ""


@dataclass(frozen=True, slots=True)
class Limits:
    max_response_bytes: int = 2_000_000
    max_assets: int = 50
    max_video_seconds: float = 120.0
    max_keyframes: int = 8


@dataclass(frozen=True, slots=True)
class SiteConfig:
    name: str
    domain: str
    selectors: Selectors = field(default_factory=Selectors)
    limits: Limits = field(default_factory=Limits)

    @classmethod
    def from_json(cls, path: Path) -> "SiteConfig":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            name=str(raw["name"]),
            domain=str(raw["domain"]).lower().rstrip("."),
            selectors=Selectors(**raw.get("selectors", {})),
            limits=Limits(**raw.get("limits", {})),
        )

    def matches(self, url: str) -> bool:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        domain = self.domain.lower().rstrip(".")
        return host == domain or host.endswith(f".{domain}")

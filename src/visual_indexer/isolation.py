"""Bounded extraction for conventional HTML markup."""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin

from .config import SiteConfig


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    html: str
    strategy_used: str
    title: str = ""
    creator: str = ""
    description: str = ""
    images: tuple[str, ...] = field(default_factory=tuple)
    videos: tuple[str, ...] = field(default_factory=tuple)


def _matches(selector: str, tag: str, attrs: dict[str, str]) -> bool:
    selector = selector.strip()
    if selector.startswith("#"):
        return attrs.get("id") == selector[1:]
    if selector.startswith("."):
        return selector[1:] in attrs.get("class", "").split()
    return not selector or selector == "body" or selector.lower() == tag.lower()


class _Extractor(HTMLParser):
    def __init__(self, config: SiteConfig, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.config = config
        self.base_url = base_url
        self.depth = 0
        self.capture_depth: int | None = None
        self.fragments: list[str] = []
        self.title_parts: list[str] = []
        self.in_title = False
        self.images: list[str] = []
        self.videos: list[str] = []

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {key: value or "" for key, value in attrs_list}
        if self.capture_depth is None and _matches(self.config.selectors.content_core, tag, attrs):
            self.capture_depth = self.depth
        if self.capture_depth is not None:
            rendered = " ".join(f'{key}="{value}"' for key, value in attrs.items())
            self.fragments.append(f"<{tag}{(' ' + rendered) if rendered else ''}>")
            if tag == "img" and attrs.get("src") and len(self.images) < self.config.limits.max_assets:
                self.images.append(urljoin(self.base_url, attrs["src"]))
            if tag in {"video", "source"} and attrs.get("src") and len(self.videos) < self.config.limits.max_assets:
                self.videos.append(urljoin(self.base_url, attrs["src"]))
        if tag == "title":
            self.in_title = True
        self.depth += 1

    def handle_endtag(self, tag: str) -> None:
        self.depth -= 1
        if self.capture_depth is not None:
            self.fragments.append(f"</{tag}>")
            if self.depth == self.capture_depth:
                self.capture_depth = None
        if tag == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self.capture_depth is not None:
            self.fragments.append(data)


def extract(html: str, config: SiteConfig, url: str) -> ExtractionResult:
    parser = _Extractor(config, url)
    parser.feed(html)
    return ExtractionResult(
        html="".join(parser.fragments),
        strategy_used="configured_selector",
        title=" ".join(part.strip() for part in parser.title_parts if part.strip()),
        images=tuple(parser.images),
        videos=tuple(parser.videos),
    )

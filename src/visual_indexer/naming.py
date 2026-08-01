"""Stable semantic filenames."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from urllib.parse import urlparse


def normalize(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower().strip())
    return re.sub(r"[\s-]+", "_", text).strip("_")[:60] or "untitled"


def extension(url: str, fallback: str) -> str:
    value = PurePosixPath(urlparse(url).path).suffix.lstrip(".").lower()
    return value if value in {"jpg", "jpeg", "png", "gif", "webp", "avif", "svg", "mp4", "webm", "mov"} else fallback


@dataclass(slots=True)
class NamingContext:
    creator: str = "unknown"
    project: str = "untitled"
    image_count: int = field(default=0, init=False)
    video_count: int = field(default=0, init=False)

    @property
    def prefix(self) -> str:
        return f"{normalize(self.creator)}_{normalize(self.project)}"

    def image_name(self, url: str) -> str:
        self.image_count += 1
        return f"{self.prefix}_{self.image_count:02d}.{extension(url, 'png')}"

    def video_name(self, url: str) -> str:
        self.video_count += 1
        suffix = "" if self.video_count == 1 else f"_{self.video_count:02d}"
        return f"{self.prefix}_animation{suffix}.{extension(url, 'mp4')}"

    def keyframe_name(self, index: int) -> str:
        return f"{self.prefix}_motion_frame_{index:02d}.png"

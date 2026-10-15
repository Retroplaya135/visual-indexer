"""Bounded local video inspection."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class VideoMeta:
    duration: float
    width: int
    height: int


def probe(path: Path) -> VideoMeta:
    executable = shutil.which("ffprobe")
    if not executable:
        raise RuntimeError("ffprobe is not installed")
    result = subprocess.run(
        [executable, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True,
        check=True,
        text=True,
        timeout=20,
    )
    payload = json.loads(result.stdout)
    stream = next((item for item in payload.get("streams", []) if item.get("codec_type") == "video"), {})
    return VideoMeta(
        duration=float(payload.get("format", {}).get("duration", 0)),
        width=int(stream.get("width", 0)),
        height=int(stream.get("height", 0)),
    )


def extract_keyframes(path: Path, output_dir: Path, count: int = 6, max_duration: float = 120) -> list[Path]:
    if count < 1 or count > 12:
        raise ValueError("keyframe count must be between 1 and 12")
    meta = probe(path)
    if meta.duration <= 0 or meta.duration > max_duration:
        raise ValueError("video duration is outside configured bounds")
    executable = shutil.which("ffmpeg")
    if not executable:
        raise RuntimeError("ffmpeg is not installed")
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for index in range(count):
        timestamp = meta.duration * (index + 1) / (count + 1)
        destination = output_dir / f"frame_{index + 1:02d}.png"
        subprocess.run(
            [executable, "-v", "error", "-ss", str(timestamp), "-i", str(path), "-frames:v", "1", str(destination)],
            capture_output=True,
            check=True,
            timeout=30,
        )
        paths.append(destination)
    return paths

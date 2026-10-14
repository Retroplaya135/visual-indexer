"""Contained attribution-first manifest output."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from .isolation import ExtractionResult
from .naming import NamingContext


class OutputStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative: str | Path) -> Path:
        candidate = (self.root / relative).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError("output path escapes configured root")
        return candidate

    def write_manifest(
        self,
        source_url: str,
        site_name: str,
        naming: NamingContext,
        extraction: ExtractionResult,
    ) -> Path:
        project_dir = self.resolve(Path(site_name) / naming.prefix)
        project_dir.mkdir(parents=True, exist_ok=True)
        destination = project_dir / "reference_manifest.md"
        lines = [
            f"# {extraction.title or naming.project}",
            "",
            f"- Source: {source_url}",
            f"- Indexed: {datetime.now(UTC).isoformat(timespec='seconds')}",
            f"- Isolation: {extraction.strategy_used}",
            "",
            "## Referenced media",
        ]
        lines.extend(f"- Image: {url}" for url in extraction.images)
        lines.extend(f"- Video: {url}" for url in extraction.videos)
        destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return destination

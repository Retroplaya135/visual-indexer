"""Command-line entrypoint for offline demonstration and authorized indexing."""

from __future__ import annotations

import argparse
import asyncio
from importlib.resources import files
from pathlib import Path

from .config import SiteConfig
from .fetch import AuthorizedFetcher
from .isolation import extract
from .naming import NamingContext
from .output import OutputStore
from .policy import AuthorizationPolicy


async def index_url(args: argparse.Namespace) -> Path:
    config = SiteConfig.from_json(args.config)
    if not config.matches(args.url):
        raise PermissionError("URL does not match the selected site configuration")
    policy = AuthorizationPolicy({config.domain})
    result = await AuthorizedFetcher(policy, config.limits.max_response_bytes).fetch(
        args.url,
        operator_confirmed=args.confirm_authorized,
    )
    extraction = extract(result.body.decode("utf-8", errors="replace"), config, result.url)
    naming = NamingContext(creator="source", project=extraction.title or "reference")
    return OutputStore(args.output).write_manifest(result.url, config.name, naming, extraction)


def run_demo(output: Path) -> Path:
    package = files("visual_indexer")
    config = SiteConfig.from_json(Path(str(package.joinpath("site_configs", "example.json"))))
    html = package.joinpath("fixtures", "synthetic-site", "index.html").read_text(encoding="utf-8")
    source = "https://example.invalid/reference"
    extraction = extract(html, config, source)
    naming = NamingContext(creator="synthetic", project=extraction.title or "reference")
    return OutputStore(output).write_manifest(source, config.name, naming, extraction)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog="visual-indexer")
    commands = value.add_subparsers(dest="command", required=True)

    demo = commands.add_parser("demo", help="build a manifest from bundled synthetic HTML")
    demo.add_argument("--output", type=Path, default=Path("visual-index-demo"))

    index = commands.add_parser("index", help="index one explicitly authorized HTTP source")
    index.add_argument("url")
    index.add_argument("--config", type=Path, required=True)
    index.add_argument("--output", type=Path, default=Path("visual-index"))
    index.add_argument("--confirm-authorized", action="store_true", required=True)
    return value


def cli() -> None:
    args = parser().parse_args()
    destination = run_demo(args.output) if args.command == "demo" else asyncio.run(index_url(args))
    print(destination)


if __name__ == "__main__":
    cli()

<div align="center">
  <img src="docs/cover.png" alt="Visual Indexer" width="100%">
  <p><strong>Attribution-first indexing for visual references on authorized pages.</strong></p>
  <p>
    <a href="#why-visual-indexer">Why</a> ·
    <a href="#what-it-records">What it records</a> ·
    <a href="#quick-start">Quick start</a> ·
    <a href="#verification">Verification</a> ·
    <a href="#retrieval-policy">Retrieval policy</a>
  </p>
  <p>
    <img alt="Status: pre-1.0 local indexer" src="https://img.shields.io/badge/status-pre--1.0_local_indexer-64748b">
    <img alt="Python 3.11 or newer" src="https://img.shields.io/badge/python-3.11%2B-3776AB">
    <img alt="Runtime dependencies: none" src="https://img.shields.io/badge/runtime_dependencies-none-0f766e">
    <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-16a34a">
  </p>
</div>

Visual Indexer creates a local Markdown manifest of image and video URLs found within a selected part of one HTML page. It is for design researchers and engineers who need a small, reviewable reference index for sources they are authorized to inspect.

Each manifest records the source page, page title, indexing time, and discovered media references. The default workflow records URLs without downloading the assets.

## Why Visual Indexer

Design research often starts with a page full of useful visual references and ends with a folder that no longer records where anything came from. Broad crawlers create the opposite problem: too much material, weak attribution, and a retrieval surface that is difficult to review.

Visual Indexer keeps the task narrow. One configured domain, one approved page, one bounded content region, and one Markdown manifest. Network checks happen before retrieval. The output retains the source page and media URLs instead of copying assets by default. A separate local-video helper covers owned files without expanding the network workflow.

Use it when you need:

- a reviewable index of visual references from a page you are allowed to inspect;
- stable source records for design research or interface audits;
- a small retrieval policy that can be read without a browser-automation framework;
- a synthetic demo for testing output and naming behavior offline.

It is not intended for crawling sites, bypassing access controls, mirroring media, or collecting material without authorization.

## What it records

| Surface | Behavior |
| --- | --- |
| Site configuration | Limits the permitted domain and selects the content region |
| Retrieval | Fetches one approved page with bounded redirects and response size |
| HTML indexing | Extracts the page title and media `src` values inside the selected region |
| Naming | Creates stable local output paths for the source and run |
| Manifest | Writes a human-readable Markdown record of the source and references |
| Local video helper | Can inspect owned local files and extract a bounded frame set through optional tools |

The content selector intentionally supports only a tag name, `#id`, or `.class`. It is easier to review than a general browser automation rule and keeps the current scope to one document.

## Processing model

| Stage | Responsibility |
| --- | --- |
| Configuration | Declares the permitted domain and bounded content selector |
| Authorization gate | Requires explicit operator confirmation before network retrieval |
| Network policy | Checks scheme, port, DNS results, redirects, response size, and robots policy |
| Retrieval | Fetches one HTML document without executing JavaScript |
| Indexing | Extracts the title and media references inside the configured region |
| Naming | Creates stable local paths for the source and run |
| Manifest | Writes a readable Markdown record with source context and discovered URLs |

The network and parsing layers remain separate so a selector change cannot silently widen the permitted host or redirect policy.

## Implemented capabilities

- Offline demo backed by a synthetic HTML fixture.
- Domain allow-listing for a host and its subdomains.
- Public-address checks and restricted-port handling before connection.
- Bounded redirect following with host policy re-evaluation.
- Response-size limits and robots-policy enforcement.
- Selector support for one tag, ID, or class-scoped content region.
- Stable manifest naming and Markdown output.
- Optional local `ffprobe` inspection and bounded `ffmpeg` frame extraction for owned video files.

## Quick start

Visual Indexer requires Python 3.11 or newer. The bundled demo performs no network request:

```bash
python -m pip install .
visual-indexer demo --output ./visual-index-demo
```

The command prints the path to `reference_manifest.md` inside the output directory.

To index a permitted page, copy [the example configuration](src/visual_indexer/site_configs/example.json) to `source.json`, then set its `domain` and `selectors.content_core` values. The configured domain permits that host and its subdomains.

After reviewing [USAGE_POLICY.md](USAGE_POLICY.md):

```bash
visual-indexer index \
  https://your-domain.example/reference \
  --config source.json \
  --output ./references \
  --confirm-authorized
```

The explicit confirmation is required for network retrieval. It records intent; it does not replace permission or the source's terms.

## Practical usage

Run the offline demo first and inspect the generated manifest. It shows the output contract without contacting a website and is suitable for packaging or regression checks.

For a permitted source, keep each site configuration small and specific. Set the exact domain and the narrowest content selector that contains the references you need. Review the manifest after every run; the tool records URLs and source context, but it does not determine whether each asset may be downloaded, redistributed, or reused.

The local video helper is intentionally separate from the network CLI. Use it only with files you own or are authorized to process, and keep extracted frames within the same retention and licensing boundary as the source video.

## Retrieval policy

Before retrieval, the client checks the configured host, public DNS results, allowed ports, redirects, response size, and the requested page's robots policy. Connections use the validated address while retaining hostname verification for HTTPS. Empty or denying robots policies stop the request.

This design reduces common server-side request-forgery risks and accidental broad crawling, but it does not turn the tool into a general-purpose scraper. Operators remain responsible for authorization, terms, copyright, request frequency, and how manifests are used.

## Verification

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

Tests cover configuration, selectors, URL and address policy, redirect handling, response limits, robots behavior, manifest output, naming, and local video helpers.

## Repository map

| Path | Responsibility |
| --- | --- |
| `src/visual_indexer/main.py` | CLI routing for demo and authorized indexing |
| `src/visual_indexer/config.py` | Site-configuration loading and validation |
| `src/visual_indexer/policy.py` | URL, domain, address, port, and robots policy |
| `src/visual_indexer/fetch.py` | Bounded retrieval and redirect handling |
| `src/visual_indexer/output.py` | HTML indexing and Markdown manifest output |
| `src/visual_indexer/naming.py` | Stable source and run naming |
| `src/visual_indexer/video.py` | Optional inspection and frame extraction for local video |
| `tests/` | Synthetic policy, retrieval, output, naming, and video tests |
| `USAGE_POLICY.md` | Authorization, terms, copyright, and operational expectations |

## Project status

The indexer reads one HTML page without executing JavaScript. It does not crawl links or download referenced media. Creator and description configuration fields are reserved but are not currently extracted.

The Python video module can inspect local files with `ffprobe` and extract a bounded set of frames with `ffmpeg`. Those tools are optional and are not exposed as a CLI command in this release. Interfaces may change before 1.0.

See [SECURITY.md](SECURITY.md), [USAGE_POLICY.md](USAGE_POLICY.md), [CONTRIBUTING.md](CONTRIBUTING.md), and [CHANGELOG.md](CHANGELOG.md).

## Contributing, security, and license

Changes to network policy should include tests for the permitted path and the closest rejected path. Use only synthetic domains and fixtures in tests, issues, and pull requests; do not add scraped assets or private page content.

Report server-side request-forgery bypasses, redirect-policy failures, response-limit issues, unsafe local-file handling, or sensitive-data exposure through GitHub's private security-advisory channel.

Visual Indexer is available under the [MIT License](LICENSE).

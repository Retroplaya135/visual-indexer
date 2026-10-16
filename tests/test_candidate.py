import asyncio
import tempfile
import unittest
from pathlib import Path

from visual_indexer.config import SiteConfig
from visual_indexer.fetch import AuthorizedFetcher, _Response
from visual_indexer.isolation import extract
from visual_indexer.main import run_demo
from visual_indexer.naming import NamingContext
from visual_indexer.output import OutputStore
from visual_indexer.policy import AuthorizationPolicy


def public_resolver(host, port):
    return [(2, 1, 6, "", ("93.184.216.34", port))]


def private_resolver(host, port):
    return [(2, 1, 6, "", ("127.0.0.1", port))]


class CandidateTests(unittest.TestCase):
    def test_exact_host_boundary_and_authorization(self) -> None:
        policy = AuthorizationPolicy({"example.com"}, resolver=public_resolver)
        self.assertTrue(policy.evaluate_target("https://docs.example.com/x", operator_confirmed=True).allowed)
        self.assertFalse(policy.evaluate_target("https://example.com.evil.test/x", operator_confirmed=True).allowed)
        self.assertFalse(policy.evaluate_target("https://example.com/x", operator_confirmed=False).allowed)
        self.assertFalse(policy.evaluate_target("file:///tmp/x", operator_confirmed=True).allowed)

    def test_private_address_and_robots_are_denied(self) -> None:
        policy = AuthorizationPolicy({"example.com"}, resolver=private_resolver)
        self.assertFalse(policy.evaluate_target("https://example.com/x", operator_confirmed=True).allowed)
        public = AuthorizationPolicy({"example.com"}, resolver=public_resolver)
        robots = "User-agent: *\nDisallow: /private\nAllow: /"
        self.assertFalse(public.evaluate_robots("https://example.com/private/x", robots).allowed)
        self.assertTrue(public.evaluate_robots("https://example.com/public/x", robots).allowed)
        self.assertFalse(public.evaluate_robots("https://example.com/public/x", "").allowed)

    def test_fetcher_enforces_robots_redirect_and_size_limits(self) -> None:
        calls = []

        def exchange(target, limit, user_agent):
            calls.append((target.host, target.addresses, target.parsed.path, limit, user_agent))
            if target.parsed.path == "/robots.txt":
                return _Response(200, {"content-type": "text/plain"}, b"User-agent: *\nAllow: /")
            if target.parsed.path == "/start":
                return _Response(302, {"location": "/final"}, b"")
            return _Response(200, {"content-type": "text/html; charset=utf-8"}, b"<html><body>ok</body></html>")

        policy = AuthorizationPolicy({"example.com"}, resolver=public_resolver)
        fetcher = AuthorizedFetcher(policy, max_response_bytes=1000, exchange=exchange)
        result = asyncio.run(fetcher.fetch("https://example.com/start", operator_confirmed=True))
        self.assertEqual(result.url, "https://example.com/final")
        self.assertTrue(all(call[1] == ("93.184.216.34",) for call in calls))

        def too_large(target, limit, user_agent):
            if target.parsed.path == "/robots.txt":
                return _Response(200, {"content-type": "text/plain"}, b"User-agent: *\nAllow: /")
            return _Response(200, {"content-type": "text/html"}, b"x" * (limit + 1))

        with self.assertRaises(ValueError):
            asyncio.run(
                AuthorizedFetcher(policy, max_response_bytes=10, exchange=too_large).fetch(
                    "https://example.com/page", operator_confirmed=True
                )
            )

    def test_credentials_nonstandard_ports_and_redirect_escape_are_denied(self) -> None:
        policy = AuthorizationPolicy({"example.com"}, resolver=public_resolver)
        self.assertFalse(policy.evaluate_target("https://user@example.com/", operator_confirmed=True).allowed)
        self.assertFalse(policy.evaluate_target("https://example.com:8443/", operator_confirmed=True).allowed)

        def redirect_escape(target, limit, user_agent):
            if target.parsed.path == "/robots.txt":
                return _Response(200, {"content-type": "text/plain"}, b"User-agent: *\nAllow: /")
            return _Response(302, {"location": "https://evil.test/page"}, b"")

        with self.assertRaises(PermissionError):
            asyncio.run(
                AuthorizedFetcher(policy, exchange=redirect_escape).fetch(
                    "https://example.com/start", operator_confirmed=True
                )
            )

    def test_synthetic_extraction_and_contained_output(self) -> None:
        root = Path(__file__).parent
        html = (root / "fixtures/synthetic-site/index.html").read_text(encoding="utf-8")
        config = SiteConfig.from_json(root.parent / "src/visual_indexer/site_configs/example.json")
        result = extract(html, config, "https://example.invalid/reference")
        self.assertEqual(result.title, "Synthetic reference")
        self.assertEqual(result.images, ("https://example.invalid/assets/example.png",))
        with tempfile.TemporaryDirectory() as tmp:
            store = OutputStore(Path(tmp))
            manifest = store.write_manifest(
                "https://example.invalid/reference",
                config.name,
                NamingContext(project=result.title),
                result,
            )
            self.assertTrue(manifest.is_file())
            with self.assertRaises(ValueError):
                store.resolve("../escape")

    def test_offline_demo_writes_a_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            destination = run_demo(Path(tmp))
            self.assertTrue(destination.is_file())
            self.assertIn("https://example.invalid/reference", destination.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

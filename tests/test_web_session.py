"""Checks for the cookie-session credential loader.

Run: uv run python tests/test_web_session.py    (stdlib asserts, no pytest needed)
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from reddit_mcp import web_session as ws  # noqa: E402

SESSION = {"name": "reddit_session", "value": "V", "domain": ".reddit.com"}
FOREIGN = {"name": "_ga", "value": "X", "domain": ".google.com"}


def _write(tmp: str, payload, mode: int = 0o600) -> pathlib.Path:
    p = pathlib.Path(tmp) / "cookies.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    os.chmod(p, mode)
    return p


def test_domain_matcher_handles_subdomains():
    # The naive exact-or-".parent" matcher fails the first case, because the cookie
    # domain is *shorter* than the host, and every request silently goes out anon.
    assert ws.domain_matches(".reddit.com", "old.reddit.com")
    assert ws.domain_matches(".reddit.com", "reddit.com")
    assert ws.domain_matches("reddit.com", "www.reddit.com")
    assert ws.domain_matches(".reddit.com", "oauth.reddit.com")
    assert not ws.domain_matches(".example.com", "reddit.com")
    assert not ws.domain_matches(".reddit.com.evil.com", "reddit.com")
    assert not ws.domain_matches("", "reddit.com")


def test_accepts_both_export_shapes_and_drops_foreign_domains():
    with tempfile.TemporaryDirectory() as tmp:
        for payload in ([SESSION, FOREIGN], {"cookies": [SESSION, FOREIGN]}):
            jar = ws.load_cookies(str(_write(tmp, payload)))
            assert jar == {"reddit_session": "V"}, f"{payload!r} -> {jar!r}"


def test_mode_600_is_enforced_at_read_time():
    with tempfile.TemporaryDirectory() as tmp:
        for bad in (0o644, 0o640, 0o666):
            try:
                ws.load_cookies(str(_write(tmp, [SESSION], mode=bad)))
            except ws.SessionError as exc:
                assert "600" in str(exc), exc
            else:
                raise AssertionError(f"mode {bad:03o} was accepted")


def test_missing_and_unusable_files_are_actionable():
    with tempfile.TemporaryDirectory() as tmp:
        try:
            ws.load_cookies(str(pathlib.Path(tmp) / "absent.json"))
        except ws.SessionError as exc:
            assert "chmod" in str(exc) and "export" in str(exc).lower(), exc
        else:
            raise AssertionError("missing file accepted")

        try:
            ws.load_cookies(str(_write(tmp, [FOREIGN])))
        except ws.SessionError as exc:
            assert "no reddit.com cookies" in str(exc), exc
        else:
            raise AssertionError("foreign-only export accepted")

        broken = pathlib.Path(tmp, "broken.json")
        broken.write_text("{not json", encoding="utf-8")
        os.chmod(broken, 0o600)  # mode is checked before parsing, so set it 600
        try:
            ws.load_cookies(str(pathlib.Path(tmp) / "broken.json"))
        except ws.SessionError as exc:
            assert "JSON" in str(exc), exc
        else:
            raise AssertionError("malformed JSON accepted")


def test_requires_the_session_cookie_not_just_any_cookie():
    # The short-lived token alone does NOT authenticate (verified live: 302), so a
    # jar holding only it must fail loudly here rather than 302 mysteriously later.
    with tempfile.TemporaryDirectory() as tmp:
        only_token = [{"name": "token_v2", "value": "V", "domain": ".reddit.com"}]
        try:
            ws.load_cookies(str(_write(tmp, only_token)))
        except ws.SessionError as exc:
            assert "reddit_session" in str(exc), exc
        else:
            raise AssertionError("a token_v2-only jar was accepted")


def test_session_available_reports_cleanly():
    with tempfile.TemporaryDirectory() as tmp:
        assert not ws.session_available(str(pathlib.Path(tmp) / "absent.json"))
        assert ws.session_available(str(_write(tmp, [SESSION])))


if __name__ == "__main__":
    ran = 0
    for name in sorted(n for n in dir() if n.startswith("test_")):
        globals()[name]()
        print(f"  ok  {name}")
        ran += 1
    print(f"\nall {ran} loader checks passed")

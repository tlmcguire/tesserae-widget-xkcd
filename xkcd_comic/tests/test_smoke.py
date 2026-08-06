"""xkcd_comic: render smoke test plus fetch/cache/random-pick unit tests.

Mirrors the shape of plugins/news_rss/tests/test_smoke.py in the main
Tesserae repo: load server.py by path (so this test file runs standalone
against a plugin folder, not just inside the host's test suite), patch
urllib.request.urlopen so nothing hits the real network, and exercise
/_test/render across every supported size plus the server-side logic
directly.
"""

from __future__ import annotations

import importlib.util
import json
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest
from flask.testing import FlaskClient

_SPEC = importlib.util.spec_from_file_location(
    "xkcd_comic_server", Path(__file__).resolve().parent.parent / "server.py"
)
assert _SPEC is not None and _SPEC.loader is not None
srv = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(srv)

_LATEST = {
    "num": 3000,
    "safe_title": "Widget Testing",
    "img": "https://imgs.xkcd.com/comics/widget_testing.png",
    "alt": "This is the hovertext, printed in the open like it should always have been.",
    "year": "2026",
    "month": "8",
    "day": "5",
}

_COMIC_353 = {
    "num": 353,
    "safe_title": "Python",
    "img": "https://imgs.xkcd.com/comics/python.png",
    "alt": "I wrote 20 short programs in Python yesterday. It was wonderful. Perl, I'm leaving you.",
    "year": "2007",
    "month": "8",
    "day": "6",
}


class _FakeResp:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResp:  # noqa: PYI034 - matches urlopen's real return type
        return self

    def __exit__(self, *a: object) -> bool:
        return False


def _urlopen_for(payload: dict):
    def _fake(req, timeout=0):
        return _FakeResp(payload)

    return _fake


@pytest.mark.parametrize("size", ["sm", "md", "lg"])
def test_widget_renders(client: FlaskClient, size: str, tmp_path) -> None:
    with patch("urllib.request.urlopen", _urlopen_for(_LATEST)):
        resp = client.get(f"/_test/render?plugin=xkcd_comic&size={size}")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert 'data-plugin="xkcd_comic"' in body
    assert "Widget Testing" in body
    # The hovertext must appear as literal, visible text in the markup,
    # not just an alt="" attribute a mouse would need to hover to read.
    assert "printed in the open" in body


def test_shape_builds_a_date_and_page_link() -> None:
    shaped = srv._shape(_COMIC_353)
    assert shaped["date"] == "2007-08-06"
    assert shaped["link_page"] == "https://xkcd.com/353/"
    assert shaped["title"] == "Python"


def test_fixed_mode_fetches_the_requested_number(tmp_path) -> None:
    with patch("urllib.request.urlopen", _urlopen_for(_COMIC_353)):
        result = srv.fetch(
            {"mode": "fixed", "comic_number": 353}, {}, ctx={"data_dir": str(tmp_path)}
        )
    assert result["num"] == 353
    assert result["alt"].startswith("I wrote 20 short programs")


def test_fixed_mode_404_refuses_with_a_friendly_message(tmp_path) -> None:
    result = srv.fetch(
        {"mode": "fixed", "comic_number": 404}, {}, ctx={"data_dir": str(tmp_path)}
    )
    assert "error" in result
    assert "joke" in result["error"].lower()


def test_numbered_comic_is_cached_forever(tmp_path) -> None:
    calls = {"n": 0}

    def _counting_fake(req, timeout=0):
        calls["n"] += 1
        return _FakeResp(_COMIC_353)

    with patch("urllib.request.urlopen", _counting_fake):
        srv.fetch({"mode": "fixed", "comic_number": 353}, {}, ctx={"data_dir": str(tmp_path)})
        srv.fetch({"mode": "fixed", "comic_number": 353}, {}, ctx={"data_dir": str(tmp_path)})

    assert calls["n"] == 1


def test_random_mode_skips_the_joke_404(tmp_path) -> None:
    # random.randint is forced to land on 404 every time it's called; the
    # dodge must still resolve to some other comic, and the fetch for that
    # comic must be answered with a payload carrying its own real number,
    # not a copy-pasted 404 payload, so the assertion actually proves the
    # returned num came from the dodge path rather than from the mock.
    def _by_number(req, timeout=0):
        url = getattr(req, "full_url", "")
        if url == srv.LATEST_URL:
            return _FakeResp({**_LATEST, "num": 404})
        return _FakeResp({**_COMIC_353, "num": 403})

    with (
        patch("random.randint", return_value=404),
        patch("urllib.request.urlopen", _by_number),
    ):
        result = srv.fetch({"mode": "random"}, {}, ctx={"data_dir": str(tmp_path)})
    assert result["num"] == 403


def test_random_mode_reuses_its_pick_within_the_refresh_window(tmp_path) -> None:
    calls = {"n": 0}

    def _counting_fake(req, timeout=0):
        calls["n"] += 1
        url = getattr(req, "full_url", "")
        return _FakeResp(_LATEST if url == srv.LATEST_URL else _COMIC_353)

    with (
        patch("random.randint", return_value=353),
        patch("urllib.request.urlopen", _counting_fake),
    ):
        srv.fetch(
            {"mode": "random", "random_refresh_hours": 24}, {}, ctx={"data_dir": str(tmp_path)}
        )
        result = srv.fetch(
            {"mode": "random", "random_refresh_hours": 24}, {}, ctx={"data_dir": str(tmp_path)}
        )

    # First call: one hit for "latest" (to learn the upper bound) + one for
    # the numbered pick. Second call should reuse both caches untouched.
    assert calls["n"] == 2
    assert result["num"] == 353


def test_network_failure_is_translated_to_a_friendly_message(tmp_path) -> None:
    def _raise(req, timeout=0):
        raise urllib.error.URLError("no route to host")

    with patch("urllib.request.urlopen", _raise):
        result = srv.fetch({"mode": "latest"}, {}, ctx={"data_dir": str(tmp_path)})

    assert "error" in result
    assert "URLError" not in result["error"]  # translated, not the raw exception

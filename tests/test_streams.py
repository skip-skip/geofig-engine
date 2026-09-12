"""
Phase 18.3 wp1: stream web-API I/O (`io/streams.py`).

Covers the paginated USGS NHDPlus_HR REST query (URL params asserted, the
`exceededTransferLimit` page loop, the `max_pages` cap + truthful
`truncated` flag, bbox validation before any HTTP), the NaN-separated
multipart GeoJSON parse (LineString/MultiLineString fixtures, degenerate-part
skipping, trailing-separator trim, non-polyline/malformed raises), the
never-raise `fetch_streams` degrade, and the io-layer import discipline.
All network access goes through monkeypatched `requests.get` with canned
JSON payloads — no live calls.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest
import requests

import geofig_engine.io.streams as streams_mod
from geofig_engine.io.streams import (
    DEFAULT_STREAM_SERVICE_URL,
    StreamsError,
    fetch_streams,
    parse_lines,
    query_lines,
)


def _bbox(west=-116.55, south=41.18, east=-116.24, north=41.36):
    """A site-scale bbox around the example wells (US — NHD coverage)."""
    return (west, south, east, north)


def _line(coords):
    """A LineString feature (lon/lat vertex list)."""
    return {
        "geometry": {"type": "LineString", "coordinates": coords},
        "properties": {"ftype": 460},
    }


def _multi(parts):
    """A MultiLineString feature (list of lon/lat vertex lists)."""
    return {
        "geometry": {"type": "MultiLineString", "coordinates": parts},
        "properties": {"ftype": 460},
    }


def _payload(features, exceeded=False):
    """A canned GeoJSON-style query payload."""
    return {"features": features, "exceededTransferLimit": exceeded}


class FakeResponse:
    """A fake ``requests.Response`` (status + ``json()`` only)."""

    def __init__(self, payload=None, status_code=200, json_error=None):
        self._payload = payload
        self.status_code = status_code
        self._json_error = json_error

    def json(self):
        if self._json_error is not None:
            raise self._json_error
        return self._payload


class FakeRequests:
    """Records ``get`` calls and serves canned pages, then empty pages.

    Each ``pages`` entry is either a :class:`FakeResponse`, a payload (status
    200), or a ``(payload, status_code)`` tuple. Once exhausted, every
    further call returns an empty non-paginated payload.
    """

    def __init__(self, *pages):
        self.pages = list(pages)
        self.calls: list[dict] = []

    def get(self, url, params=None, timeout=None, headers=None):
        self.calls.append(
            {"url": url, "params": params, "timeout": timeout, "headers": headers}
        )
        if self.pages:
            item = self.pages.pop(0)
            if isinstance(item, FakeResponse):
                return item
            if isinstance(item, tuple):
                payload, status = item
            else:
                payload, status = item, 200
            return FakeResponse(payload, status_code=status)
        return FakeResponse(_payload([]))


@pytest.fixture
def fake_requests(monkeypatch):
    """Monkeypatch the global ``requests.get`` with a recording fake."""
    fake = FakeRequests()
    monkeypatch.setattr(requests, "get", fake.get)
    return fake


class TestQueryLines:
    def test_url_and_params(self, fake_requests):
        fake_requests.pages = [
            _payload([_line([[-116.4, 41.3], [-116.3, 41.3]])])
        ]
        features, truncated = query_lines(_bbox())
        assert not truncated
        call = fake_requests.calls[0]
        assert call["url"] == DEFAULT_STREAM_SERVICE_URL
        assert call["url"].endswith("/MapServer/3/query")
        params = call["params"]
        assert params["f"] == "geojson"
        assert params["geometryType"] == "esriGeometryEnvelope"
        assert params["inSR"] == 4326
        assert params["outSR"] == 4326
        assert params["where"] == "ftype = 460"
        assert params["returnGeometry"] == "true"
        assert params["outFields"] == "ftype"
        assert params["resultRecordCount"] == 2000
        assert params["resultOffset"] == 0
        assert json.loads(params["geometry"]) == {
            "xmin": -116.55,
            "ymin": 41.18,
            "xmax": -116.24,
            "ymax": 41.36,
            "spatialReference": {"wkid": 4326},
        }
        assert call["timeout"] == 30
        assert features == [_line([[-116.4, 41.3], [-116.3, 41.3]])]

    def test_single_page_no_pagination(self, fake_requests):
        fake_requests.pages = [_payload([_line([[0.0, 0.0], [1.0, 0.0]])])]
        features, truncated = query_lines(_bbox())
        assert len(fake_requests.calls) == 1
        assert not truncated
        assert len(features) == 1

    def test_paginates_while_exceeded(self, fake_requests):
        fake_requests.pages = [
            _payload([_line([[-116.4, 41.3], [-116.3, 41.3]])], exceeded=True),
            _payload([_line([[-116.2, 41.3], [-116.1, 41.3]])]),
        ]
        features, truncated = query_lines(_bbox())
        assert len(fake_requests.calls) == 2
        assert fake_requests.calls[1]["params"]["resultOffset"] == 2000
        assert len(features) == 2
        assert not truncated

    def test_caps_at_max_pages_and_flags_truncated(self, fake_requests):
        fake_requests.pages = [
            _payload([_line([[0.0, 0.0], [1.0, 0.0]])], exceeded=True),
            _payload([_line([[1.0, 0.0], [2.0, 0.0]])], exceeded=True),
            _payload([_line([[2.0, 0.0], [3.0, 0.0]])], exceeded=True),
        ]
        features, truncated = query_lines(_bbox(), max_pages=2)
        assert len(fake_requests.calls) == 2
        assert fake_requests.calls[1]["params"]["resultOffset"] == 2000
        assert truncated
        assert len(features) == 2

    def test_optional_layer_id_appended_to_bare_base_url(self, fake_requests):
        query_lines(_bbox(), service_url="https://example.invalid/MapServer")
        params = fake_requests.calls[0]["params"]
        assert fake_requests.calls[0]["url"] == (
            "https://example.invalid/MapServer/3/query"
        )
        assert params["resultOffset"] == 0

    def test_non_200_raises(self, fake_requests):
        fake_requests.pages = [(_payload([]), 500)]
        with pytest.raises(StreamsError, match="500"):
            query_lines(_bbox())

    def test_malformed_json_raises(self, fake_requests):
        fake_requests.pages = [FakeResponse(json_error=ValueError("no json"))]
        with pytest.raises(StreamsError, match="malformed JSON"):
            query_lines(_bbox())

    def test_payload_missing_features_raises(self, fake_requests):
        fake_requests.pages = [FakeResponse({"exceededTransferLimit": False})]
        with pytest.raises(StreamsError, match="features"):
            query_lines(_bbox())

    def test_bad_bbox_validated_before_any_http(self, fake_requests):
        bad_bboxes = [
            (-116.24, 41.18, -116.55, 41.36),  # west >= east
            (-116.55, 41.36, -116.24, 41.18),  # south >= north
            (-116.55, 41.18, -116.24),  # wrong length
            ("a", 41.18, -116.24, 41.36),  # non-numeric
            (-116.55, float("nan"), -116.24, 41.36),  # non-finite
        ]
        for bbox in bad_bboxes:
            with pytest.raises(ValueError):
                query_lines(bbox)
        assert fake_requests.calls == []  # validated before any HTTP call


class TestParseLines:
    def test_single_linestring(self):
        x, y = parse_lines(
            [_line([[-116.4, 41.3], [-116.3, 41.3], [-116.2, 41.3]])]
        )
        assert x == [-116.4, -116.3, -116.2]
        assert y == [41.3, 41.3, 41.3]

    def test_multilinestring_parts_open_with_single_nan_separator(self):
        x, y = parse_lines(
            [
                _multi(
                    [
                        [[-116.4, 41.3], [-116.3, 41.3]],
                        [[-116.2, 41.3], [-116.1, 41.3]],
                    ]
                )
            ]
        )
        assert len(x) == len(y) == 5
        assert x[:2] == [-116.4, -116.3]
        assert x[3:] == [-116.2, -116.1]
        assert math.isnan(x[2]) and math.isnan(y[2])
        # exactly one separator, and the trailing one is trimmed
        assert sum(math.isnan(v) for v in x) == 1
        assert not math.isnan(x[-1])

    def test_multiple_features_appended(self):
        x, y = parse_lines(
            [
                _line([[-116.4, 41.3], [-116.3, 41.3]]),
                _line([[-116.2, 41.3], [-116.1, 41.3]]),
            ]
        )
        assert len(x) == len(y) == 5
        assert math.isnan(x[2]) and math.isnan(y[2])
        assert not math.isnan(x[-1])

    def test_degenerate_parts_skipped(self):
        x, y = parse_lines(
            [
                _multi(
                    [
                        [],  # empty
                        [[-116.4, 41.3]],  # single point (<2 vertices)
                        [[-116.2, 41.3], [-116.1, 41.3]],
                    ]
                )
            ]
        )
        assert x == [-116.2, -116.1]
        assert y == [41.3, 41.3]
        assert sum(math.isnan(v) for v in x) == 0

    def test_all_degenerate_returns_empty(self):
        x, y = parse_lines([_multi([[], [[-116.4, 41.3]]])])
        assert x == [] and y == []

    def test_empty_features(self):
        assert parse_lines([]) == ([], [])

    def test_non_polyline_geometry_raises(self):
        point = {
            "geometry": {"type": "Point", "coordinates": [-116.4, 41.3]},
            "properties": {},
        }
        with pytest.raises(StreamsError, match="Point"):
            parse_lines([point])

    def test_missing_geometry_raises(self):
        with pytest.raises(StreamsError, match="geometry"):
            parse_lines([{"features": 1}])

    def test_malformed_vertex_raises(self):
        with pytest.raises(StreamsError, match="vertex"):
            parse_lines([_line([[-116.4, 41.3], ["bad", 41.3]])])


class TestFetchStreams:
    def test_happy_path_frame_shape(self, fake_requests):
        fake_requests.pages = [
            _payload(
                [
                    _multi(
                        [
                            [[-116.4, 41.3], [-116.3, 41.3]],
                            [[-116.2, 41.3], [-116.1, 41.3]],
                        ]
                    )
                ]
            )
        ]
        df = fetch_streams(_bbox())
        assert list(df.columns) == ["x", "y"]
        assert df["x"].dtype == np.float64
        assert df["y"].dtype == np.float64
        assert len(df) == 5
        assert math.isnan(df["x"].iloc[2])
        assert not math.isnan(df["x"].iloc[-1])

    def test_kwargs_forwarded_to_query(self, fake_requests):
        fake_requests.pages = [_payload([_line([[0.0, 0.0], [1.0, 0.0]])])]
        fetch_streams(_bbox(), service_url="https://example.invalid/MapServer")
        call = fake_requests.calls[0]
        assert call["url"] == "https://example.invalid/MapServer/3/query"

    def test_http_error_warns_and_empty(self, monkeypatch):
        def boom(url, params=None, timeout=None, headers=None):
            raise requests.ConnectionError("boom")

        monkeypatch.setattr(requests, "get", boom)
        with pytest.warns(UserWarning, match="streams unavailable"):
            df = fetch_streams(_bbox())
        assert list(df.columns) == ["x", "y"]
        assert df.empty

    def test_non_200_warns_and_empty(self, fake_requests):
        fake_requests.pages = [(_payload([]), 500)]
        with pytest.warns(UserWarning, match="streams unavailable"):
            df = fetch_streams(_bbox())
        assert df.empty

    def test_malformed_json_warns_and_empty(self, fake_requests):
        fake_requests.pages = [FakeResponse(json_error=ValueError("nope"))]
        with pytest.warns(UserWarning, match="streams unavailable"):
            df = fetch_streams(_bbox())
        assert df.empty

    def test_empty_features_warns_and_empty(self, fake_requests):
        fake_requests.pages = [_payload([])]
        with pytest.warns(UserWarning, match="streams unavailable"):
            df = fetch_streams(_bbox())
        assert list(df.columns) == ["x", "y"]
        assert df.empty

    def test_trivial_bbox_empty_without_http(self, fake_requests):
        df = fetch_streams((-116.55, 41.18, -116.55, 41.18))  # west == east
        assert list(df.columns) == ["x", "y"]
        assert df.empty
        assert fake_requests.calls == []

    def test_all_degenerate_warns_and_empty(self, fake_requests):
        fake_requests.pages = [_payload([_multi([[], [[-116.4, 41.3]]])])]
        with pytest.warns(UserWarning, match="streams unavailable"):
            df = fetch_streams(_bbox())
        assert df.empty


class TestImportDiscipline:
    def test_requests_import_is_lazy(self):
        # Function-level lazy imports never populate the module namespace, so
        # the attribute stays absent even after the fetch path has run.
        assert "requests" not in streams_mod.__dict__

    def test_no_renderer_or_upstream_imports_in_source(self):
        source = Path(streams_mod.__file__).read_text(encoding="utf-8")
        for banned in ("geodata", "geochemmodel", "renderers"):
            assert f"import {banned}" not in source
            assert f"from {banned}" not in source

    def test_module_imports_offline_without_banned_packages(self):
        # Top-of-module imports are stdlib + numpy + pandas only (all declared
        # dependencies); requests is imported lazily inside functions, so a
        # pure-offline `import geofig_engine.io.streams` succeeds without it.
        import ast

        tree = ast.parse(Path(streams_mod.__file__).read_text(encoding="utf-8"))
        module_level = set()
        for node in tree.body:  # top-level statements only (no function bodies)
            if isinstance(node, ast.Import):
                module_level.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                module_level.add(node.module.split(".")[0])
        assert "requests" not in module_level
        assert "geodata" not in module_level
        assert "geochemmodel" not in module_level
        assert "matplotlib" not in module_level
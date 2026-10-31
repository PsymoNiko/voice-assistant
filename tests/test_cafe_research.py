import sqlite3

import pytest

from apps.cafe_research import osm, store
from apps.cafe_research.mcp_server import _slug, _validate_url


def test_slug_and_url_validation():
    assert _slug("Café Meridian") == "cafe-meridian"
    assert _slug("   ") == ""
    assert _validate_url("https://example.com/menu", "menu_url") == (
        "https://example.com/menu"
    )
    with pytest.raises(ValueError, match="public http or https"):
        _validate_url("javascript:alert(1)", "menu_url")


def test_saved_leads_are_searchable_and_upserted_by_osm_id(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "CAFE_RESEARCH_DB_PATH", str(tmp_path / "cafe-research.sqlite3")
    )
    first = _lead(name="First name")
    saved_first = store.save_lead(first)
    updated = store.save_lead({**first, "name": "Updated name"})

    results = store.find_leads("Updated", 10)
    assert saved_first["id"] == updated["id"]
    assert updated["name"] == "Updated name"
    assert updated["field_sources"] == {
        "name": "https://example.com/about",
    }
    assert updated["menu_summary"] == "Coffee, tea, and pastries"
    assert updated["checked_at"]
    assert len(results) == 1
    assert results[0]["osm_id"] == 123


def test_initialize_migrates_older_local_memory_schema(tmp_path, monkeypatch):
    path = tmp_path / "older.sqlite3"
    monkeypatch.setenv("CAFE_RESEARCH_DB_PATH", str(path))
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE cafe_leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                osm_type TEXT,
                osm_id INTEGER,
                name TEXT NOT NULL,
                slug TEXT NOT NULL,
                address TEXT NOT NULL DEFAULT '',
                city TEXT NOT NULL DEFAULT '',
                region TEXT NOT NULL DEFAULT '',
                country TEXT NOT NULL DEFAULT '',
                latitude REAL,
                longitude REAL,
                phone TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                website_url TEXT NOT NULL DEFAULT '',
                menu_url TEXT NOT NULL DEFAULT '',
                logo_url TEXT NOT NULL DEFAULT '',
                cuisine TEXT NOT NULL DEFAULT '',
                opening_hours TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'new',
                notes TEXT NOT NULL DEFAULT '',
                field_sources TEXT NOT NULL DEFAULT '{}',
                demo_url TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(osm_type, osm_id)
            )
            """
        )
        connection.execute(
            """
            INSERT INTO cafe_leads (name, slug, city, demo_url, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "Existing Cafe",
                "existing-cafe",
                "Test City",
                "https://beanscoin.cafe/cafe/existing-cafe",
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
            ),
        )

    store.initialize()
    result = store.find_leads("Existing Cafe", 1)[0]

    assert result["checked_at"] == "2026-01-01T00:00:00+00:00"
    assert result["menu_summary"] == ""


def test_map_search_caches_geocoding_and_overpass_results(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "CAFE_RESEARCH_DB_PATH", str(tmp_path / "cafe-research.sqlite3")
    )
    monkeypatch.setattr(osm, "wait_for_nominatim_slot", lambda: None)
    calls = []

    def fake_request(url, *, data=None, timeout=20):
        calls.append(url)
        if "nominatim" in url:
            return [
                {
                    "display_name": "Sample District, Example City",
                    "boundingbox": ["1.0", "1.1", "2.0", "2.1"],
                }
            ]
        return {
            "elements": [
                {
                    "type": "node",
                    "id": 123,
                    "lat": 1.05,
                    "lon": 2.05,
                    "tags": {
                        "amenity": "cafe",
                        "name": "Example Cafe",
                        "phone": "+100000000",
                        "website": "https://example.com",
                    },
                }
            ]
        }

    monkeypatch.setattr(osm, "_request_json", fake_request)

    first = osm.search_cafes("Sample District, Example City", "cafe", 10)
    second = osm.search_cafes("Sample District, Example City", "cafe", 10)

    assert len(calls) == 2
    assert first == second
    assert first["resolved_area"] == "Sample District, Example City"
    assert first["results"][0]["name"] == "Example Cafe"
    assert first["results"][0]["source_url"].endswith("/node/123")
    assert "OpenStreetMap contributors" in first["attribution"]


def test_map_search_rejects_broad_areas(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "CAFE_RESEARCH_DB_PATH", str(tmp_path / "cafe-research.sqlite3")
    )
    monkeypatch.setattr(
        osm,
        "_geocode",
        lambda _: {
            "display_name": "A broad region",
            "boundingbox": ["0", "2", "0", "2"],
        },
    )
    with pytest.raises(ValueError, match="too broad"):
        osm.search_cafes("A broad region", "all", 10)


def _lead(name: str) -> dict:
    return {
        "osm_type": "node",
        "osm_id": 123,
        "name": name,
        "slug": "example-cafe",
        "address": "1 Test Street",
        "city": "Test City",
        "region": "",
        "country": "",
        "latitude": 1.0,
        "longitude": 2.0,
        "phone": "",
        "email": "",
        "website_url": "",
        "menu_url": "",
        "menu_summary": "Coffee, tea, and pastries",
        "logo_url": "",
        "cuisine": "",
        "opening_hours": "",
        "status": "new",
        "notes": "",
        "field_sources": {"name": "https://example.com/about"},
        "demo_url": "https://beanscoin.cafe/cafe/example-cafe",
    }

"""User-triggered, cached cafe searches using OpenStreetMap data."""

from __future__ import annotations

import json
import os
from datetime import timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from apps.cafe_research.store import (
    get_cached_json,
    set_cached_json,
    wait_for_nominatim_slot,
)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OSM_ATTRIBUTION = "© OpenStreetMap contributors, ODbL"
NOMINATIM_CACHE_TTL = timedelta(days=30)
OVERPASS_CACHE_TTL = timedelta(days=7)
MAX_BBOX_AREA = 0.04


def search_cafes(area: str, category: str, limit: int) -> dict[str, Any]:
    area = area.strip()
    if not area:
        raise ValueError("Enter a specific city, district, or neighborhood.")
    if category not in {"all", "cafe", "restaurant"}:
        raise ValueError("category must be all, cafe, or restaurant.")
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50.")

    geocoded = _geocode(area)
    bounds = _bounds(geocoded)
    south, west, north, east = bounds
    if (north - south) * (east - west) > MAX_BBOX_AREA:
        raise ValueError(
            "That area is too broad for a bounded public map lookup. "
            "Try a city district or neighborhood instead."
        )

    query = _overpass_query(bounds, category)
    cache_key = f"overpass:{category}:{','.join(f'{value:.5f}' for value in bounds)}"
    elements = get_cached_json(cache_key)
    if elements is None:
        elements = _fetch_overpass(query)
        set_cached_json(cache_key, elements, OVERPASS_CACHE_TTL)

    places = [_normalize_element(item) for item in elements]
    places = [place for place in places if place["name"]]
    places.sort(key=lambda place: place["name"].casefold())
    return {
        "resolved_area": geocoded["display_name"],
        "category": category,
        "result_count": min(len(places), limit),
        "results": places[:limit],
        "attribution": OSM_ATTRIBUTION,
        "license_url": "https://www.openstreetmap.org/copyright",
        "limitations": (
            "Map records may omit phone, website, menu, or logo details. "
            "Verify missing or changing details with the business's official sources."
        ),
    }


def _geocode(area: str) -> dict[str, Any]:
    cache_key = f"nominatim:{area.casefold()}"
    cached = get_cached_json(cache_key)
    if cached is not None:
        return cached

    wait_for_nominatim_slot()
    query = urlencode({"q": area, "format": "jsonv2", "limit": 1, "addressdetails": 1})
    result = _request_json(f"{NOMINATIM_URL}?{query}")
    if not isinstance(result, list) or not result:
        raise ValueError(f"No map area could be resolved for {area!r}.")
    set_cached_json(cache_key, result[0], NOMINATIM_CACHE_TTL)
    return result[0]


def _bounds(geocoded: dict[str, Any]) -> tuple[float, float, float, float]:
    raw = geocoded.get("boundingbox")
    if not isinstance(raw, list) or len(raw) != 4:
        raise ValueError("The map result did not contain a usable search boundary.")
    try:
        south, north, west, east = (float(value) for value in raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("The map result contained an invalid search boundary.") from exc
    if south > north or west > east:
        raise ValueError("The map result contained an invalid search boundary.")
    return south, west, north, east


def _overpass_query(
    bounds: tuple[float, float, float, float], category: str
) -> str:
    south, west, north, east = (f"{coordinate:.6f}" for coordinate in bounds)
    box = f"({south},{west},{north},{east})"
    amenities = ("cafe", "restaurant") if category == "all" else (category,)
    selectors = "\n".join(
        f'  nwr["amenity"="{amenity}"]{box};' for amenity in amenities
    )
    return f"[out:json][timeout:25];\n(\n{selectors}\n);\nout center tags;"


def _fetch_overpass(query: str) -> list[dict[str, Any]]:
    response = _request_json(
        OVERPASS_URL,
        data=urlencode({"data": query}).encode(),
        timeout=40,
    )
    elements = response.get("elements") if isinstance(response, dict) else None
    if not isinstance(elements, list):
        raise TypeError("The map service returned an unexpected cafe search response.")
    return elements


def _request_json(
    url: str, *, data: bytes | None = None, timeout: int = 20
) -> Any:
    user_agent = os.environ.get(
        "CAFE_RESEARCH_USER_AGENT", "BeansCafeResearch/0.1 (OpenCode local research)"
    )
    headers = {"User-Agent": user_agent, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = Request(url, data=data, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"Map service returned HTTP {exc.code}.") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach the map service: {exc.reason}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Map service returned invalid JSON.") from exc


def _normalize_element(element: dict[str, Any]) -> dict[str, Any]:
    tags = element.get("tags") or {}
    center = element.get("center") or element
    address_parts = [
        " ".join(part for part in (tags.get("addr:housenumber"), tags.get("addr:street")) if part),
        tags.get("addr:suburb") or tags.get("addr:district"),
        tags.get("addr:city") or tags.get("addr:town") or tags.get("addr:village"),
        tags.get("addr:state") or tags.get("addr:province"),
        tags.get("addr:country"),
    ]
    address = ", ".join(part for part in address_parts if part)
    osm_type = element.get("type", "")
    osm_id = element.get("id")
    return {
        "name": tags.get("name", ""),
        "category": tags.get("amenity", ""),
        "address": address,
        "city": (
            tags.get("addr:city") or tags.get("addr:town") or tags.get("addr:village", "")
        ),
        "region": tags.get("addr:state") or tags.get("addr:province", ""),
        "country": tags.get("addr:country", ""),
        "latitude": center.get("lat"),
        "longitude": center.get("lon"),
        "phone": tags.get("phone") or tags.get("contact:phone", ""),
        "email": tags.get("email") or tags.get("contact:email", ""),
        "website_url": tags.get("website") or tags.get("contact:website", ""),
        "menu_url": tags.get("menu") or tags.get("contact:menu", ""),
        "logo_url": tags.get("logo", ""),
        "cuisine": tags.get("cuisine", ""),
        "opening_hours": tags.get("opening_hours", ""),
        "osm_type": osm_type,
        "osm_id": osm_id,
        "source_url": f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
    }

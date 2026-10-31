"""OpenCode MCP tools for cafe discovery and source-aware lead memory."""

from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

from mcp.server.fastmcp import FastMCP

from apps.cafe_research.osm import OSM_ATTRIBUTION, search_cafes
from apps.cafe_research.store import find_leads, initialize, save_lead

DEMO_BASE_URL = "https://beanscoin.cafe/cafe"
ALLOWED_STATUSES = {"new", "reviewed", "contacted", "qualified", "not_fit"}
SOURCE_FIELDS = {
    "name",
    "address",
    "city",
    "region",
    "country",
    "phone",
    "email",
    "website_url",
    "menu_url",
    "menu_summary",
    "logo_url",
    "cuisine",
    "opening_hours",
    "map_record",
}

mcp = FastMCP("beans-cafe-research")


@mcp.tool()
def search_cafes_on_map(
    area: str, category: str = "all", limit: int = 25
) -> str:
    """Find cafes or restaurants in one specific city district using OpenStreetMap.

    This is an on-demand, bounded search, not a worldwide or systematic crawler.
    Returned map records may lack menu, logo, and contact details.
    """
    return json.dumps(search_cafes(area, category, limit), ensure_ascii=False)


@mcp.tool()
def save_cafe_lead(
    name: str,
    osm_type: str = "",
    osm_id: int | None = None,
    slug: str = "",
    address: str = "",
    city: str = "",
    region: str = "",
    country: str = "",
    latitude: float | None = None,
    longitude: float | None = None,
    phone: str = "",
    email: str = "",
    website_url: str = "",
    menu_url: str = "",
    menu_summary: str = "",
    logo_url: str = "",
    cuisine: str = "",
    opening_hours: str = "",
    status: str = "new",
    notes: str = "",
    field_sources: dict[str, str] | None = None,
) -> str:
    """Save a reviewed business lead and its public source links to local SQLite memory."""
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("name is required.")
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"status must be one of: {', '.join(sorted(ALLOWED_STATUSES))}.")
    if bool(osm_type) != (osm_id is not None):
        raise ValueError("Provide both osm_type and osm_id, or neither.")
    if osm_type and osm_type not in {"node", "way", "relation"}:
        raise ValueError("osm_type must be node, way, or relation.")
    if osm_id is not None and osm_id <= 0:
        raise ValueError("osm_id must be a positive integer.")
    if (latitude is None) != (longitude is None):
        raise ValueError("Provide both latitude and longitude, or neither.")
    if latitude is not None and not (-90 <= latitude <= 90):
        raise ValueError("latitude must be between -90 and 90.")
    if longitude is not None and not (-180 <= longitude <= 180):
        raise ValueError("longitude must be between -180 and 180.")

    clean_sources: dict[str, str] = {}
    for field, source in (field_sources or {}).items():
        if field not in SOURCE_FIELDS:
            raise ValueError(f"Unsupported source field: {field}.")
        clean_sources[field] = _validate_url(source, f"field_sources[{field}]")
    if osm_type and osm_id:
        clean_sources.setdefault(
            "map_record", f"https://www.openstreetmap.org/{osm_type}/{osm_id}"
        )

    clean_slug = _slug(slug or clean_name)
    if not clean_slug:
        clean_slug = f"cafe-{osm_id}" if osm_id else "cafe"
    lead = {
        "osm_type": osm_type or None,
        "osm_id": osm_id,
        "name": clean_name,
        "slug": clean_slug,
        "address": address.strip(),
        "city": city.strip(),
        "region": region.strip(),
        "country": country.strip(),
        "latitude": latitude,
        "longitude": longitude,
        "phone": phone.strip(),
        "email": email.strip(),
        "website_url": _optional_url(website_url, "website_url"),
        "menu_url": _optional_url(menu_url, "menu_url"),
        "menu_summary": menu_summary.strip(),
        "logo_url": _optional_url(logo_url, "logo_url"),
        "cuisine": cuisine.strip(),
        "opening_hours": opening_hours.strip(),
        "status": status,
        "notes": notes.strip(),
        "field_sources": clean_sources,
        "demo_url": f"{DEMO_BASE_URL}/{quote(clean_slug, safe='-')}",
    }
    saved = save_lead(lead)
    return json.dumps(
        {
            "saved": True,
            "lead": saved,
            "demo_url_note": (
                "This follows the requested cafe route. A cafe-specific demo may still "
                "need to be provisioned in the product."
            ),
        },
        ensure_ascii=False,
    )


@mcp.tool()
def find_saved_cafes(query: str = "", limit: int = 25) -> str:
    """Search the persistent BEANS cafe lead memory by name, location, or cuisine."""
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100.")
    results = find_leads(query, limit)
    return json.dumps({"results": results, "result_count": len(results)}, ensure_ascii=False)


@mcp.tool()
def get_beans_product_context(cafe_name: str = "", cafe_slug: str = "") -> str:
    """Return source-backed product facts and a cafe-specific demo URL."""
    profile_path = os.environ.get(
        "CAFE_RESEARCH_PRODUCT_PROFILE",
        "../BEANS/beans-cafe-ads/memory/product-profile.json",
    )
    path = Path(profile_path).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    try:
        profile: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Product profile not found at {path}.") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Product profile at {path} is not valid JSON.") from exc

    slug = _slug(cafe_slug or cafe_name) if cafe_slug or cafe_name else ""
    result = {
        "product": profile,
        "demo_url": f"{DEMO_BASE_URL}/{quote(slug, safe='-')}" if slug else DEMO_BASE_URL,
        "map_attribution": OSM_ATTRIBUTION,
    }
    return json.dumps(result, ensure_ascii=False)


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", normalized.casefold())).strip("-")


def _optional_url(value: str, field: str) -> str:
    return _validate_url(value, field) if value.strip() else ""


def _validate_url(value: str, field: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field} must be a public http or https URL.")
    return value.strip()


def main() -> None:
    initialize()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

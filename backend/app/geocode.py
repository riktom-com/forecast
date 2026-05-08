"""
Geocode arbitrary place strings to lat/lon.

Uses Open-Meteo's free geocoding API (handles cities, place names, and US zip
codes), with a Nominatim/OpenStreetMap fallback for addresses Open-Meteo
doesn't recognize.
"""
import re
import httpx

OPEN_METEO_GEO = "https://geocoding-api.open-meteo.com/v1/search"
NOMINATIM = "https://nominatim.openstreetmap.org/search"

_DIRECT_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")


def _try_direct(q: str):
    m = _DIRECT_RE.match(q)
    if not m:
        return None
    lat, lon = float(m.group(1)), float(m.group(2))
    if -90 <= lat <= 90 and -180 <= lon <= 180:
        return {
            "name": f"{lat:.4f}, {lon:.4f}",
            "latitude": lat,
            "longitude": lon,
            "source": "direct",
        }
    return None


async def _open_meteo(q: str, client: httpx.AsyncClient):
    r = await client.get(
        OPEN_METEO_GEO,
        params={"name": q, "count": 5, "language": "en", "format": "json"},
    )
    r.raise_for_status()
    data = r.json()
    out = []
    for hit in data.get("results", [])[:5]:
        parts = [hit.get("name")]
        if hit.get("admin1"):
            parts.append(hit["admin1"])
        if hit.get("country_code"):
            parts.append(hit["country_code"])
        out.append({
            "name": ", ".join(p for p in parts if p),
            "latitude": hit["latitude"],
            "longitude": hit["longitude"],
            "source": "open-meteo",
        })
    return out


async def _nominatim(q: str, client: httpx.AsyncClient):
    r = await client.get(
        NOMINATIM,
        params={"q": q, "format": "json", "limit": 5, "addressdetails": 0},
        headers={"User-Agent": "riktom-forecast/0.1 (https://riktom.com)"},
    )
    r.raise_for_status()
    data = r.json()
    return [
        {
            "name": hit.get("display_name", q),
            "latitude": float(hit["lat"]),
            "longitude": float(hit["lon"]),
            "source": "nominatim",
        }
        for hit in data[:5]
    ]


async def lookup(q: str) -> list[dict]:
    direct = _try_direct(q)
    if direct:
        return [direct]

    async with httpx.AsyncClient(timeout=10.0) as client:
        results = await _open_meteo(q, client)
        if results:
            return results
        # Open-Meteo missed — try Nominatim (handles street addresses and
        # some zip-code edge cases Open-Meteo doesn't).
        return await _nominatim(q, client)

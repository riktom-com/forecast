"""
Open-Meteo weather data client with in-process TTL cache.
Free, no API key required.
"""
import time
import httpx

_CACHE: dict = {}
_TTL_SECONDS = 30 * 60  # 30 min — weather updates hourly

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


async def fetch_weather(lat: float, lon: float, tz: str = "America/New_York") -> dict:
    cache_key = (round(lat, 3), round(lon, 3), tz)
    now = time.time()
    cached = _CACHE.get(cache_key)
    if cached and (now - cached[0]) < _TTL_SECONDS:
        return cached[1]

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join([
            "temperature_2m", "apparent_temperature",
            "precipitation_probability", "precipitation",
            "weathercode", "surface_pressure",
            "cloudcover", "windspeed_10m", "winddirection_10m",
            "soil_temperature_0cm", "soil_temperature_6cm",
        ]),
        "daily": ",".join([
            "sunrise", "sunset",
            "temperature_2m_max", "temperature_2m_min",
        ]),
        "past_days": 2,
        "forecast_days": 4,
        "timezone": tz,
        "temperature_unit": "fahrenheit",
        "windspeed_unit": "mph",
        "precipitation_unit": "inch",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(OPEN_METEO_URL, params=params)
        r.raise_for_status()
        data = r.json()

    _CACHE[cache_key] = (now, data)
    return data

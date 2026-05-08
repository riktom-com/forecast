"""
FastAPI app for the riktom.com hunt + fish forecast.
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import scoring, weather, profiles

app = FastAPI(
    title="riktom forecast",
    description="Research-weighted 24-hour hunt + fish activity forecast.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"ok": True}


@app.get("/api/profiles")
async def list_profiles():
    return {
        name: {
            "name": p.name,
            "label": p.label,
            "emoji": p.emoji,
            "weights": p.weights,
            "factor_labels": p.factor_labels,
        }
        for name, p in profiles.PROFILES.items()
    }


@app.get("/api/forecast")
async def get_forecast(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    species: str = Query("fish", pattern="^(fish|hunt)$"),
):
    if species not in profiles.PROFILES:
        raise HTTPException(400, f"Unknown species: {species}")
    try:
        wx = await weather.fetch_weather(lat, lon)
    except Exception as e:
        raise HTTPException(502, f"Weather data unavailable: {e}")
    return scoring.build_forecast(wx, species, lon)

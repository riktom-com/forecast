"""
Scoring engine — runs a profile's factor functions over 24h of weather data
and produces composite hourly scores.
"""
from datetime import datetime, timedelta, timezone
from . import profiles, solunar


def rating(score: int) -> str:
    if score >= 80:
        return "EXCELLENT"
    if score >= 65:
        return "GOOD"
    if score >= 50:
        return "MODERATE"
    if score >= 35:
        return "FAIR"
    return "POOR"


def composite(scores: dict, weights: dict) -> int:
    raw = sum(scores[k] * weights[k] for k in weights if k in scores)
    mx = sum(10 * v for v in weights.values())
    return round(raw / mx * 100)


def _factor_scores_fish(hourly, i, hour, sr_h, ss_h, periods, m_score):
    soil = (hourly.get("soil_temperature_0cm") or [None] * len(hourly["time"]))[i]
    air = hourly["temperature_2m"][i]
    wind = hourly["windspeed_10m"][i]
    cloud = hourly["cloudcover"][i]
    p_hist = hourly["surface_pressure"][max(0, i - 12):i + 1]
    t_hist = hourly["temperature_2m"][max(0, i - 24):i + 1]
    fp_hist = hourly["surface_pressure"][max(0, i - 24):i + 1]

    wt_s, wt_est = profiles.fish_water_temp(soil, air)
    fr_s, fr_cond = profiles.fish_front(t_hist, fp_hist)
    t_local = datetime.fromisoformat(hourly["time"][i])
    return {
        "water_temp":     wt_s,
        "front":          fr_s,
        "time_of_day":    profiles.fish_time_of_day(hour, sr_h, ss_h),
        "wind":           profiles.fish_wind(wind),
        "solunar":        solunar.solunar_score_at(t_local, periods),
        "pressure_trend": profiles.pressure_trend_score(p_hist),
        "moon_phase":     m_score,
        "cloud_cover":    profiles.cloud_score_fish(cloud, hour, sr_h, ss_h),
    }, fr_cond, wt_est


def _factor_scores_hunt(hourly, i, hour, sr_h, ss_h, periods, m_score):
    air = hourly["temperature_2m"][i]
    wind = hourly["windspeed_10m"][i]
    cloud = hourly["cloudcover"][i]
    p_hist = hourly["surface_pressure"][max(0, i - 12):i + 1]
    t_hist = hourly["temperature_2m"][max(0, i - 24):i + 1]
    fp_hist = hourly["surface_pressure"][max(0, i - 24):i + 1]

    fr_s, fr_cond = profiles.hunt_front(t_hist, fp_hist)
    t_local = datetime.fromisoformat(hourly["time"][i])
    return {
        "time_of_day":    profiles.hunt_time_of_day(hour, sr_h, ss_h),
        "front":          fr_s,
        "temp_drop":      profiles.hunt_temp_drop(t_hist, air),
        "wind":           profiles.hunt_wind(wind),
        "pressure_trend": profiles.pressure_trend_score(p_hist),
        "moon_phase":     m_score,
        "solunar":        solunar.solunar_score_at(t_local, periods),
        "cloud_cover":    profiles.cloud_score_hunt(cloud, hour, sr_h, ss_h),
    }, fr_cond, None


def build_forecast(weather: dict, profile_name: str, lon: float) -> dict:
    profile = profiles.PROFILES[profile_name]
    hourly = weather["hourly"]
    daily = weather["daily"]
    h_times = [datetime.fromisoformat(t) for t in hourly["time"]]

    now_utc = datetime.now(timezone.utc)
    tz_off = -4 if solunar.is_dst(now_utc) else -5
    now_local = now_utc + timedelta(hours=tz_off)
    today_str = now_local.strftime("%Y-%m-%d")

    today_idx = next((i for i, d in enumerate(daily["time"]) if d == today_str), 2)
    sr_dt = datetime.fromisoformat(daily["sunrise"][today_idx])
    ss_dt = datetime.fromisoformat(daily["sunset"][today_idx])
    sr_h = sr_dt.hour + sr_dt.minute / 60
    ss_h = ss_dt.hour + ss_dt.minute / 60

    today = now_local.date()
    periods = solunar.get_solunar_periods(today, lon, tz_off)
    phase, phase_name, illum = solunar.moon_phase(today)
    m_score = solunar.moon_phase_score(phase)

    start_idx = next(
        (i for i, t in enumerate(h_times)
         if datetime(t.year, t.month, t.day, t.hour, t.minute) >= now_local.replace(tzinfo=None)),
        0,
    )

    scorer = _factor_scores_fish if profile_name == "fish" else _factor_scores_hunt
    rows = []
    for i in range(start_idx, min(start_idx + 24, len(h_times))):
        t = h_times[i]
        hour = t.hour + t.minute / 60
        scores, condition, wt_est = scorer(hourly, i, hour, sr_h, ss_h, periods, m_score)
        total = composite(scores, profile.weights)
        rows.append({
            "time": t.isoformat(),
            "hour_label": t.strftime("%-I %p").lower(),
            "score": total,
            "rating": rating(total),
            "factors": {k: round(scores[k], 1) for k in scores},
            "weather": {
                "air_f":    round(hourly["temperature_2m"][i], 1),
                "wind_mph": round(hourly["windspeed_10m"][i]),
                "cloud_pct": round(hourly["cloudcover"][i]),
                "precip_pct": round((hourly.get("precipitation_probability") or [0] * len(h_times))[i]),
            },
            "condition": condition,
            "solunar": solunar.solunar_label(t, periods),
            "water_temp_f": round(wt_est, 1) if wt_est else None,
        })

    best_windows = []
    seen_hours = set()
    for r in sorted(rows, key=lambda x: x["score"], reverse=True):
        h = datetime.fromisoformat(r["time"]).hour + datetime.fromisoformat(r["time"]).minute / 60
        if not any(abs(h - sh) < 2 for sh in seen_hours):
            best_windows.append({
                "time": r["time"],
                "hour_label": r["hour_label"],
                "score": r["score"],
                "rating": r["rating"],
                "solunar": r["solunar"],
            })
            seen_hours.add(h)
        if len(best_windows) == 4:
            break
    best_windows.sort(key=lambda x: x["time"])

    return {
        "profile": {
            "name": profile.name,
            "label": profile.label,
            "emoji": profile.emoji,
            "weights": profile.weights,
            "factor_labels": profile.factor_labels,
        },
        "now_local": now_local.isoformat(),
        "moon": {
            "phase_name": phase_name,
            "illumination_pct": round(illum),
        },
        "sun": {
            "sunrise": sr_dt.isoformat(),
            "sunset":  ss_dt.isoformat(),
        },
        "solunar_periods": [
            {"start": s.isoformat(), "end": e.isoformat(), "kind": k}
            for s, e, k in sorted(periods, key=lambda x: x[0])
        ],
        "hourly": rows,
        "best_windows": best_windows,
    }

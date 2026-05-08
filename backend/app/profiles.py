"""
Scoring profiles for different activities.

Each profile defines:
- name, label, emoji for UI
- factor weights (must sum to ~1.0)
- scoring functions per factor (0-10 scale)

Fish profile is ported from hahirafish (research-weighted).
Hunt profile is whitetail-tuned with adjusted weights and scoring functions.
"""
from dataclasses import dataclass, field
from typing import Callable, Dict


# ── FISH SCORING FUNCTIONS ────────────────────────────────────────────

def fish_water_temp(soil_f, air_f):
    """Optimal 68-82°F for largemouth/catfish/bream."""
    wt = soil_f if soil_f else air_f * 0.65 + 22
    if 68 <= wt <= 82:
        s = 10
    elif 60 <= wt < 68:
        s = 10 - (68 - wt) * 0.5
    elif 82 < wt <= 88:
        s = 10 - (wt - 82) * 0.8
    elif 50 <= wt < 60:
        s = max(0, 4 - (60 - wt) * 0.3)
    elif wt > 88:
        s = max(0, 5 - (wt - 88) * 1.5)
    else:
        s = max(0, 2 - (50 - wt) * 0.3)
    return min(10, max(0, s)), wt


def fish_wind(mph):
    """Light-moderate wind oxygenates water; heavy wind = chop reduces fishing."""
    if mph < 2:
        return 2
    elif mph <= 8:
        return 8 + (mph - 2) / 6 * 2
    elif mph <= 15:
        return 10 - (mph - 8) / 7 * 3
    elif mph <= 25:
        return 7 - (mph - 15) / 10 * 4
    return max(0, 3 - (mph - 25) * 0.2)


def fish_time_of_day(hour, sr, ss):
    """Dawn/dusk peak feeding. Midday slow."""
    if sr - 0.5 <= hour <= sr + 1.5:
        t = (hour - (sr - 0.5)) / 2 if hour <= sr else 1 - (hour - sr) / 1.5
        return 7 + t * 3
    if ss - 1.5 <= hour <= ss + 0.5:
        t = (hour - (ss - 1.5)) / 1.25 if hour <= ss - 0.25 else 1 - (hour - (ss - 0.25)) / 0.75
        return 6 + t * 4
    if sr + 1.5 < hour <= 11:
        return max(3, 6 - (hour - (sr + 1.5)) * 0.5)
    if 11 < hour <= 14:
        return max(2, 4 - (hour - 11) * 0.5)
    if 14 < hour < ss - 1.5:
        return 2 + (hour - 14) / (ss - 15.5) * 3
    return 1


def fish_front(t_hist, p_hist):
    """24h temp and pressure trends → front classification."""
    if len(t_hist) < 6:
        return 5, "stable"
    t_chg24 = t_hist[-1] - t_hist[0]
    p_chg24 = (p_hist[-1] - p_hist[0]) if len(p_hist) >= len(t_hist) else 0
    t_chg6 = t_hist[-1] - t_hist[max(0, len(t_hist) - 7)]
    if t_chg24 < -8 and p_chg24 > 3:
        return 1, "post-cold-front (tough bite)"
    elif t_chg24 < -5:
        return 2, "cold front recovery"
    elif p_chg24 < -3 and t_chg6 > 3:
        return 9, "pre-front (hot bite!)"
    elif p_chg24 < -1.5:
        return 7, "approaching system"
    elif p_chg24 > 3:
        return 3, "high pressure (slow bite)"
    return 6, "stable"


# ── HUNT SCORING FUNCTIONS (whitetail-tuned) ─────────────────────────

def hunt_temp_drop(t_hist, t_now):
    """Whitetail movement spikes on cold mornings, especially after a drop.
    24h drop of >10°F = strong driver. Cold morning (<50°F GA) = bonus."""
    if not t_hist:
        return 5
    drop = t_hist[0] - t_now if len(t_hist) >= 12 else 0
    base = 5
    if t_now < 35:
        base = 9
    elif t_now < 50:
        base = 7.5
    elif t_now < 65:
        base = 6
    elif t_now > 80:
        base = 3
    bonus = min(2, max(0, drop / 5)) if drop > 0 else 0
    return min(10, base + bonus)


def hunt_wind(mph):
    """Calm-light is best for scent control. Heavy wind suppresses movement."""
    if mph < 1:
        return 6  # dead-calm makes scent control very hard
    elif mph <= 5:
        return 10  # ideal — steady scent direction
    elif mph <= 10:
        return 8
    elif mph <= 15:
        return 6
    elif mph <= 20:
        return 4
    elif mph <= 25:
        return 2
    return 1


def hunt_time_of_day(hour, sr, ss):
    """Whitetail movement is heavily dawn/dusk concentrated.
    First 1.5h after sunrise and last 1.5h before sunset are prime."""
    if sr - 1 <= hour <= sr + 1.5:
        return 10
    if ss - 1.5 <= hour <= ss + 0.5:
        return 10
    if sr + 1.5 < hour <= sr + 3:
        return 7
    if ss - 3 <= hour < ss - 1.5:
        return 7
    if 10 <= hour <= 14:
        return 2  # midday lull
    return 4


def hunt_front(t_hist, p_hist):
    """Whitetail respond strongly to front passage.
    Pre-front feeding push, post-front day 1 dead, day 2-3 strong recovery."""
    if len(t_hist) < 6:
        return 5, "stable"
    t_chg24 = t_hist[-1] - t_hist[0]
    p_chg24 = (p_hist[-1] - p_hist[0]) if len(p_hist) >= len(t_hist) else 0
    if p_chg24 < -3 and t_chg24 < -3:
        return 9, "pre-front (movement spike)"
    elif t_chg24 < -10 and p_chg24 > 3:
        return 4, "post-front day 1 (lull)"
    elif t_chg24 < -5 and p_chg24 > 1:
        return 8, "post-front recovery"
    elif p_chg24 < -1.5:
        return 7, "approaching system"
    elif p_chg24 > 3:
        return 5, "high pressure stable"
    return 6, "stable"


# ── SHARED FUNCTIONS ──────────────────────────────────────────────────

def pressure_trend_score(p_hist):
    if len(p_hist) < 3:
        return 5
    chg = p_hist[-1] - p_hist[max(0, len(p_hist) - 6)]
    if chg < -2:
        return 8
    elif chg < -0.5:
        return 7
    elif chg < 0:
        return 6
    elif abs(chg) <= 0.5:
        return 5
    elif chg <= 2:
        return 4
    return 3


def cloud_score_fish(pct, hour, sr, ss):
    if not (sr <= hour <= ss):
        return 5
    if 30 <= pct <= 70:
        return 8
    elif pct < 30:
        return 5
    elif pct <= 90:
        return 7
    return 5


def cloud_score_hunt(pct, hour, sr, ss):
    """Overcast extends the dawn/dusk window — slight advantage."""
    if not (sr <= hour <= ss):
        return 5
    if 60 <= pct <= 95:
        return 7
    if 30 <= pct < 60:
        return 6
    return 5


# ── PROFILES ──────────────────────────────────────────────────────────

@dataclass
class Profile:
    name: str
    label: str
    emoji: str
    weights: Dict[str, float]
    factor_labels: Dict[str, str]


FISH = Profile(
    name="fish",
    label="Fishing",
    emoji="🎣",
    weights={
        "water_temp":     0.22,
        "front":          0.20,
        "time_of_day":    0.18,
        "wind":           0.14,
        "solunar":        0.10,
        "pressure_trend": 0.09,
        "moon_phase":     0.04,
        "cloud_cover":    0.03,
    },
    factor_labels={
        "water_temp":     "Water Temp",
        "front":          "Weather Front",
        "time_of_day":    "Time of Day",
        "wind":           "Wind / Oxygen",
        "solunar":        "Solunar",
        "pressure_trend": "Pressure Trend",
        "moon_phase":     "Moon Phase",
        "cloud_cover":    "Cloud Cover",
    },
)

HUNT = Profile(
    name="hunt",
    label="Hunting (Whitetail)",
    emoji="🦌",
    weights={
        "time_of_day":    0.25,
        "front":          0.20,
        "temp_drop":      0.15,
        "wind":           0.12,
        "pressure_trend": 0.10,
        "moon_phase":     0.08,
        "solunar":        0.07,
        "cloud_cover":    0.03,
    },
    factor_labels={
        "time_of_day":    "Dawn/Dusk Window",
        "front":          "Weather Front",
        "temp_drop":      "Temperature",
        "wind":           "Wind (Scent)",
        "pressure_trend": "Pressure Trend",
        "moon_phase":     "Moon Phase",
        "solunar":        "Solunar",
        "cloud_cover":    "Cloud Cover",
    },
)


PROFILES = {"fish": FISH, "hunt": HUNT}

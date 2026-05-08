"""
Solunar period and moon phase calculations.
Ported from Tnijem/hahirafish (Meeus astronomical algorithms).
"""
import math
from datetime import datetime, timedelta, timezone


def is_dst(dt_utc: datetime) -> bool:
    """US DST: second Sunday March → first Sunday November."""
    y = dt_utc.year
    ds = datetime(y, 3, 8, tzinfo=timezone.utc)
    while ds.weekday() != 6:
        ds += timedelta(days=1)
    de = datetime(y, 11, 1, tzinfo=timezone.utc)
    while de.weekday() != 6:
        de += timedelta(days=1)
    return ds <= dt_utc < de


def moon_phase(date):
    """Return (phase[0..1], name, illumination_pct)."""
    known_new = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
    synodic = 29.530588853
    dt = datetime(date.year, date.month, date.day, 12, 0, tzinfo=timezone.utc)
    phase = ((dt - known_new).total_seconds() / 86400 / synodic) % 1.0
    illum = (1 - math.cos(2 * math.pi * phase)) / 2 * 100
    names = ["New Moon", "Waxing Crescent", "First Quarter", "Waxing Gibbous",
             "Full Moon", "Waning Gibbous", "Last Quarter", "Waning Crescent"]
    name = names[int(phase * 8) % 8]
    return phase, name, illum


def moon_phase_score(phase: float) -> float:
    """0-10 score: full and new moon peak; quarters score lowest."""
    return ((math.cos(2 * math.pi * phase) + 1) / 2) * 10


def _julian_day(dt: datetime) -> float:
    a = (14 - dt.month) // 12
    y = dt.year + 4800 - a
    m = dt.month + 12 * a - 3
    jdn = dt.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    return jdn + (dt.hour - 12) / 24.0 + dt.minute / 1440.0 + dt.second / 86400.0


def _moon_ra(jd: float) -> float:
    T = (jd - 2451545.0) / 36525.0
    L0 = 218.3164477 + 481267.88123421 * T
    Mm = math.radians((134.9633964 + 477198.8675055 * T) % 360)
    D = math.radians((297.8501921 + 445267.1114034 * T) % 360)
    F = math.radians((93.2720950 + 483202.0175233 * T) % 360)
    Ms = math.radians((357.5291092 + 35999.0502909 * T) % 360)
    dL = (6288774 * math.sin(Mm) + 1274027 * math.sin(2 * D - Mm)
          + 658314 * math.sin(2 * D) + 213618 * math.sin(2 * Mm)
          - 185116 * math.sin(Ms) - 114332 * math.sin(2 * F)) / 1e6
    lon = math.radians((L0 + dL) % 360)
    eps = math.radians(23.4393 - 0.0130 * T)
    return math.degrees(math.atan2(math.sin(lon) * math.cos(eps), math.cos(lon))) % 360


def _gst(jd: float) -> float:
    return (280.46061837 + 360.98564736629 * (jd - 2451545.0)) % 360


def get_solunar_periods(date, lon: float, tz_offset_h: int):
    """Find upper/lower moon transit (major) and moonrise/set (minor)."""
    dt0 = datetime(date.year, date.month, date.day, 0, 0, tzinfo=timezone.utc)
    times = [dt0 + timedelta(minutes=10 * i) for i in range(145)]
    has = []
    for dt in times:
        jd = _julian_day(dt)
        lst = (_gst(jd) + lon) % 360
        ra = _moon_ra(jd)
        ha = (lst - ra + 540) % 360 - 180
        has.append(ha)

    upper = lower = None
    for i in range(len(has) - 1):
        if has[i] > 0 > has[i + 1]:
            frac = has[i] / (has[i] - has[i + 1])
            upper = times[i] + timedelta(minutes=10 * frac)
        if has[i] < -170 and has[i + 1] > 170:
            lower = times[i]

    if upper is None:
        upper = dt0 + timedelta(hours=12)
    if lower is None:
        lower = upper + timedelta(hours=12, minutes=25)

    tz = timedelta(hours=tz_offset_h)
    # Strip tzinfo so periods are naive local-time (matches Open-Meteo's naive timestamps).
    ul = (upper + tz).replace(tzinfo=None)
    ll = (lower + tz).replace(tzinfo=None)
    mr = ul - timedelta(hours=6, minutes=12)
    ms = ul + timedelta(hours=6, minutes=12)

    return [
        (ul - timedelta(hours=1), ul + timedelta(hours=1), "MAJOR"),
        (ll - timedelta(hours=1), ll + timedelta(hours=1), "MAJOR"),
        (mr - timedelta(minutes=30), mr + timedelta(minutes=30), "minor"),
        (ms - timedelta(minutes=30), ms + timedelta(minutes=30), "minor"),
    ]


def solunar_score_at(dt: datetime, periods) -> float:
    """0-10 score based on proximity to major (peak 10) or minor (peak 6) periods."""
    best = 0
    for s, e, kind in periods:
        center = s + (e - s) / 2
        half = (e - s) / 2
        ext = half + timedelta(minutes=30)
        diff = abs((dt - center).total_seconds())
        if diff <= half.total_seconds():
            score = 10 if kind == "MAJOR" else 6
        elif diff <= ext.total_seconds():
            score = 5 if kind == "MAJOR" else 3
        else:
            score = 0
        best = max(best, score)
    return best


def solunar_label(dt: datetime, periods) -> str:
    for s, e, kind in periods:
        if s <= dt <= e:
            return "MAJOR" if kind == "MAJOR" else "minor"
    return ""

// Forecast app — riktom.com

const API_BASE = window.location.origin;
const state = {
  species: 'fish',
  hours: 24,
  lat: 30.9913,
  lon: -83.3727,
  resolvedName: 'Hahira, Georgia',
};

const $ = (id) => document.getElementById(id);

// ── mode toggle ──
document.querySelectorAll('.mode-toggle button').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.mode-toggle button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state.species = btn.dataset.species;
    updateTitle();
    fetchForecast();
  });
});

// ── window toggle ──
document.querySelectorAll('.window-toggle button').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.window-toggle button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state.hours = parseInt(btn.dataset.hours, 10);
    fetchForecast();
  });
});

function updateTitle() {
  if (state.species === 'fish') {
    $('page-title').textContent = '24-Hour Fishing Activity Forecast';
    $('tagline').textContent = 'Research-weighted scoring for largemouth, catfish, crappie, and bream. Built on weather, solunar, and front-passage data.';
  } else {
    $('page-title').textContent = '24-Hour Whitetail Movement Forecast';
    $('tagline').textContent = 'Research-weighted scoring for whitetail deer movement. Dawn/dusk windows, front passage, scent-control wind conditions.';
  }
}

// ── location search ──
$('loc-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const q = $('location-search').value.trim();
  if (!q) return;
  await geocodeAndFetch(q);
});

async function geocodeAndFetch(q) {
  $('loading').hidden = false;
  $('error').hidden = true;
  $('results').hidden = true;
  try {
    const r = await fetch(`${API_BASE}/api/geocode?q=${encodeURIComponent(q)}`);
    if (!r.ok) {
      const body = await r.json().catch(() => ({}));
      throw new Error(body.detail || `Geocode failed (${r.status})`);
    }
    const data = await r.json();
    const hit = data.results[0];
    state.lat = hit.latitude;
    state.lon = hit.longitude;
    state.resolvedName = hit.name;
    showResolved();
    await fetchForecast();
  } catch (err) {
    $('loading').hidden = true;
    showError(err.message);
  }
}

function showResolved() {
  $('resolved-name').textContent = state.resolvedName;
  $('resolved').hidden = false;
}

// ── geolocation ──
$('locate-me').addEventListener('click', () => {
  if (!navigator.geolocation) {
    showError('Geolocation is not supported by this browser.');
    return;
  }
  // Modern browsers block geolocation on insecure (non-HTTPS) origins.
  if (window.location.protocol !== 'https:' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    showError('Browser geolocation requires HTTPS. Type a zip code, city, or address instead — or come back once SSL is enabled on this site.');
    return;
  }
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      state.lat = pos.coords.latitude;
      state.lon = pos.coords.longitude;
      state.resolvedName = `${state.lat.toFixed(4)}, ${state.lon.toFixed(4)}`;
      showResolved();
      fetchForecast();
    },
    (err) => {
      let msg = err.message;
      if (err.code === 1) msg = 'Location permission denied. You can type a zip code, city, or address instead.';
      else if (err.code === 2) msg = 'Could not determine your location. Try entering a zip or city instead.';
      else if (err.code === 3) msg = 'Location request timed out. Try entering a zip or city instead.';
      showError(msg);
    },
    { timeout: 10000, maximumAge: 60000 },
  );
});

// ── fetch forecast ──
async function fetchForecast() {
  $('loading').hidden = false;
  $('error').hidden = true;
  $('results').hidden = true;
  try {
    const url = `${API_BASE}/api/forecast?lat=${state.lat}&lon=${state.lon}&species=${state.species}&hours=${state.hours}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`API ${res.status}`);
    const data = await res.json();
    render(data);
  } catch (err) {
    showError('Failed to load forecast: ' + err.message);
  } finally {
    $('loading').hidden = true;
  }
}

function showError(msg) {
  $('error').textContent = msg;
  $('error').hidden = false;
  $('loading').hidden = true;
}

// ── render ──
function render(data) {
  $('moon').textContent = `${data.moon.phase_name} (${data.moon.illumination_pct}% lit)`;
  const sr = formatTime(data.sun.sunrise);
  const ss = formatTime(data.sun.sunset);
  $('sun').textContent = `${sr} / ${ss}`;
  const cond = data.hourly[0]?.condition || '—';
  $('condition').textContent = cond;

  const windowsEl = $('best-windows');
  windowsEl.innerHTML = '';
  data.best_windows.forEach((w) => {
    const li = document.createElement('li');
    const sol = w.solunar ? ` <span style="color: var(--water); font-size: 0.8rem;">${w.solunar === 'MAJOR' ? '★★' : '★'}</span>` : '';
    li.innerHTML = `
      <span class="when">${w.hour_label}${sol}</span>
      <span class="score">${w.score} · ${w.rating}</span>
    `;
    windowsEl.appendChild(li);
  });

  // Update section headings to reflect window
  $('best-windows-suffix').textContent = `(next ${state.hours}h)`;
  $('hourly-suffix').textContent = `(${state.hours}h)`;

  const barsEl = $('bars');
  barsEl.innerHTML = '';
  barsEl.style.gridTemplateColumns = `repeat(${data.hourly.length}, 1fr)`;
  // For longer windows, label every Nth bar to prevent overlap
  const labelEvery = data.hourly.length <= 24 ? 1 : data.hourly.length <= 48 ? 3 : 6;
  data.hourly.forEach((h, idx) => {
    const bar = document.createElement('div');
    bar.className = 'bar';
    bar.title = `${h.hour_label} · Score ${h.score} (${h.rating}) · ${h.weather.air_f}°F · ${h.weather.wind_mph}mph wind · ${h.weather.cloud_pct}% cloud`;
    const fillHeight = Math.max(8, h.score * 1.4);
    const label = idx % labelEvery === 0 ? h.hour_label : '';
    bar.innerHTML = `
      <div class="fill score-${h.rating.toLowerCase()}" style="height: ${fillHeight}px;"></div>
      <div class="label">${label}</div>
    `;
    barsEl.appendChild(bar);
  });

  const best = data.hourly.reduce((a, b) => (a.score > b.score ? a : b));
  $('best-hour').textContent = best.hour_label;
  const fEl = $('factors');
  fEl.innerHTML = '';
  const labels = data.profile.factor_labels;
  const weights = data.profile.weights;
  Object.keys(weights).sort((a, b) => weights[b] - weights[a]).forEach((k) => {
    const score = best.factors[k];
    const row = document.createElement('div');
    row.className = 'factor-row';
    row.innerHTML = `
      <div class="factor-label">${labels[k]} <span style="color:var(--muted); font-size:0.75rem;">(${Math.round(weights[k] * 100)}%)</span></div>
      <div class="factor-bar"><div class="factor-fill" style="width: ${score * 10}%;"></div></div>
      <div class="factor-value">${score.toFixed(1)} / 10</div>
    `;
    fEl.appendChild(row);
  });

  $('results').hidden = false;
}

function formatTime(iso) {
  const d = new Date(iso);
  let h = d.getHours();
  const m = d.getMinutes();
  const am = h < 12;
  if (h === 0) h = 12;
  else if (h > 12) h -= 12;
  return `${h}:${String(m).padStart(2, '0')} ${am ? 'AM' : 'PM'}`;
}

// ── init ──
updateTitle();
$('location-search').value = 'Hahira, GA';
showResolved();
fetchForecast();

// Forecast app — riktom.com

const API_BASE = window.location.origin;
const state = {
  species: 'fish',
  lat: 30.9585,
  lon: -83.3777,
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

function updateTitle() {
  if (state.species === 'fish') {
    $('page-title').textContent = '24-Hour Fishing Activity Forecast';
    $('tagline').textContent = 'Research-weighted scoring for largemouth, catfish, crappie, and bream. Built on weather, solunar, and front-passage data.';
  } else {
    $('page-title').textContent = '24-Hour Whitetail Movement Forecast';
    $('tagline').textContent = 'Research-weighted scoring for whitetail deer movement. Dawn/dusk windows, front passage, scent-control wind conditions.';
  }
}

// ── form ──
$('loc-form').addEventListener('submit', (e) => {
  e.preventDefault();
  state.lat = parseFloat($('lat').value);
  state.lon = parseFloat($('lon').value);
  fetchForecast();
});

$('locate-me').addEventListener('click', () => {
  if (!navigator.geolocation) {
    showError('Geolocation not supported by this browser.');
    return;
  }
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      state.lat = pos.coords.latitude;
      state.lon = pos.coords.longitude;
      $('lat').value = state.lat.toFixed(4);
      $('lon').value = state.lon.toFixed(4);
      fetchForecast();
    },
    (err) => showError('Could not get location: ' + err.message),
  );
});

// ── fetch ──
async function fetchForecast() {
  $('loading').hidden = false;
  $('error').hidden = true;
  $('results').hidden = true;
  try {
    const url = `${API_BASE}/api/forecast?lat=${state.lat}&lon=${state.lon}&species=${state.species}`;
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
}

// ── render ──
function render(data) {
  // meta
  $('moon').textContent = `${data.moon.phase_name} (${data.moon.illumination_pct}% lit)`;
  const sr = formatTime(data.sun.sunrise);
  const ss = formatTime(data.sun.sunset);
  $('sun').textContent = `${sr} / ${ss}`;
  const cond = data.hourly[0]?.condition || '—';
  $('condition').textContent = cond;

  // best windows
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

  // hourly bars
  const barsEl = $('bars');
  barsEl.innerHTML = '';
  data.hourly.forEach((h) => {
    const bar = document.createElement('div');
    bar.className = 'bar';
    bar.title = `${h.hour_label} · Score ${h.score} (${h.rating}) · ${h.weather.air_f}°F · ${h.weather.wind_mph}mph wind · ${h.weather.cloud_pct}% cloud`;
    const fillHeight = Math.max(8, h.score * 1.4);
    bar.innerHTML = `
      <div class="fill score-${h.rating.toLowerCase()}" style="height: ${fillHeight}px;"></div>
      <div class="label">${h.hour_label}</div>
    `;
    barsEl.appendChild(bar);
  });

  // factor breakdown for best hour
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
fetchForecast();

// --------------------------------------------------------------------------
// Network Path & Delay Analyzer - Cyber-Sleek Modern Telemetry Controller
// High-FPS Real-time SSE, Chart.js Gradients, CartoDB Geo-Map, SQLite History
// --------------------------------------------------------------------------

let currentTraceId = null;
let hopsData = [];
let rttChart = null;
let leafletMap = null;
let tileLayer = null;
let mapMarkers = [];
let mapPolyline = null;
let activeEventSource = null;

// --------------------------------------------------------------------------
// 1. Theme Management
// --------------------------------------------------------------------------

function initTheme() {
  const saved = localStorage.getItem('theme') || 'dark';
  document.documentElement.dataset.theme = saved;
  updateThemeIcon(saved);

  document.getElementById('theme-toggle').addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    localStorage.setItem('theme', next);
    updateThemeIcon(next);
    updateChartTheme();
    updateMapTiles();
  });
}

function updateThemeIcon(theme) {
  const btn = document.getElementById('theme-toggle');
  btn.textContent = theme === 'dark' ? '🌙' : '☀️';
}

function getMapTileUrl() {
  return 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
}

function updateMapTiles() {
  if (!leafletMap) return;
  if (tileLayer) {
    leafletMap.removeLayer(tileLayer);
  }
  tileLayer = L.tileLayer(getMapTileUrl(), {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(leafletMap);
}

// --------------------------------------------------------------------------
// 2. Navigation Tabs
// --------------------------------------------------------------------------

function initNavigation() {
  document.querySelectorAll('.nav-links button').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });
}

function switchTab(tabName) {
  document.querySelectorAll('.nav-links button').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === tabName);
  });
  document.querySelectorAll('.tab').forEach(sec => {
    sec.classList.toggle('hidden', sec.id !== `tab-${tabName}`);
    sec.classList.toggle('active', sec.id === `tab-${tabName}`);
  });

  if (tabName === 'history') {
    loadHistory();
  } else if (tabName === 'trace' && leafletMap) {
    setTimeout(() => leafletMap.invalidateSize(), 200);
  }
}

// --------------------------------------------------------------------------
// 3. Formatting Helpers
// --------------------------------------------------------------------------

function formatMs(val) {
  if (val === null || val === undefined) return '*';
  return val.toFixed(1) + ' ms';
}

function getRttTagClass(val) {
  if (val === null || val === undefined) return 'tag-rtt tag-timeout';
  if (val < 30) return 'tag-rtt tag-good';
  if (val < 100) return 'tag-rtt tag-warn';
  return 'tag-rtt tag-bad';
}

function showError(msg) {
  const box = document.getElementById('error-msg');
  box.textContent = msg;
  box.classList.remove('hidden');
}

function clearError() {
  const box = document.getElementById('error-msg');
  box.textContent = '';
  box.classList.add('hidden');
}

// --------------------------------------------------------------------------
// 4. Live Traceroute via SSE Stream
// --------------------------------------------------------------------------

function startTrace() {
  const target = document.getElementById('target').value.trim();
  const method = document.getElementById('method').value;
  const maxHops = parseInt(document.getElementById('max-hops').value, 10) || 30;

  clearError();

  if (!target) {
    showError('Please enter a target domain or IPv4/IPv6 address.');
    return;
  }

  // Close any prior stream
  if (activeEventSource) {
    activeEventSource.close();
    activeEventSource = null;
  }

  // Reset telemetry & display
  currentTraceId = null;
  hopsData = [];
  document.getElementById('hops-tbody').innerHTML = '';
  document.getElementById('analysis-explanation').textContent = `Initiating route exploration to ${target}...`;
  document.getElementById('kpi-hops').textContent = '0';
  document.getElementById('kpi-rtt').innerHTML = '0.0 <small>ms</small>';
  document.getElementById('kpi-dest').textContent = `Tracing ${target}`;
  document.getElementById('kpi-bottleneck').textContent = 'Analyzing...';
  document.getElementById('kpi-bottleneck-delay').textContent = '+0.0 ms';
  document.getElementById('kpi-jitter').innerHTML = '0.0 <small>ms</small>';
  document.getElementById('kpi-loss').textContent = '0.0%';

  document.getElementById('engine-status').textContent = 'TRACING LIVE';

  resetMapState();
  initOrResetChart();

  const progress = document.getElementById('progress-bar');
  const progressText = document.getElementById('progress-text');
  progress.classList.remove('hidden');
  progressText.textContent = `Probing hops along route to ${target} (${method.toUpperCase()})...`;

  const url = `/api/trace?target=${encodeURIComponent(target)}&method=${method}&max_hops=${maxHops}&timeout=2`;
  const es = new EventSource(url);
  activeEventSource = es;

  es.addEventListener('hop', e => {
    try {
      const hop = JSON.parse(e.data);
      hopsData.push(hop);
      addHopToTable(hop);
      updateChart(hopsData);
      updateMap(hop);

      document.getElementById('kpi-hops').textContent = hopsData.length;
      if (hop.avg_rtt !== null) {
        document.getElementById('kpi-rtt').innerHTML = `${hop.avg_rtt.toFixed(1)} <small>ms</small>`;
      }
      progressText.textContent = `Hop ${hop.hop}: ${hop.ip || 'Request timed out'} [${hop.avg_rtt ? hop.avg_rtt.toFixed(1) + 'ms' : '* * *'}]`;
    } catch (err) {
      console.error('Hop parse error:', err);
    }
  });

  es.addEventListener('analysis', e => {
    try {
      const analysis = JSON.parse(e.data);
      renderAnalysis(analysis);
    } catch (err) {
      console.error('Analysis parse error:', err);
    }
  });

  es.addEventListener('ping', e => {
    try {
      const pingData = JSON.parse(e.data);
      renderPing(pingData);
    } catch (err) {
      console.error('Ping parse error:', err);
    }
  });

  es.addEventListener('complete', e => {
    try {
      const data = JSON.parse(e.data);
      currentTraceId = data.id;
      progress.classList.add('hidden');
      document.getElementById('engine-status').textContent = 'SYSTEM READY';
      es.close();
      activeEventSource = null;
    } catch (err) {
      console.error('Complete event error:', err);
    }
  });

  es.addEventListener('app_error', e => {
    try {
      const err = JSON.parse(e.data);
      showError(err.message || 'Traceroute encountered an error.');
    } catch (_) {}
    progress.classList.add('hidden');
    document.getElementById('engine-status').textContent = 'ERROR';
    es.close();
    activeEventSource = null;
  });

  es.onerror = () => {
    if (es.readyState === EventSource.CLOSED) {
      progress.classList.add('hidden');
      document.getElementById('engine-status').textContent = 'SYSTEM READY';
      activeEventSource = null;
    }
  };
}

// --------------------------------------------------------------------------
// 5. Hop Table Population (Sticky & Smooth Scroll)
// --------------------------------------------------------------------------

function addHopToTable(hop) {
  const tbody = document.getElementById('hops-tbody');
  const tr = document.createElement('tr');

  const rtts = hop.rtts || [];
  const r1 = formatMs(rtts[0]);
  const r2 = formatMs(rtts[1]);
  const r3 = formatMs(rtts[2]);
  const avg = hop.avg_rtt !== null ? `${hop.avg_rtt.toFixed(1)} ms` : '*';
  const inc = hop.incremental_delay !== null ? `+${hop.incremental_delay.toFixed(1)} ms` : '-';
  const jitter = hop.jitter !== null ? `${hop.jitter.toFixed(1)} ms` : '-';
  const loss = `${hop.packet_loss.toFixed(0)}%`;

  const city = hop.geo && hop.geo.city ? `${hop.geo.city}, ${hop.geo.country}` : '-';
  const asn = hop.geo && hop.geo.asn ? hop.geo.asn : '-';

  tr.innerHTML = `
    <td><strong style="color:var(--cyan); font-family:var(--font-mono);">${hop.hop}</strong></td>
    <td style="font-family: var(--font-mono); font-weight:600;">${hop.ip || '* * *'}</td>
    <td style="max-width: 170px; overflow: hidden; text-overflow: ellipsis; color:var(--text-muted);" title="${hop.hostname || ''}">${hop.hostname || '-'}</td>
    <td style="font-family: var(--font-mono);">${r1}</td>
    <td style="font-family: var(--font-mono);">${r2}</td>
    <td style="font-family: var(--font-mono);">${r3}</td>
    <td><span class="${getRttTagClass(hop.avg_rtt)}">${avg}</span></td>
    <td style="font-family: var(--font-mono); color:${hop.incremental_delay > 15 ? 'var(--amber)' : 'inherit'}; font-weight:${hop.incremental_delay > 15 ? '700' : 'normal'};">${inc}</td>
    <td style="font-family: var(--font-mono);">${jitter}</td>
    <td style="font-family: var(--font-mono); color: ${hop.packet_loss > 0 ? 'var(--rose)' : 'inherit'}; font-weight: ${hop.packet_loss > 0 ? '700' : 'normal'};">${loss}</td>
    <td>${city}</td>
    <td style="font-size: 0.76rem; color: var(--text-dim); max-width:140px; overflow:hidden; text-overflow:ellipsis;">${asn}</td>
  `;

  tbody.appendChild(tr);

  // Auto-scroll table container to keep latest hop in view
  const viewport = document.querySelector('.table-scroll-viewport');
  if (viewport) {
    viewport.scrollTop = viewport.scrollHeight;
  }
}

// --------------------------------------------------------------------------
// 6. Summary Diagnostics & Ping Cards
// --------------------------------------------------------------------------

function renderAnalysis(analysis) {
  document.getElementById('analysis-explanation').textContent = analysis.explanation || 'Path delay decomposed across all transit hops.';
  
  if (analysis.bottleneck_hop) {
    document.getElementById('kpi-bottleneck').textContent = `Hop ${analysis.bottleneck_hop}`;
    document.getElementById('kpi-bottleneck-delay').textContent = `+${analysis.bottleneck_delay ? analysis.bottleneck_delay.toFixed(1) : 0} ms spike`;
  } else {
    document.getElementById('kpi-bottleneck').textContent = 'Smooth';
    document.getElementById('kpi-bottleneck-delay').textContent = 'No major jump';
  }

  if (analysis.end_to_end_rtt) {
    document.getElementById('kpi-rtt').innerHTML = `${analysis.end_to_end_rtt.toFixed(1)} <small>ms</small>`;
  }
}

function renderPing(ping) {
  document.getElementById('kpi-jitter').innerHTML = `${ping.jitter.toFixed(1)} <small>ms</small>`;
  document.getElementById('kpi-loss').textContent = `${ping.packet_loss.toFixed(0)}%`;
  document.getElementById('kpi-loss-sub').textContent = `${ping.probes} probes tested`;
  if (ping.avg_rtt > 0) {
    document.getElementById('kpi-rtt').innerHTML = `${ping.avg_rtt.toFixed(1)} <small>ms</small>`;
    document.getElementById('kpi-dest').textContent = `Min ${ping.min_rtt.toFixed(0)} / Max ${ping.max_rtt.toFixed(0)} ms`;
  }
}

// --------------------------------------------------------------------------
// 7. Interactive Leaflet World Map (CartoDB Tiles & Glowing Path)
// --------------------------------------------------------------------------

function initMap() {
  if (leafletMap) return;

  const isDark = document.documentElement.dataset.theme === 'dark';
  leafletMap = L.map('map', {
    zoomControl: true,
    attributionControl: false
  }).setView([20.0, 0.0], 2);

  tileLayer = L.tileLayer(getMapTileUrl(), {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(leafletMap);

  setTimeout(() => leafletMap.invalidateSize(), 300);
}

function resetMapState() {
  if (!leafletMap) {
    initMap();
    return;
  }
  mapMarkers.forEach(m => leafletMap.removeLayer(m));
  mapMarkers = [];
  if (mapPolyline) {
    leafletMap.removeLayer(mapPolyline);
    mapPolyline = null;
  }
  document.getElementById('map-counter').textContent = '0 Locations';
  leafletMap.setView([20.0, 0.0], 2);
}

function updateMap(hop) {
  if (!leafletMap) initMap();
  if (!hop.geo || hop.geo.lat === undefined || hop.geo.lon === undefined) return;

  const lat = hop.geo.lat;
  const lon = hop.geo.lon;

  // Add Glowing Pulse Circle Marker
  const marker = L.circleMarker([lat, lon], {
    radius: 7,
    color: '#06b6d4',
    weight: 2,
    fillColor: '#38bdf8',
    fillOpacity: 0.9
  }).addTo(leafletMap);

  const popupHtml = `
    <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.85rem; line-height: 1.45; color:#0f172a;">
      <strong style="color:#0284c7; font-size:0.95rem;">Hop ${hop.hop}: ${hop.ip}</strong><br>
      📍 <strong>${hop.geo.city || 'Unknown'}, ${hop.geo.country || ''}</strong><br>
      🏢 <span style="color: #64748b; font-size: 0.78rem;">${hop.geo.isp || ''} (${hop.geo.asn || ''})</span><br>
      ⏱️ <strong style="color: #059669;">Avg RTT: ${hop.avg_rtt ? hop.avg_rtt.toFixed(1) + ' ms' : '*'}</strong>
    </div>
  `;
  marker.bindPopup(popupHtml);
  mapMarkers.push(marker);

  document.getElementById('map-counter').textContent = `${mapMarkers.length} Locations`;

  // Draw glowing cyan dashed route line
  const latlngs = mapMarkers.map(m => m.getLatLng());
  if (latlngs.length >= 2) {
    if (mapPolyline) {
      mapPolyline.setLatLngs(latlngs);
    } else {
      mapPolyline = L.polyline(latlngs, {
        color: '#06b6d4',
        weight: 3.5,
        opacity: 0.9,
        dashArray: '8, 8'
      }).addTo(leafletMap);
    }
  }

  // Adjust zoom to fit all markers
  if (latlngs.length > 0) {
    const group = L.featureGroup(mapMarkers);
    leafletMap.fitBounds(group.getBounds().pad(0.25));
  }
}

// --------------------------------------------------------------------------
// 8. Chart.js RTT Bar Chart (Gradient Filled & Theme Aware)
// --------------------------------------------------------------------------

function initOrResetChart() {
  if (rttChart) {
    rttChart.destroy();
    rttChart = null;
  }
}

function updateChartTheme() {
  if (!rttChart) return;
  const isDark = document.documentElement.dataset.theme === 'dark';
  rttChart.options.scales.x.ticks.color = isDark ? '#94a3b8' : '#64748b';
  rttChart.options.scales.y.ticks.color = isDark ? '#94a3b8' : '#64748b';
  rttChart.options.scales.x.grid.color = isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0,0,0,0.06)';
  rttChart.options.scales.y.grid.color = isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0,0,0,0.06)';
  rttChart.update();
}

function updateChart(hops) {
  const labels = hops.map(h => `H${h.hop}`);
  const data = hops.map(h => (h.avg_rtt !== null ? h.avg_rtt : 0));
  const colors = hops.map(h => {
    if (h.avg_rtt === null) return 'rgba(148, 163, 184, 0.3)';
    if (h.avg_rtt < 30) return '#10b981';
    if (h.avg_rtt < 100) return '#f59e0b';
    return '#f43f5e';
  });

  const isDark = document.documentElement.dataset.theme === 'dark';
  const textColor = isDark ? '#94a3b8' : '#64748b';
  const gridColor = isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0,0,0,0.06)';

  if (!rttChart) {
    const ctx = document.getElementById('rtt-chart').getContext('2d');
    rttChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Avg RTT (ms)',
          data: data,
          backgroundColor: colors,
          borderRadius: 6,
          barPercentage: 0.7,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(13, 21, 38, 0.95)',
            titleFont: { family: 'JetBrains Mono', size: 12 },
            bodyFont: { family: 'Plus Jakarta Sans', size: 12 },
            padding: 10,
            cornerRadius: 8,
            borderColor: 'rgba(6, 182, 212, 0.4)',
            borderWidth: 1,
            callbacks: {
              label: (ctx) => `${ctx.raw > 0 ? ctx.raw.toFixed(1) + ' ms' : 'Timeout (* * *)'}`
            }
          }
        },
        scales: {
          x: {
            ticks: { color: textColor, font: { family: 'JetBrains Mono', size: 10 } },
            grid: { display: false }
          },
          y: {
            beginAtZero: true,
            title: { display: true, text: 'RTT (ms)', color: textColor, font: { size: 11, family: 'JetBrains Mono' } },
            ticks: { color: textColor, font: { family: 'JetBrains Mono', size: 10 } },
            grid: { color: gridColor }
          }
        }
      }
    });
  } else {
    rttChart.data.labels = labels;
    rttChart.data.datasets[0].data = data;
    rttChart.data.datasets[0].backgroundColor = colors;
    rttChart.update();
  }
}

// --------------------------------------------------------------------------
// 9. Persistent SQLite History Management
// --------------------------------------------------------------------------

async function loadHistory() {
  const tbody = document.getElementById('history-tbody');
  const noHist = document.getElementById('no-history');
  tbody.innerHTML = '';

  try {
    const res = await fetch('/api/history');
    if (!res.ok) throw new Error('Failed to load history');
    const items = await res.json();

    if (!items || items.length === 0) {
      noHist.style.display = 'block';
      return;
    }

    noHist.style.display = 'none';
    items.forEach(item => {
      const tr = document.createElement('tr');
      const rtt = item.end_to_end_rtt ? `${item.end_to_end_rtt.toFixed(1)} ms` : '-';
      tr.innerHTML = `
        <td><strong style="color:var(--cyan); font-family:var(--font-mono);">${item.target}</strong></td>
        <td style="font-family: var(--font-mono);">${item.resolved_ip || '-'}</td>
        <td style="text-transform: uppercase; font-family: var(--font-mono); font-size: 0.78rem;">${item.method}</td>
        <td><span class="tag-rtt" style="background:var(--bg-subtle);">${item.total_hops} hops</span></td>
        <td style="color: var(--cyan); font-weight: 700; font-family:var(--font-mono);">${rtt}</td>
        <td style="color: var(--text-dim); font-size: 0.8rem; font-family:var(--font-mono);">${item.timestamp}</td>
        <td style="text-align: right;">
          <button class="btn-action view" onclick="viewAnalysis('${item.id}')">Inspect</button>
          <button class="btn-action delete" onclick="deleteAnalysis('${item.id}')">Delete</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('History fetch error:', err);
    noHist.textContent = 'Could not retrieve history from server.';
    noHist.style.display = 'block';
  }
}

async function viewAnalysis(id) {
  try {
    const res = await fetch(`/api/history/${id}`);
    if (!res.ok) throw new Error('Analysis record not found');
    const record = await res.json();

    switchTab('trace');
    currentTraceId = record.id;
    hopsData = record.hops || [];

    document.getElementById('target').value = record.target;
    document.getElementById('method').value = record.method || 'icmp';
    document.getElementById('hops-tbody').innerHTML = '';

    resetMapState();
    initOrResetChart();

    hopsData.forEach(h => {
      addHopToTable(h);
      updateMap(h);
    });
    updateChart(hopsData);

    document.getElementById('kpi-hops').textContent = hopsData.length;
    if (record.end_to_end_rtt) {
      document.getElementById('kpi-rtt').innerHTML = `${record.end_to_end_rtt.toFixed(1)} <small>ms</small>`;
    }
    document.getElementById('kpi-dest').textContent = `Inspected ${record.target}`;

    if (record.analysis) {
      renderAnalysis(record.analysis);
    }
    if (record.ping) {
      renderPing(record.ping);
    }
  } catch (err) {
    alert('Error loading analysis details: ' + err.message);
  }
}

async function deleteAnalysis(id) {
  if (!confirm('Permanently delete this analysis record from SQLite?')) return;
  try {
    const res = await fetch(`/api/history/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Deletion failed');
    loadHistory();
  } catch (err) {
    alert('Error deleting record: ' + err.message);
  }
}

// --------------------------------------------------------------------------
// 10. Data Exports
// --------------------------------------------------------------------------

function exportCSV() {
  if (!currentTraceId) {
    alert('No completed trace record available for export.');
    return;
  }
  window.open(`/api/export/${currentTraceId}?format=csv`, '_blank');
}

function exportJSON() {
  if (!currentTraceId) {
    alert('No completed trace record available for export.');
    return;
  }
  window.open(`/api/export/${currentTraceId}?format=json`, '_blank');
}

// --------------------------------------------------------------------------
// 11. Master DOM Initialization
// --------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initNavigation();
  initMap();

  document.getElementById('btn-trace').addEventListener('click', startTrace);
  document.getElementById('target').addEventListener('keydown', e => {
    if (e.key === 'Enter') startTrace();
  });
});

let allEvents = [];
let activeVenues = new Set(); // prázdná = vše
let searchQuery = '';
let activeView = 'all';

const todayStr = (() => {
  const d = new Date();
  return `${d.getDate()}.${d.getMonth()+1}.${d.getFullYear()}`;
})();

function normalizeDate(raw) {
  if (!raw) return '';
  // odstranit mezery, sjednotit formát
  return raw.replace(/\s/g, '');
}

function isToday(dateStr) {
  const n = normalizeDate(dateStr);
  return n === todayStr || n === todayStr.replace(/\b(\d)\./g, '0$1.');
}

function formatDate(dateStr, timeStr) {
  if (!dateStr) return '';
  const parts = dateStr.replace(/\s/g, '').split('.');
  if (parts.length < 2) return dateStr;
  const days = ['Ne','Po','Út','St','Čt','Pá','So'];
  try {
    const d = new Date(parseInt(parts[2]) || new Date().getFullYear(), parseInt(parts[1])-1, parseInt(parts[0]));
    const dayName = days[d.getDay()];
    return `${dayName} ${parts[0]}.${parts[1]}. ${parts[2] || ''}${timeStr ? ' · ' + timeStr : ''}`.trim();
  } catch(e) {
    return `${dateStr}${timeStr ? ' · '+timeStr : ''}`;
  }
}

function buildFilters(events) {
  const fromEvents = new Set(events.map(e => e.venue).filter(Boolean));
  const fromCoords = new Set(Object.keys(venueCoords));
  const venues = [...new Set([...fromEvents, ...fromCoords])].sort();
  const wrap = document.getElementById('filters');
  wrap.innerHTML = '<button class="filter-btn active" data-venue="vse">Vše</button>';
  venues.forEach(v => {
    const btn = document.createElement('button');
    btn.className = 'filter-btn';
    btn.dataset.venue = v;
    btn.textContent = v;
    wrap.appendChild(btn);
  });

  // Toggle tlačítko pro mobilní zobrazení
  const toggle = document.createElement('button');
  toggle.className = 'filters-toggle';
  toggle.id = 'filters-toggle';
  wrap.parentNode.insertBefore(toggle, wrap);

  function updateToggleLabel() {
    const n = activeVenues.size;
    toggle.innerHTML = `<span>Kluby${n > 0 ? ` (${n})` : ''}</span><span class="filters-toggle-icon">▾</span>`;
    toggle.classList.toggle('has-active', n > 0);
  }
  updateToggleLabel();

  toggle.addEventListener('click', () => {
    wrap.classList.toggle('filters-open');
    toggle.classList.toggle('open');
  });

  const showBtn = document.createElement('button');
  showBtn.className = 'filters-show-btn';
  showBtn.textContent = 'Zobrazit koncerty';
  wrap.insertAdjacentElement('afterend', showBtn);
  showBtn.addEventListener('click', () => {
    wrap.classList.remove('filters-open');
    toggle.classList.remove('open');
    closeMenu();
  });

  wrap.addEventListener('click', e => {
    const btn = e.target.closest('.filter-btn');
    if (!btn) return;
    const v = btn.dataset.venue;
    if (v === 'vse') {
      activeVenues.clear();
    } else {
      if (activeVenues.has(v)) activeVenues.delete(v);
      else activeVenues.add(v);
    }
    // Aktualizuj styly tlačítek
    wrap.querySelector('[data-venue="vse"]').classList.toggle('active', activeVenues.size === 0);
    wrap.querySelectorAll('.filter-btn:not([data-venue="vse"])').forEach(b => {
      b.classList.toggle('active', activeVenues.has(b.dataset.venue));
    });
    updateToggleLabel();
    if (activeView === 'kalendar' || activeView === 'mapa') {
      activeView = 'all';
      document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
      document.querySelector('.view-btn[data-view="all"]').classList.add('active');
    }
    render();
  });
}

function eventDate(ev) {
  const parts = normalizeDate(ev.date).split('.');
  try {
    const d = new Date(parseInt(parts[2]), parseInt(parts[1])-1, parseInt(parts[0]));
    d.setHours(0,0,0,0);
    return isNaN(d) ? null : d;
  } catch(e) { return null; }
}

function getFiltered() {
  const today = new Date(); today.setHours(0,0,0,0);
  return allEvents.filter(ev => {
    const venueOk = activeVenues.size === 0 || activeVenues.has(ev.venue);
    const q = searchQuery.toLowerCase();
    const searchOk = !q ||
      (ev.title || '').toLowerCase().includes(q) ||
      (ev.venue || '').toLowerCase().includes(q);
    if (!venueOk || !searchOk) return false;
    if (activeView === 'dnes') {
      return isToday(ev.date);
    }
    if (activeView === 'zitra') {
      const d = eventDate(ev);
      if (!d) return false;
      return Math.round((d - today) / 86400000) === 1;
    }
    if (activeView === 'tyden') {
      const d = eventDate(ev);
      if (!d) return false;
      const diff = Math.round((d - today) / 86400000);
      return diff >= 0 && diff <= 7;
    }
    return true;
  });
}

function renderCalendar(selectedKey = null, calYear = null, calMonth = null) {
  const content = document.getElementById('content');
  const today = new Date(); today.setHours(0,0,0,0);
  const year = calYear ?? today.getFullYear();
  const month = calMonth ?? today.getMonth();
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const monthNames = ['Leden','Únor','Březen','Duben','Květen','Červen','Červenec','Srpen','Září','Říjen','Listopad','Prosinec'];
  const dayNames = ['Po','Út','St','Čt','Pá','So','Ne'];

  const byDate = {};
  allEvents.forEach(ev => {
    const d = eventDate(ev);
    if (!d) return;
    const key = `${d.getDate()}.${d.getMonth()+1}.${d.getFullYear()}`;
    if (!byDate[key]) byDate[key] = [];
    byDate[key].push(ev);
  });

  let startOffset = (firstDay.getDay() + 6) % 7;
  let cells = '';
  for (let i = 0; i < startOffset; i++) cells += `<div class="cal-cell cal-empty"></div>`;
  for (let day = 1; day <= lastDay.getDate(); day++) {
    const key = `${day}.${month+1}.${year}`;
    const evs = byDate[key] || [];
    const isT = day === today.getDate() && month === today.getMonth() && year === today.getFullYear();
    const isSel = key === selectedKey;
    cells += `
      <div class="cal-cell${isT ? ' cal-today' : ''}${evs.length ? ' cal-has-events' : ''}${isSel ? ' cal-selected' : ''}" data-key="${key}">
        <div class="cal-day-num">${day}</div>
        ${evs.length ? `<span class="cal-count">${evs.length}</span>` : ''}
      </div>`;
  }

  const dayCards = selectedKey && byDate[selectedKey]
    ? `<div class="cal-day-cards">
        <div class="section-head">
          <h2 class="section-title">${selectedKey}</h2>
          <span class="section-count">${byDate[selectedKey].length} ${byDate[selectedKey].length === 1 ? 'akce' : 'akcí'}</span>
        </div>
        <div class="grid">${byDate[selectedKey].map(ev => cardHTML(ev)).join('')}</div>
       </div>`
    : '';

  content.innerHTML = `
    <div class="cal-wrap">
      <div class="cal-nav">
        <button class="cal-nav-btn" id="cal-prev">&#8592;</button>
        <div class="cal-header">${monthNames[month]} ${year}</div>
        <button class="cal-nav-btn" id="cal-next">&#8594;</button>
      </div>
      <div class="cal-grid">
        ${dayNames.map(d => `<div class="cal-head-cell">${d}</div>`).join('')}
        ${cells}
      </div>
    </div>
    ${dayCards}`;

  content.querySelectorAll('.cal-cell.cal-has-events').forEach(cell => {
    cell.addEventListener('click', () => {
      renderCalendar(cell.dataset.key, year, month);
      const cards = document.querySelector('.cal-day-cards');
      if (cards) scrollBelowHeader(cards);
    });
  });

  document.getElementById('cal-prev').addEventListener('click', () => {
    const d = new Date(year, month - 1, 1);
    renderCalendar(null, d.getFullYear(), d.getMonth());
  });

  document.getElementById('cal-next').addEventListener('click', () => {
    const d = new Date(year, month + 1, 1);
    renderCalendar(null, d.getFullYear(), d.getMonth());
  });
}

let venueCoords = {};

async function loadVenueCoords() {
  if (Object.keys(venueCoords).length) return;
  try {
    const res = await fetch('venue-coords.json');
    venueCoords = await res.json();
  } catch(e) {
    console.warn('venue-coords.json se nepodařilo načíst', e);
  }
}

let mapInstance = null;
const mapMarkers = {};

async function renderMap() {
  const content = document.getElementById('content');
  content.innerHTML = `<div id="map-container"></div>`;

  const today = new Date(); today.setHours(0, 0, 0, 0);

  // Skupiny událostí podle venue (jen budoucí + dnes)
  const byVenue = {};
  allEvents.forEach(ev => {
    const venueOk = activeVenues.size === 0 || activeVenues.has(ev.venue);
    if (!venueOk) return;
    const d = eventDate(ev);
    if (d && d < today) return;
    if (!byVenue[ev.venue]) byVenue[ev.venue] = [];
    byVenue[ev.venue].push(ev);
  });

  if (mapInstance) { mapInstance.remove(); mapInstance = null; }

  mapInstance = L.map('map-container', { zoomControl: true }).setView([50.0780, 14.4341], 13);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
  }).addTo(mapInstance);

  await loadVenueCoords();
  Object.entries(venueCoords).forEach(([venue, coords]) => {
    const evs = byVenue[venue] || [];
    const hasEvents = evs.length > 0;

    const icon = L.divIcon({
      className: '',
      html: `<div class="map-marker${hasEvents ? ' map-marker--active' : ''}">${hasEvents ? evs.length : ''}</div>`,
      iconSize: [36, 36],
      iconAnchor: [18, 18],
    });

    const marker = L.marker(coords, { icon }).addTo(mapInstance);
    mapMarkers[venue] = marker;

    const navUrl = `https://www.google.com/maps/dir/?api=1&destination=${coords[0]},${coords[1]}`;
    const navBtn = `<a class="map-popup-nav" href="${navUrl}" target="_blank" rel="noopener">&#9657; Navigovat</a>`;

    const popupContent = hasEvents
      ? `<div class="map-popup">
           <div class="map-popup-venue">${venue}</div>
           <ul class="map-popup-list">
             ${evs.slice(0, 5).map(ev =>
               `<li><span class="map-popup-date">${formatDate(ev.date, ev.time)}</span> ${escHtml(ev.title)}</li>`
             ).join('')}
             ${evs.length > 5 ? `<li class="map-popup-more">+ ${evs.length - 5} dalších</li>` : ''}
           </ul>
           ${navBtn}
         </div>`
      : `<div class="map-popup"><div class="map-popup-venue">${venue}</div><p class="map-popup-empty">Žádné nadcházející akce</p>${navBtn}</div>`;

    marker.bindPopup(popupContent, { maxWidth: 280 });
  });

  // Klik na prázdné místo mapy (mimo marker/popup) → zpět na seznam
  mapInstance.on('click', () => {
    activeView = 'all';
    document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('.view-btn[data-view="all"]').classList.add('active');
    render();
  });
}

function render() {
  if (activeView === 'kalendar') { renderCalendar(); return; }
  if (activeView === 'mapa') { renderMap(); return; }
  const events = getFiltered();
  const content = document.getElementById('content');

  if (!events.length) {
    const _solo = activeVenues.size === 1 ? [...activeVenues][0] : null;
    const mapBtn = (_solo && venueCoords[_solo])
      ? `<button class="venue-map-btn" id="venue-map-btn">📍 Zobrazit na mapě</button>`
      : '';
    content.innerHTML = mapBtn + `
      <div class="grid">
        <div class="empty">
          <div class="empty-icon">&#9835;</div>
          <div class="empty-title">Nic nenalezeno</div>
          <p>Zkus jiný filtr nebo hledaný výraz.</p>
        </div>
      </div>`;
    document.getElementById('venue-map-btn')?.addEventListener('click', () => {
      const venue = _solo;
      activeView = 'mapa';
      document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
      document.querySelector('.view-btn[data-view="mapa"]').classList.add('active');
      render().then(() => {
        const marker = mapMarkers[venue];
        if (marker) { mapInstance.setView(marker.getLatLng(), 16, { animate: true }); marker.openPopup(); }
      });
    });
    return;
  }

  // Skupiny: Dnes / Tento týden / Brzy
  const today = new Date(); today.setHours(0,0,0,0);
  const groups = { 'Dnes': [], 'Zítra': [], 'Tento týden': [], 'Brzy': [] };

  events.forEach(ev => {
    const parts = normalizeDate(ev.date).split('.');
    let d = null;
    try { d = new Date(parseInt(parts[2]), parseInt(parts[1])-1, parseInt(parts[0])); d.setHours(0,0,0,0); } catch(e) {}
    if (!d || isNaN(d)) { groups['Brzy'].push(ev); return; }
    const diff = Math.round((d - today) / 86400000);
    if (diff === 0) groups['Dnes'].push(ev);
    else if (diff === 1) groups['Zítra'].push(ev);
    else if (diff > 1 && diff <= 7) groups['Tento týden'].push(ev);
    else groups['Brzy'].push(ev);
  });

  const sectionIds = { 'Dnes': 'section-dnes', 'Zítra': 'section-zitra', 'Tento týden': 'section-tyden', 'Brzy': 'section-brzy' };
  const collapsible = new Set(['Zítra', 'Tento týden', 'Brzy']);
  let html = '';
  Object.entries(groups).forEach(([label, evs]) => {
    if (!evs.length) return;
    const id = sectionIds[label];
    if (collapsible.has(label)) {
      html += `
        <div class="section-head section-head--toggle is-collapsed" id="${id}" data-body="${id}-body">
          <h2 class="section-title">${label}</h2>
          <span class="section-count">${evs.length} ${evs.length === 1 ? 'akce' : 'akcí'}</span>
          <span class="section-toggle-icon">▾</span>
        </div>
        <div class="grid section-body is-collapsed" id="${id}-body">
          ${evs.map(ev => cardHTML(ev)).join('')}
        </div>`;
    } else {
      html += `
        <div class="section-head" id="${id}">
          <h2 class="section-title">${label}</h2>
          <span class="section-count">${evs.length} ${evs.length === 1 ? 'akce' : 'akcí'}</span>
        </div>
        <div class="grid">
          ${evs.map(ev => cardHTML(ev)).join('')}
        </div>`;
    }
  });

  const _soloV = activeVenues.size === 1 ? [...activeVenues][0] : null;
  if (_soloV && venueCoords[_soloV]) {
    html = `<button class="venue-map-btn" id="venue-map-btn">📍 Zobrazit na mapě</button>` + html;
  }

  content.innerHTML = html;

  document.getElementById('venue-map-btn')?.addEventListener('click', () => {
    const venue = _soloV;
    activeView = 'mapa';
    document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('.view-btn[data-view="mapa"]').classList.add('active');
    render().then(() => {
      const marker = mapMarkers[venue];
      if (marker) {
        mapInstance.setView(marker.getLatLng(), 16, { animate: true });
        marker.openPopup();
      }
    });
  });

  content.querySelectorAll('.section-head--toggle').forEach(head => {
    head.addEventListener('click', () => {
      const body = document.getElementById(head.dataset.body);
      const collapsed = head.classList.toggle('is-collapsed');
      body.classList.toggle('is-collapsed', collapsed);
    });
  });
}

function cardHTML(ev) {
  const dateLabel = formatDate(ev.date, ev.time);
  const img = ev.image
    ? `<img class="card-img" src="${escHtml(ev.image)}" alt="${escHtml(ev.title)}" loading="lazy" onerror="this.outerHTML='<div class=\\'card-img-placeholder\\'>&#9835;</div>'">`
    : `<div class="card-img-placeholder">&#9835;</div>`;

  return `
    <a class="card" href="${escHtml(ev.url || '#')}" target="_blank" rel="noopener">
      <div style="position:relative">
        ${img}
        <span class="card-arrow">&#8599;</span>
      </div>
      <div class="card-body">
        <div class="card-date">${escHtml(dateLabel)}</div>
        <div class="card-title">${escHtml(ev.title || '???')}</div>
        <div class="card-venue">&#9679; ${escHtml(ev.venue || '')}</div>
      </div>
    </a>`;
}

function escHtml(str) {
  return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function updateStats(events) {
  const todayCount = events.filter(e => isToday(e.date)).length;
  const venues = new Set([...events.map(e => e.venue).filter(Boolean), ...Object.keys(venueCoords)]);
  const welcomeCount = document.getElementById('welcome-venue-count');
  if (welcomeCount) welcomeCount.textContent = venues.size;
  [1,2,3,4,5,6].forEach(i => {
    const suffix = i === 1 ? '' : `-${i}`;
    document.getElementById(`stat-total${suffix}`).textContent = events.length;
    document.getElementById(`stat-venues${suffix}`).textContent = venues.size;
    document.getElementById(`stat-today${suffix}`).textContent = todayCount;
  });
}

async function init() {
  try {
    const res = await fetch('concerts.json');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    allEvents = data.events || [];

    // update badge
    const badge = document.getElementById('update-badge');
    if (data.updated && badge) {
      const d = new Date(data.updated);
      badge.innerHTML =
        `Aktualizováno: <span>${d.toLocaleDateString('cs-CZ')} v ${d.toLocaleTimeString('cs-CZ', {hour:'2-digit',minute:'2-digit'})}</span>`;
    }

    // ticker
    const ticker = document.getElementById('ticker');
    if (ticker) {
      const titles = allEvents.slice(0, 10).map(e => e.title).filter(Boolean);
      ticker.textContent = titles.join('  ·  ');
    }

    await loadVenueCoords();
    buildFilters(allEvents);
    updateStats(allEvents);
    render();

  } catch(err) {
    document.getElementById('content').innerHTML = `
      <div class="error-box">
        <strong>Chyba při načítání dat</strong><br><br>
        ${err.message}<br><br>
        Ujisti se, že soubor <code>concerts.json</code> je ve stejné složce jako tento soubor
        a že jsi spustil <code>python scraper.py</code>.<br><br>
        Pokud otevíráš soubor přímo z disku (file://), zkus ho otevřít přes lokální server:<br>
        <code>python -m http.server 8000</code> a pak jdi na <code>http://localhost:8000</code>
      </div>`;
  }
}

document.getElementById('search').addEventListener('input', e => {
  searchQuery = e.target.value;
  if (searchQuery && activeView !== 'all') {
    activeView = 'all';
    document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('.view-btn[data-view="all"]').classList.add('active');
  }
  if (searchQuery && activeVenues.size > 0) {
    activeVenues.clear();
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('.filter-btn[data-venue="vse"]').classList.add('active');
  }
  render();
});

document.querySelector('.view-bar').addEventListener('click', e => {
  const btn = e.target.closest('.view-btn');
  if (!btn) return;
  const view = btn.dataset.view;

  if (view === 'zitra') {
    activeView = 'all';
    document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('.view-btn[data-view="all"]').classList.add('active');
    render();
    const target = document.getElementById('section-zitra');
    if (target) scrollBelowHeader(target);
    return;
  }

  if (view === 'tyden') {
    activeView = 'all';
    document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('.view-btn[data-view="all"]').classList.add('active');
    render();
    const target = document.getElementById('section-tyden');
    if (target) scrollBelowHeader(target);
    return;
  }

  activeView = view;
  document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  render();
  if (view === 'dnes') {
    const target = document.getElementById('content');
    if (target) scrollBelowHeader(target);
  }
});

function scrollBelowHeader(target) {
  const headerH = document.querySelector('header').offsetHeight;
  const top = target.getBoundingClientRect().top + window.scrollY - headerH - 8;
  window.scrollTo({ top, behavior: 'smooth' });
}

function closeMenu() {
  document.getElementById('header-nav').classList.remove('open');
  document.getElementById('hamburger').classList.remove('open');
}

document.getElementById('hamburger').addEventListener('click', () => {
  document.getElementById('header-nav').classList.toggle('open');
  document.getElementById('hamburger').classList.toggle('open');
});

document.getElementById('header-nav').addEventListener('click', e => {
  if (e.target.closest('.view-btn')) closeMenu();
});

document.addEventListener('click', e => {
  if (activeView !== 'mapa') return;
  if (e.target.closest('#map-container, #header-nav, header, .venue-map-btn')) return;
  activeView = 'all';
  document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
  document.querySelector('.view-btn[data-view="all"]').classList.add('active');
  render();
});

init();

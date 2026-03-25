// API base URL — empty string = same origin (works on Railway, VPS, etc.)
const API = '';

// Current language
let currentLang = "es";

// UI strings
const UI = {
  es: {
    loading: "Consultando a DeepSeek sobre las últimas noticias de Anthropic...",
    loadingTitle: "Obteniendo las noticias del día",
    loadingDate: "Cargando...",
    errorEmpty: "No se encontraron noticias hoy.",
    errorConnect: "Error al conectar con el servidor. Comprueba que el backend está funcionando.",
    retry: "Reintentar",
    footerApi: "Resúmenes generados con",
  },
  en: {
    loading: "Asking DeepSeek for the latest Anthropic news...",
    loadingTitle: "Fetching today's news",
    loadingDate: "Loading...",
    errorEmpty: "No news found today.",
    errorConnect: "Error connecting to the server. Check that the backend is running.",
    retry: "Retry",
    footerApi: "Summaries generated with",
  }
};

// Theme toggle
(function(){
  const t = document.querySelector('[data-theme-toggle]');
  const r = document.documentElement;
  let d = matchMedia('(prefers-color-scheme:dark)').matches ? 'dark' : 'light';
  r.setAttribute('data-theme', d);

  function updateIcon() {
    t.innerHTML = d === 'dark'
      ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>'
      : '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
  }

  updateIcon();

  t && t.addEventListener('click', () => {
    d = d === 'dark' ? 'light' : 'dark';
    r.setAttribute('data-theme', d);
    t.setAttribute('aria-label', d === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
    updateIcon();
  });
})();

// Language toggle
(function(){
  const btn = document.querySelector('[data-lang-toggle]');
  const labels = document.querySelectorAll('[data-lang-label]');

  function updateLabels() {
    labels.forEach(l => {
      l.classList.toggle('lang-active', l.dataset.langLabel === currentLang);
    });
  }

  btn && btn.addEventListener('click', () => {
    currentLang = currentLang === 'es' ? 'en' : 'es';
    updateLabels();
    updateFooter();
    loadNews();
  });
})();

// Update footer language (no-op now, footer is static)
function updateFooter() {}

// Fetch and render news
async function loadNews() {
  const heroDate = document.getElementById('hero-date');
  const heroTitle = document.getElementById('hero-title');
  const newsContent = document.getElementById('news-content');

  // Show loading
  heroDate.textContent = UI[currentLang].loadingDate;
  heroTitle.textContent = UI[currentLang].loadingTitle;
  newsContent.innerHTML = `
    <div class="loading-container">
      <div class="spinner"></div>
      <p class="loading-text">${UI[currentLang].loading}</p>
    </div>`;

  try {
    const res = await fetch(`${API}/api/news?lang=${currentLang}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    // Update hero
    heroDate.textContent = data.fecha || (currentLang === 'es' ? 'Hoy' : 'Today');
    heroTitle.textContent = data.titular_del_dia || 'Anthropic News';

    // Check for errors or empty news
    if (data.error || !data.noticias || data.noticias.length === 0) {
      newsContent.innerHTML = `
        <div class="error-container">
          <div class="error-icon">📡</div>
          <p class="error-message">${data.error || UI[currentLang].errorEmpty}</p>
          <button class="retry-btn" onclick="loadNews()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 4v6h6"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
            ${UI[currentLang].retry}
          </button>
        </div>`;
      return;
    }

    // Render news cards
    const cardsHTML = data.noticias.map((noticia, i) => {
      const sourceLink = noticia.url
        ? `<a href="${noticia.url}" target="_blank" rel="noopener noreferrer">${noticia.fuente}</a>`
        : `<span>${noticia.fuente}</span>`;

      return `
        <article class="news-card">
          <div>
            <span class="news-card-number">${i + 1}</span>
          </div>
          <h2 class="news-card-title">${noticia.titular}</h2>
          <p class="news-card-summary">${noticia.resumen}</p>
          <div class="news-card-source">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
            ${sourceLink}
          </div>
        </article>`;
    }).join('');

    newsContent.innerHTML = `<div class="news-grid">${cardsHTML}</div>`;

  } catch (err) {
    console.error('Error loading news:', err);
    newsContent.innerHTML = `
      <div class="error-container">
        <div class="error-icon">⚠️</div>
        <p class="error-message">${UI[currentLang].errorConnect}</p>
        <button class="retry-btn" onclick="loadNews()">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 4v6h6"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
          ${UI[currentLang].retry}
        </button>
      </div>`;
  }
}

// Load visit counter
async function loadVisits() {
  try {
    const res = await fetch(`${API}/api/visits`);
    if (res.ok) {
      const data = await res.json();
      const el = document.getElementById('visit-counter');
      if (el) el.textContent = `Visitas: ${data.count}`;
    }
  } catch (e) { /* silent */ }
}

// Load on page ready
document.addEventListener('DOMContentLoaded', () => {
  loadNews();
  loadVisits();
});

// OmniDownloader - Client Frontend Application
let currentExtractedData = null;
let currentFilteredFormats = [];
let currentSearchResults = [];
let currentFilter = 'all';

// DOM Elements
const sectionExtract = document.getElementById('section-extract');
const sectionSearch = document.getElementById('section-search');
const tabExtract = document.getElementById('tab-extract');
const tabSearch = document.getElementById('tab-search');
const extractUrlInput = document.getElementById('extract-url-input');
const searchQueryInput = document.getElementById('search-query-input');
const extractResultsContainer = document.getElementById('extract-results-container');
const searchResultsContainer = document.getElementById('search-results-container');
const searchGrid = document.getElementById('search-grid');
const searchCountBadge = document.getElementById('search-count-badge');

// Mode Switcher
function switchMode(mode) {
  if (mode === 'extract') {
    sectionExtract.classList.remove('hidden');
    sectionSearch.classList.add('hidden');

    tabExtract.className = 'flex items-center gap-2 px-3.5 py-1.5 rounded-lg font-medium transition-all text-white bg-purple-600 shadow-md';
    tabSearch.className = 'flex items-center gap-2 px-3.5 py-1.5 rounded-lg font-medium transition-all text-slate-400 hover:text-slate-200';
  } else {
    sectionExtract.classList.add('hidden');
    sectionSearch.classList.remove('hidden');

    tabExtract.className = 'flex items-center gap-2 px-3.5 py-1.5 rounded-lg font-medium transition-all text-slate-400 hover:text-slate-200';
    tabSearch.className = 'flex items-center gap-2 px-3.5 py-1.5 rounded-lg font-medium transition-all text-white bg-purple-600 shadow-md';
    searchQueryInput.focus();
  }
}

// Paste from Clipboard
async function pasteClipboard() {
  try {
    const text = await navigator.clipboard.readText();
    if (text) {
      extractUrlInput.value = text.trim();
      showToast('Pasted URL from clipboard', 'info');
      if (text.startsWith('http://') || text.startsWith('https://')) {
        handleExtract(new Event('submit'));
      }
    }
  } catch (err) {
    showToast('Unable to read clipboard. Please paste manually.', 'error');
  }
}

// Quick Sample Load
function loadSample(url) {
  switchMode('extract');
  extractUrlInput.value = url;
  handleExtract(new Event('submit'));
}

// Quick Search from Suggestions
function runSearch(query) {
  switchMode('search');
  searchQueryInput.value = query;
  handleSearch(new Event('submit'));
}

// Helper: Toggle Button Loading State
function setButtonLoading(btnId, spinnerId, textId, loading, defaultText) {
  const btn = document.getElementById(btnId);
  const spinner = document.getElementById(spinnerId);
  const text = document.getElementById(textId);
  if (!btn) return;

  btn.disabled = loading;
  if (loading) {
    spinner.classList.remove('hidden');
    text.textContent = 'Processing...';
    btn.classList.add('opacity-75', 'cursor-not-allowed');
  } else {
    spinner.classList.add('hidden');
    text.textContent = defaultText;
    btn.classList.remove('opacity-75', 'cursor-not-allowed');
  }
}

// Handle URL Extraction
async function handleExtract(event) {
  if (event && event.preventDefault) event.preventDefault();
  const url = extractUrlInput.value.trim();

  if (!url) {
    showToast('Please enter a video URL', 'error');
    return;
  }

  setButtonLoading('btn-extract', 'btn-extract-spinner', 'btn-extract-text', true, 'Extract Links');
  
  // Render loading skeleton
  extractResultsContainer.classList.remove('hidden');
  extractResultsContainer.innerHTML = `
    <div class="glass-panel rounded-2xl p-6 space-y-4 animate-pulse border border-slate-800">
      <div class="flex flex-col sm:flex-row gap-4">
        <div class="w-full sm:w-64 h-36 bg-slate-800 rounded-xl"></div>
        <div class="flex-1 space-y-3">
          <div class="h-6 bg-slate-800 rounded w-3/4"></div>
          <div class="h-4 bg-slate-800 rounded w-1/2"></div>
          <div class="h-4 bg-slate-800 rounded w-1/4"></div>
        </div>
      </div>
      <div class="h-10 bg-slate-800 rounded-lg"></div>
      <div class="space-y-2">
        <div class="h-12 bg-slate-800/60 rounded-xl"></div>
        <div class="h-12 bg-slate-800/60 rounded-xl"></div>
      </div>
    </div>
  `;

  try {
    const t0 = performance.now();
    const res = await fetch('/api/extract', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url })
    });

    const data = await res.json();
    const durationMs = Math.round(performance.now() - t0);

    if (!res.ok) {
      throw new Error(data.detail || data.error || 'Failed to extract video');
    }

    data._latencyMs = durationMs;
    currentExtractedData = data;
    renderExtractResults(data);
    showToast(`Successfully extracted in ${durationMs}ms`, 'success');
  } catch (err) {
    console.error('Extract error:', err);
    extractResultsContainer.innerHTML = `
      <div class="glass-panel rounded-2xl p-6 border border-red-500/30 bg-red-950/20 text-center space-y-3">
        <div class="w-12 h-12 rounded-full bg-red-500/20 text-red-400 mx-auto flex items-center justify-center">
          <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <h3 class="text-lg font-bold text-red-300">Extraction Failed</h3>
        <p class="text-sm text-slate-300 max-w-lg mx-auto">${escapeHtml(err.message)}</p>
        <p class="text-xs text-slate-400">Ensure the link is public and accessible without logging in.</p>
      </div>
    `;
    showToast(err.message, 'error');
  } finally {
    setButtonLoading('btn-extract', 'btn-extract-spinner', 'btn-extract-text', false, 'Extract Links');
  }
}

// Render Extracted Video and Available Formats
function renderExtractResults(data) {
  const platformColor = getPlatformBadgeClass(data.platform);
  
  extractResultsContainer.innerHTML = `
    <div class="glass-panel rounded-2xl p-5 sm:p-7 space-y-6 border border-slate-800 shadow-2xl">
      <!-- Media Header -->
      <div class="flex flex-col md:flex-row gap-5 items-start">
        <!-- Thumbnail / Preview -->
        <div class="relative w-full md:w-72 aspect-video bg-slate-900 rounded-xl overflow-hidden shadow-lg border border-slate-800 flex-shrink-0 group">
          <img src="${data.thumbnail || '/static/placeholder.jpg'}" alt="${escapeHtml(data.title)}" class="w-full h-full object-cover">
          <span class="absolute bottom-2 right-2 px-2 py-0.5 rounded bg-black/80 text-white font-mono text-xs backdrop-blur-sm">
            ${data.duration_formatted}
          </span>
          <a href="${data.webpage_url}" target="_blank" rel="noopener noreferrer" class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white text-xs font-semibold gap-1.5 backdrop-blur-[2px]">
            <span>Open Source</span>
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
          </a>
        </div>

        <!-- Video Info -->
        <div class="flex-1 space-y-2">
          <div class="flex flex-wrap items-center gap-2">
            <span class="px-2.5 py-0.5 rounded-md text-xs font-bold ${platformColor}">
              ${data.platform}
            </span>
            ${data._latencyMs !== undefined ? `
              <span class="px-2 py-0.5 rounded-md text-xs font-semibold ${data._latencyMs < 250 ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-slate-800 text-slate-400'} flex items-center gap-1">
                <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                <span>${data._latencyMs < 250 ? '⚡ Cached (' + data._latencyMs + 'ms)' : data._latencyMs + 'ms'}</span>
              </span>
            ` : ''}
            <span class="text-xs text-slate-400 flex items-center gap-1">
              <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
              ${escapeHtml(data.uploader || 'Creator')}
            </span>
          </div>

          <h2 class="text-xl sm:text-2xl font-extrabold text-white leading-snug">
            ${escapeHtml(data.title)}
          </h2>

          ${data.description ? `
            <p class="text-xs text-slate-400 line-clamp-2 max-w-2xl">
              ${escapeHtml(data.description)}
            </p>
          ` : ''}

          <!-- Quick 1-Click Best Quality Download -->
          ${data.best_direct_download ? `
            <div class="pt-3 flex flex-wrap gap-2.5">
              <a href="${data.best_direct_download}" download
                onclick="showToast('Starting best quality download...', 'success')"
                class="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold text-white bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 shadow-lg shadow-emerald-500/20 transition-all active:scale-[0.98]">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                <span>Quick Download Best MP4</span>
              </a>
              ${data.best_direct_url ? `
                <button type="button" onclick="copyBestDirectUrl(this)"
                  class="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-colors">
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                  <span>Copy Stream URL</span>
                </button>
              ` : ''}
            </div>
          ` : ''}
        </div>
      </div>

      <!-- Format Selection & Filtering Tabs -->
      <div class="border-t border-slate-800 pt-5 space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <h3 class="text-base font-bold text-slate-200 flex items-center gap-2">
            <span>Available Streams & Formats</span>
            <span class="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-purple-300 font-mono">
              ${data.formats ? data.formats.length : 0} options
            </span>
          </h3>

          <!-- Filter Pills -->
          <div class="flex items-center gap-1 bg-slate-900 p-1 rounded-xl border border-slate-800 text-xs">
            <button onclick="filterFormats('all')" id="filter-all" class="px-2.5 py-1 rounded-lg font-medium transition-colors bg-purple-600 text-white">All</button>
            <button onclick="filterFormats('combined')" id="filter-combined" class="px-2.5 py-1 rounded-lg font-medium transition-colors text-slate-400 hover:text-slate-200">Video + Audio</button>
            <button onclick="filterFormats('audio_only')" id="filter-audio_only" class="px-2.5 py-1 rounded-lg font-medium transition-colors text-slate-400 hover:text-slate-200">Audio Only</button>
            <button onclick="filterFormats('video_only')" id="filter-video_only" class="px-2.5 py-1 rounded-lg font-medium transition-colors text-slate-400 hover:text-slate-200">Video Only</button>
          </div>
        </div>

        <!-- Formats List Container -->
        <div id="formats-list" class="space-y-2">
          <!-- Populated by filterFormats -->
        </div>
      </div>
    </div>
  `;

  filterFormats('all');
}

// Filter and Render Format Rows
function filterFormats(category) {
  currentFilter = category;
  const listContainer = document.getElementById('formats-list');
  if (!listContainer || !currentExtractedData) return;

  // Update pill styles
  ['all', 'combined', 'audio_only', 'video_only'].forEach(cat => {
    const btn = document.getElementById(`filter-${cat}`);
    if (btn) {
      if (cat === category) {
        btn.className = 'px-2.5 py-1 rounded-lg font-medium transition-colors bg-purple-600 text-white';
      } else {
        btn.className = 'px-2.5 py-1 rounded-lg font-medium transition-colors text-slate-400 hover:text-slate-200';
      }
    }
  });

  const allFormats = currentExtractedData.formats || [];
  currentFilteredFormats = category === 'all'
    ? allFormats
    : allFormats.filter(f => f.category === category);

  if (currentFilteredFormats.length === 0) {
    listContainer.innerHTML = `
      <div class="text-center py-8 text-sm text-slate-500 bg-slate-900/40 rounded-xl border border-slate-800/60">
        No formats available for the selected category.
      </div>
    `;
    return;
  }

  listContainer.innerHTML = currentFilteredFormats.map((fmt, index) => {
    const isDirectCombined = fmt.category === 'combined';
    const badgeBg = isDirectCombined ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                    fmt.category === 'audio_only' ? 'bg-amber-500/10 text-amber-300 border border-amber-500/20' :
                    'bg-indigo-500/10 text-indigo-300 border border-indigo-500/20';

    return `
      <div class="format-row flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 sm:px-4 rounded-xl bg-slate-900/60 border border-slate-800/80">
        <!-- Quality Info -->
        <div class="flex items-center gap-3">
          <span class="px-2.5 py-1 rounded-lg text-xs font-bold ${badgeBg}">
            ${fmt.resolution}
          </span>
          <div class="space-y-0.5">
            <div class="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <span>${escapeHtml(fmt.quality_label)}</span>
              ${fmt.is_direct_mp4 ? `
                <span class="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-700">Direct MP4</span>
              ` : ''}
            </div>
            <div class="text-xs text-slate-400 flex items-center gap-2">
              <span class="uppercase font-mono">${fmt.ext}</span>
              <span>•</span>
              <span>${fmt.filesize_formatted}</span>
              ${fmt.fps ? `<span>•</span><span>${fmt.fps} fps</span>` : ''}
            </div>
          </div>
        </div>

        <!-- Download & Direct Link Actions -->
        <div class="flex items-center gap-2 sm:self-center">
          <!-- Copy Direct Stream Link -->
          <button type="button" onclick="copyFormatUrl(${index}, this)"
            title="Copy direct stream URL"
            class="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition-colors flex items-center gap-1">
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
            <span class="copy-text">Copy URL</span>
          </button>

          <!-- Open Direct Stream in New Tab -->
          <a href="${fmt.url}" target="_blank" rel="noopener noreferrer"
            title="Open stream in player"
            class="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition-colors flex items-center gap-1">
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
            <span>Preview</span>
          </a>

          <!-- Download Action -->
          <a href="${fmt.download_url}" download
            onclick="showToast('Download started for ${fmt.resolution} (${fmt.ext.toUpperCase()})', 'success')"
            class="px-3.5 py-1.5 rounded-lg text-xs font-bold text-white bg-purple-600 hover:bg-purple-500 shadow-md shadow-purple-600/20 transition-all flex items-center gap-1.5 active:scale-95">
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            <span>Download</span>
          </a>
        </div>
      </div>
    `;
  }).join('');
}

// Copy format direct stream URL by index
function copyFormatUrl(index, btn) {
  const fmt = currentFilteredFormats[index];
  if (fmt && fmt.url) {
    copyToClipboard(fmt.url, btn);
  }
}

// Copy best direct stream URL
function copyBestDirectUrl(btn) {
  if (currentExtractedData && currentExtractedData.best_direct_url) {
    copyToClipboard(currentExtractedData.best_direct_url, btn);
  }
}

// Handle YouTube Search
async function handleSearch(event) {
  if (event && event.preventDefault) event.preventDefault();
  const query = searchQueryInput.value.trim();

  if (!query) {
    showToast('Please enter a search query', 'error');
    return;
  }

  setButtonLoading('btn-search', 'btn-search-spinner', 'btn-search-text', true, 'Search');

  searchResultsContainer.classList.remove('hidden');
  searchCountBadge.textContent = 'Searching...';
  searchGrid.innerHTML = Array(6).fill(0).map(() => `
    <div class="glass-panel rounded-xl p-3 space-y-3 animate-pulse border border-slate-800">
      <div class="aspect-video bg-slate-800 rounded-lg"></div>
      <div class="h-4 bg-slate-800 rounded w-3/4"></div>
      <div class="h-3 bg-slate-800 rounded w-1/2"></div>
    </div>
  `).join('');

  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=10`);
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || data.error || 'Failed to search YouTube');
    }

    currentSearchResults = data.results || [];
    renderSearchResults(data);
  } catch (err) {
    console.error('Search error:', err);
    searchGrid.innerHTML = `
      <div class="col-span-full py-8 text-center text-sm text-red-400 bg-red-950/20 border border-red-500/20 rounded-xl">
        ${escapeHtml(err.message)}
      </div>
    `;
    showToast(err.message, 'error');
  } finally {
    setButtonLoading('btn-search', 'btn-search-spinner', 'btn-search-text', false, 'Search');
  }
}

// Render Search Results Grid
function renderSearchResults(data) {
  const items = currentSearchResults;
  searchCountBadge.textContent = `${items.length} results`;

  if (items.length === 0) {
    searchGrid.innerHTML = `
      <div class="col-span-full py-12 text-center text-slate-400">
        No results found for "${escapeHtml(data.query)}". Try another keyword.
      </div>
    `;
    return;
  }

  searchGrid.innerHTML = items.map((item, index) => `
    <div class="glass-panel rounded-xl overflow-hidden border border-slate-800 hover:border-purple-600/50 transition-all flex flex-col group hover:-translate-y-1 shadow-lg">
      <!-- Thumbnail with Duration -->
      <div class="relative aspect-video bg-slate-900 overflow-hidden cursor-pointer" onclick="selectSearchIndex(${index})">
        <img src="${item.thumbnail || '/static/placeholder.jpg'}" alt="${escapeHtml(item.title)}" loading="lazy" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300">
        <span class="absolute bottom-2 right-2 px-1.5 py-0.5 rounded bg-black/80 text-white font-mono text-[11px]">
          ${item.duration_formatted}
        </span>
      </div>

      <!-- Info & Quick Action -->
      <div class="p-4 flex-1 flex flex-col justify-between gap-3">
        <div class="space-y-1">
          <h3 class="font-bold text-sm text-slate-100 line-clamp-2 leading-snug hover:text-purple-300 cursor-pointer" onclick="selectSearchIndex(${index})">
            ${escapeHtml(item.title)}
          </h3>
          <div class="flex items-center justify-between text-xs text-slate-400">
            <span class="truncate max-w-[140px]">${escapeHtml(item.channel || 'Channel')}</span>
            <span>${item.views}</span>
          </div>
        </div>

        <button type="button" onclick="selectSearchIndex(${index})"
          class="w-full py-2 px-3 rounded-lg text-xs font-bold text-white bg-purple-600 hover:bg-purple-500 shadow-md shadow-purple-600/20 transition-all flex items-center justify-center gap-1.5 active:scale-95">
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          <span>Select & Download</span>
        </button>
      </div>
    </div>
  `).join('');
}

// Select search result by index
function selectSearchIndex(index) {
  const item = currentSearchResults[index];
  if (item && item.url) {
    selectSearchItem(item.url);
  }
}

// Select a Video from Search and Switch to Extract
function selectSearchItem(url) {
  switchMode('extract');
  extractUrlInput.value = url;
  handleExtract(new Event('submit'));
  window.scrollTo({ top: 120, behavior: 'smooth' });
}

// Copy to Clipboard with Feedback
async function copyToClipboard(text, btnElement) {
  try {
    await navigator.clipboard.writeText(text);
    showToast('Direct stream link copied to clipboard!', 'success');
    if (btnElement) {
      const originalText = btnElement.innerHTML;
      btnElement.innerHTML = `
        <svg class="w-3.5 h-3.5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
        <span class="text-emerald-400">Copied!</span>
      `;
      setTimeout(() => {
        btnElement.innerHTML = originalText;
      }, 2000);
    }
  } catch (err) {
    showToast('Failed to copy. Please copy manually.', 'error');
  }
}

// Toast Notifications
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  const bg = type === 'success' ? 'bg-emerald-950 border-emerald-700/80 text-emerald-200' :
             type === 'error' ? 'bg-red-950 border-red-700/80 text-red-200' :
             'bg-slate-900 border-slate-700 text-slate-200';

  toast.className = `toast-enter pointer-events-auto p-3.5 rounded-xl border shadow-xl flex items-center justify-between gap-3 text-xs sm:text-sm font-medium ${bg}`;
  toast.innerHTML = `
    <div class="flex items-center gap-2">
      ${type === 'success' ? '<svg class="w-4 h-4 text-emerald-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>' :
        type === 'error' ? '<svg class="w-4 h-4 text-red-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>' :
        '<svg class="w-4 h-4 text-purple-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>'
      }
      <span>${escapeHtml(message)}</span>
    </div>
    <button onclick="this.parentElement.remove()" class="text-slate-400 hover:text-white p-0.5">&times;</button>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 4000);
}

// Helper: Escape HTML
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Helper: Platform Badge Class
function getPlatformBadgeClass(platform) {
  const p = (platform || '').toLowerCase();
  if (p.includes('youtube')) return 'bg-red-500/10 text-red-400 border border-red-500/20';
  if (p.includes('instagram')) return 'bg-pink-500/10 text-pink-400 border border-pink-500/20';
  if (p.includes('facebook')) return 'bg-blue-500/10 text-blue-400 border border-blue-500/20';
  if (p.includes('snapchat')) return 'bg-amber-500/10 text-amber-300 border border-amber-500/20';
  if (p.includes('tiktok')) return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
  return 'bg-purple-500/10 text-purple-300 border border-purple-500/20';
}

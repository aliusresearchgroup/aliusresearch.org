/* Fit the .section-nav items to the available width using pretext for
 * canvas-based text measurement. Scales font-size down (within a min/max
 * range) so labels fit on one row when possible; falls back to horizontal
 * scroll-snap when items are too long to shrink-fit.
 *
 * Integration notes:
 * - pretext (https://www.npmjs.com/package/@chenglou/pretext) is loaded
 *   dynamically from esm.sh. If it fails to load (blocked by CSP, offline,
 *   etc.), we fall back to a minimal canvas measureText shim with the same
 *   cache semantics.
 * - Recomputed on load, font-load (document.fonts.ready), and resize.
 */
(function () {
  'use strict';

  var MIN_FONT_PX = 9;
  var MAX_FONT_PX = 13; // matches CSS .section-nav a default
  var PAD_X_PX = 28;    // approx horizontal padding per pill (CSS 0.85rem×2)
  var GAP_PX = 6;       // approx CSS gap between items
  var SAFETY_PX = 24;   // breathing room at edges

  var state = {
    measure: null,      // function(text, font) -> pixel width
    canvasCtx: null,
    fontFamily: 'Raleway, sans-serif',
    letterSpacing: 0.08, // em
  };

  function initCanvasFallback() {
    if (state.canvasCtx) return state.canvasCtx;
    try {
      var c = typeof OffscreenCanvas !== 'undefined'
        ? new OffscreenCanvas(1, 1)
        : document.createElement('canvas');
      state.canvasCtx = c.getContext('2d');
      return state.canvasCtx;
    } catch (_e) {
      return null;
    }
  }

  function measureViaCanvas(text, fontSpec) {
    var ctx = initCanvasFallback();
    if (!ctx) return text.length * 7; // rough guess
    ctx.font = fontSpec;
    // Canvas measureText ignores CSS letter-spacing; add it back manually.
    var base = ctx.measureText(text).width;
    var fontSizePx = parseFloat(fontSpec) || MAX_FONT_PX;
    return base + (text.length - 1) * state.letterSpacing * fontSizePx;
  }

  function buildFontSpec(pxSize) {
    // Must match the weight/style used by the nav CSS so pretext measures
    // with the same metrics the browser would.
    return 'bold ' + pxSize + 'px ' + state.fontFamily;
  }

  function measureWithPretext(textModule) {
    // pretext's getMeasureContext returns a canvas ctx; we still drive it
    // with ctx.font + ctx.measureText. The win is the shared cache and
    // consistent engine profile across Safari/Chromium/Firefox.
    var ctx = textModule.getMeasureContext();
    var caches = {};
    return function (text, fontSpec) {
      ctx.font = fontSpec;
      var cache = caches[fontSpec] || (caches[fontSpec] = textModule.getSegmentMetricCache
        ? textModule.getSegmentMetricCache(fontSpec)
        : new Map());
      var hit = cache.get(text);
      if (hit && typeof hit.width === 'number') return hit.width;
      var w = ctx.measureText(text).width;
      var fontSizePx = parseFloat(fontSpec) || MAX_FONT_PX;
      w += (text.length - 1) * state.letterSpacing * fontSizePx;
      if (hit) { hit.width = w; } else { cache.set(text, { width: w, containsCJK: false }); }
      return w;
    };
  }

  function totalWidthNeeded(labels, fontSizePx) {
    var spec = buildFontSpec(fontSizePx);
    var total = 0;
    for (var i = 0; i < labels.length; i++) {
      total += state.measure(labels[i], spec) + PAD_X_PX;
    }
    total += GAP_PX * Math.max(0, labels.length - 1);
    total += SAFETY_PX;
    return total;
  }

  function fit(nav) {
    var list = nav.querySelector('ol');
    if (!list) return;
    var items = list.querySelectorAll('a');
    if (!items.length) return;
    var labels = [];
    for (var i = 0; i < items.length; i++) {
      labels.push((items[i].textContent || '').trim().toUpperCase());
    }
    var available = nav.clientWidth - 20; // account for nav padding
    if (available <= 0) return;

    // Binary-search (integer px) the largest font size that fits.
    var lo = MIN_FONT_PX, hi = MAX_FONT_PX, best = MIN_FONT_PX;
    while (lo <= hi) {
      var mid = (lo + hi) >> 1;
      if (totalWidthNeeded(labels, mid) <= available) {
        best = mid;
        lo = mid + 1;
      } else {
        hi = mid - 1;
      }
    }
    nav.style.setProperty('--section-nav-font-size', best + 'px');
    // If even the min size doesn't fit, horizontal scroll-snap kicks in via CSS.
    var fits = totalWidthNeeded(labels, MIN_FONT_PX) <= available;
    nav.classList.toggle('is-overflow', !fits);
  }

  function fitAll() {
    var navs = document.querySelectorAll('.section-nav');
    for (var i = 0; i < navs.length; i++) fit(navs[i]);
  }

  function boot() {
    // Try pretext, fall back to canvas-only measurement.
    state.measure = measureViaCanvas;
    fitAll();

    // Dynamic import of pretext from esm.sh. Runs async; once loaded, rerun
    // the fit with pretext's more accurate cached measurements.
    try {
      var url = 'https://esm.sh/@chenglou/pretext@0.0.4';
      import(/* @vite-ignore */ url).then(function (mod) {
        if (mod && typeof mod.getMeasureContext === 'function') {
          state.measure = measureWithPretext(mod);
          fitAll();
        }
      }).catch(function () {
        // Network/CSP blocked; keep canvas fallback already active.
      });
    } catch (_e) { /* older browsers without dynamic import: canvas fallback is fine */ }

    // Refit when fonts finish loading (Raleway may not be ready at DOMContentLoaded)
    if (document.fonts && document.fonts.ready && typeof document.fonts.ready.then === 'function') {
      document.fonts.ready.then(fitAll).catch(function () {});
    }

    // Debounced resize / orientation handler
    var raf = 0;
    window.addEventListener('resize', function () {
      if (raf) cancelAnimationFrame(raf);
      raf = requestAnimationFrame(function () { raf = 0; fitAll(); });
    }, { passive: true });
    window.addEventListener('orientationchange', fitAll, { passive: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();

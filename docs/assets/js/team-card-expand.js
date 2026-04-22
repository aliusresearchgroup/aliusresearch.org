/* Team-card click-to-expand: GPU-smooth transform:scale, pretext-driven.
 *
 * Why this is smoother than grid-template-* animation:
 *   - transform is composited on the GPU; no layout reflow per frame
 *   - CSS transitions on transform are consistently smooth across browsers
 *   - The bio's `font-size` is what actually reveals the text — it
 *     transitions from 0 → 14px over 2400ms, so text emerges gradually
 *     from nothing (user wanted: "text doesn't appear out of nowhere,
 *     it could just shrink so small that it's practically invisible")
 *
 * Pretext's role:
 *   Pretext measures the bio text's natural layout given the card's
 *   current width and a target font-size. We iterate to find the smallest
 *   `scale` factor such that the scaled card (original_w × scale by
 *   original_h × scale) is a square and fits the bio at readable font.
 *   This makes the expanded card's size genuinely driven by the length
 *   of that specific member's biography.
 */
(function () {
  'use strict';

  var state = { expanded: null, measure: null };

  function init() {
    if (!document.querySelector('.team-card')) return;
    document.addEventListener('click', onDocClick, true);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') collapse();
    });
    window.addEventListener('resize', function () {
      if (state.expanded) {
        var c = state.expanded; collapse(true);
        requestAnimationFrame(function () { expand(c); });
      }
    }, { passive: true });

    try {
      import(/* @vite-ignore */ 'https://esm.sh/@chenglou/pretext@0.0.4')
        .then(function (mod) { if (mod && mod.getMeasureContext) state.measure = makeMeasurer(mod); })
        .catch(function () {});
    } catch (_e) {}
  }

  function makeMeasurer(mod) {
    return function (text, fontSpec, availablePx, lineHeightPx) {
      try {
        var ctx = mod.getMeasureContext();
        ctx.font = fontSpec;
        var words = text.split(/\s+/);
        var lines = 1;
        var current = '';
        for (var i = 0; i < words.length; i++) {
          var candidate = current ? current + ' ' + words[i] : words[i];
          var w = ctx.measureText(candidate).width;
          if (w > availablePx && current) { lines++; current = words[i]; }
          else { current = candidate; }
        }
        return Math.ceil(lines * lineHeightPx);
      } catch (_e) { return null; }
    };
  }

  function measureBioHeight(text, fontSizePx, lineHeightMultiplier, widthPx) {
    var lineHeight = fontSizePx * lineHeightMultiplier;
    var fontSpec = '400 ' + fontSizePx + 'px Raleway, sans-serif';
    if (state.measure) {
      var h = state.measure(text, fontSpec, widthPx, lineHeight);
      if (h) return h;
    }
    // Canvas fallback
    try {
      var canvas = document.createElement('canvas');
      var ctx = canvas.getContext('2d');
      ctx.font = fontSpec;
      var words = text.split(/\s+/);
      var lines = 1;
      var current = '';
      for (var i = 0; i < words.length; i++) {
        var candidate = current ? current + ' ' + words[i] : words[i];
        if (ctx.measureText(candidate).width > widthPx && current) { lines++; current = words[i]; }
        else { current = candidate; }
      }
      return Math.ceil(lines * lineHeight);
    } catch (_e) { return 200; }
  }

  /**
   * Compute the scale factor such that the scaled card is:
   *   - large enough vertically to fit all chrome + bio content
   *   - a square (effective width × scale ≈ effective height × scale)
   *
   * Because transform:scale is uniform, the scaled card preserves aspect.
   * If the default card is already near-square, a single scale factor
   * works. Otherwise we pick the larger of the two ratios.
   */
  function computeExpandScale(card) {
    var bio = card.querySelector('.team-card__bio');
    if (!bio) return 1.6;
    var text = (bio.textContent || '').trim();
    if (!text) return 1.4;

    var cardRect = card.getBoundingClientRect();
    var naturalW = cardRect.width;
    var naturalH = cardRect.height;

    // When the card is scaled by X, its contents are scaled by X too.
    // Bio will occupy naturalW * X available width at font-size (14 * X).
    // But pretext measures in absolute pixels. So we can measure at the
    // SOURCE font-size (14px) against the source width (naturalW - padX).
    // Result height in source-px. After scaling by X, visible height is
    // H*X. Total scaled card height = (chrome + bio_h) * X.
    var cs = getComputedStyle(card);
    var padX = (parseFloat(cs.paddingLeft) || 0) + (parseFloat(cs.paddingRight) || 0);
    var bioWidth = Math.max(80, naturalW - padX);
    var bioH = measureBioHeight(text, 14, 1.55, bioWidth);
    var chromeH = naturalH;  // current height with bio at font-size 0 ≈ chrome only
    var requiredSourceH = chromeH + 16 + bioH + 20;  // + margin-top + bottom slack

    // The scaled card will have height = requiredSourceH when we scale by
    // (requiredSourceH / naturalH)? Not quite — scale is uniform, so the
    // bio's content at scale X is laid out at naturalW px and then scaled.
    // So the apparent height is requiredSourceH * X if we want the bio to
    // fit. But we need the CARD's apparent height to equal requiredSourceH,
    // i.e. naturalH * X = requiredSourceH → X = requiredSourceH / naturalH.
    // This gives the square-shaped growth.
    var scaleForHeight = requiredSourceH / naturalH;
    // Also ensure visible width is at least some readable minimum (380px)
    var scaleForWidth = 380 / naturalW;
    var scale = Math.max(scaleForHeight, scaleForWidth);

    // Bound so it doesn't overflow the grid container
    var grid = card.closest('.team-grid');
    var gridWidth = grid ? grid.getBoundingClientRect().width : 1200;
    var maxScale = (gridWidth * 0.62) / naturalW;  // up to ~62% of grid
    scale = Math.min(scale, maxScale);
    scale = Math.max(scale, 1.25);                  // minimum growth
    return Math.round(scale * 100) / 100;
  }

  function onDocClick(e) {
    var card = e.target.closest && e.target.closest('.team-card');
    if (!card) return;
    if (e.target.closest('.team-card__icon, .team-card__links a, .team-card__links span')) return;
    e.preventDefault();
    if (card === state.expanded) collapse();
    else expand(card);
  }

  function expand(card) {
    var grid = card.closest('.team-grid');
    if (!grid) return;

    if (state.expanded && state.expanded !== card) {
      state.expanded.classList.remove('team-card--expanded');
      state.expanded.style.removeProperty('--expand-scale');
    }

    var scale = computeExpandScale(card);
    card.style.setProperty('--expand-scale', scale);
    card.classList.add('team-card--expanded');
    grid.classList.add('team-grid--has-expanded');
    state.expanded = card;
  }

  function collapse(skipState) {
    if (!state.expanded) return;
    var prev = state.expanded;
    var grid = prev.closest('.team-grid');
    prev.classList.remove('team-card--expanded');
    prev.style.removeProperty('--expand-scale');
    if (grid) grid.classList.remove('team-grid--has-expanded');
    if (!skipState) state.expanded = null;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else { init(); }
})();

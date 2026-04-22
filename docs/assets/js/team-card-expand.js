/* Team-card click-to-expand: grid-track animation, cell = content-sized square.
 *
 * Mental model (user's words):
 *   "The boxes are inside a grid. What changes is only the size of the
 *    boxes in the grid — the grid lines dynamically get bigger or smaller.
 *    The box should become a square, only so big as the amount of content
 *    warrants — at a legible font."
 *
 * Implementation:
 *   1. Pretext measures the clicked card's bio at a candidate reading
 *      width. Iterate until card-width ≈ card-height → the smallest square
 *      that fully fits the member's content at the default font size.
 *   2. Write inline `grid-template-columns` with that pixel size on the
 *      clicked card's column and `minmax(0, 1fr)` on the rest. Same for
 *      grid-template-rows.
 *   3. CSS animates grid-template-* natively at 1800ms cubic-bezier.
 *      Photos, names, icon buttons — every inner element — stay at their
 *      natural pixel sizes; only the CELL grows into a content-sized
 *      square and the grid lines slide.
 */
(function () {
  'use strict';

  var ANIM_MS = 2400;
  var DEFAULT_ROW_PX = 240;      // matches CSS grid-auto-rows default
  var MIN_SQUARE = 320;
  var MAX_SQUARE_FRAC = 0.6;     // up to 60% of grid width
  var MAX_SQUARE_ABS = 640;      // hard cap (readability)
  var state = { expanded: null, measure: null };

  function init() {
    if (!document.querySelector('.team-card')) return;
    document.addEventListener('click', onDocClick, true);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') collapse();
    });
    window.addEventListener('resize', function () {
      if (state.expanded) {
        var c = state.expanded;
        collapse(true);
        // Re-apply after one frame so the grid re-measures
        requestAnimationFrame(function () { expand(c); });
      }
    }, { passive: true });

    try {
      import(/* @vite-ignore */ 'https://esm.sh/@chenglou/pretext@0.0.4')
        .then(function (mod) {
          if (mod && mod.getMeasureContext) state.measure = makeMeasurer(mod);
        })
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
          if (w > availablePx && current) {
            lines++;
            current = words[i];
          } else {
            current = candidate;
          }
        }
        return Math.ceil(lines * lineHeightPx);
      } catch (_e) {
        return null;
      }
    };
  }

  function getComputedFont(el) {
    var s = getComputedStyle(el);
    return (s.fontStyle || '') + ' ' + (s.fontWeight || '') + ' ' +
           s.fontSize + ' / ' + s.lineHeight + ' ' + s.fontFamily;
  }

  function measureBioHeightAtWidth(bioEl, widthPx) {
    if (!bioEl || widthPx <= 0) return 0;
    var text = (bioEl.textContent || '').trim();
    var cs = getComputedStyle(bioEl);
    var lineHeight = parseFloat(cs.lineHeight);
    if (!lineHeight || !isFinite(lineHeight)) lineHeight = parseFloat(cs.fontSize) * 1.7;
    if (state.measure && text) {
      var h = state.measure(text, getComputedFont(bioEl), widthPx, lineHeight);
      if (h) return h;
    }
    var clone = bioEl.cloneNode(true);
    clone.style.cssText = (
      'position:absolute; left:-9999px; top:0; width:' + widthPx + 'px; ' +
      'max-height:none; -webkit-line-clamp:unset; display:block;'
    );
    document.body.appendChild(clone);
    var h2 = clone.scrollHeight;
    document.body.removeChild(clone);
    return h2;
  }

  /**
   * Iteratively find the smallest square size S such that:
   *   S ≥ chromeHeight + bioHeight(S - paddingX)
   * i.e. a square that's tall enough to fit the photo+name+role+icons
   * (the "chrome") plus the bio text at width (S - paddingX).
   */
  function computeSquareSize(card, bioEl, grid) {
    // Chrome = photo + name + role + icons + paddings, as rendered WITH the
    // bio hidden (default state). getBoundingClientRect gives us that.
    var chromeHeight = card.getBoundingClientRect().height;
    var cs = getComputedStyle(card);
    var paddingX = (parseFloat(cs.paddingLeft) || 0) + (parseFloat(cs.paddingRight) || 0);

    var gridWidth = grid.getBoundingClientRect().width;
    var hardMax = Math.min(MAX_SQUARE_ABS, gridWidth * MAX_SQUARE_FRAC);

    // Iterate to find smallest square S where S >= chrome + bio margin-top +
    // bio_height_at_width(S - paddingX) + bottom breathing room.
    var BIO_MARGIN_TOP = 16;
    var BOTTOM_SLACK = 24;
    var S = 440;
    for (var i = 0; i < 8; i++) {
      var bioWidth = Math.max(100, S - paddingX);
      var bioH = measureBioHeightAtWidth(bioEl, bioWidth);
      var neededH = chromeHeight + BIO_MARGIN_TOP + bioH + BOTTOM_SLACK;
      if (Math.abs(S - neededH) < 8) {
        S = Math.max(S, neededH);
        break;
      }
      S = (S + neededH) / 2;
    }
    return Math.round(Math.max(MIN_SQUARE, Math.min(hardMax, S)));
  }

  function onDocClick(e) {
    var card = e.target.closest && e.target.closest('.team-card');
    if (!card) return;
    if (e.target.closest('.team-card__icon, .team-card__links a, .team-card__links span')) return;
    e.preventDefault();
    if (card === state.expanded) {
      collapse();
    } else {
      expand(card);
    }
  }

  function getGridDimensions(grid) {
    var cs = getComputedStyle(grid);
    var colTracks = cs.gridTemplateColumns.split(/\s+/).filter(Boolean);
    return { cols: colTracks.length || 1 };
  }

  function expand(card) {
    var grid = card.closest('.team-grid');
    if (!grid) return;
    var cards = Array.from(grid.querySelectorAll('.team-card'));
    var idx = cards.indexOf(card);
    if (idx < 0) return;

    var dims = getGridDimensions(grid);
    var bioEl = card.querySelector('.team-card__bio');

    // Single-column mobile: just un-clamp bio via max-height
    if (dims.cols <= 1) {
      if (bioEl) {
        var w1 = bioEl.getBoundingClientRect().width - 4;
        var h1 = measureBioHeightAtWidth(bioEl, w1);
        card.style.setProperty('--expanded-bio-height', h1 + 'px');
      }
      if (state.expanded && state.expanded !== card) {
        state.expanded.classList.remove('team-card--expanded');
        state.expanded.style.removeProperty('--expanded-bio-height');
      }
      card.classList.add('team-card--expanded');
      grid.classList.add('team-grid--has-expanded');
      state.expanded = card;
      return;
    }

    // Compute the smallest content-fitting square
    var S = bioEl ? computeSquareSize(card, bioEl, grid) : 440;

    // Collapse previous (silent)
    if (state.expanded && state.expanded !== card) {
      state.expanded.classList.remove('team-card--expanded');
      state.expanded.style.removeProperty('--expanded-bio-height');
    }

    // Set the bio's target max-height to its natural pixel height at the
    // square's interior width, so the bio reveals exactly to fit.
    var cs = getComputedStyle(card);
    var paddingX = (parseFloat(cs.paddingLeft) || 0) + (parseFloat(cs.paddingRight) || 0);
    var targetBioWidth = Math.max(80, S - paddingX);
    var bioHeight = measureBioHeightAtWidth(bioEl, targetBioWidth);
    card.style.setProperty('--expanded-bio-height', bioHeight + 'px');

    // Build grid-template-columns: clicked col = Spx, others = 1fr
    var col = idx % dims.cols;
    var row = Math.floor(idx / dims.cols);
    var totalRows = Math.ceil(cards.length / dims.cols);
    var colParts = [];
    for (var c = 0; c < dims.cols; c++) {
      colParts.push(c === col ? (S + 'px') : 'minmax(0, 1fr)');
    }
    // Explicit per-row template so every non-expanded row stays at the
    // same uniform height — borders snap cleanly at row boundaries.
    var rowParts = [];
    for (var r = 0; r < totalRows; r++) {
      rowParts.push(r === row ? (S + 'px') : (DEFAULT_ROW_PX + 'px'));
    }

    grid.style.gridTemplateColumns = colParts.join(' ');
    grid.style.gridTemplateRows = rowParts.join(' ');
    card.classList.add('team-card--expanded');
    grid.classList.add('team-grid--has-expanded');

    state.expanded = card;
  }

  function collapse(skipState) {
    if (!state.expanded) return;
    var prev = state.expanded;
    var grid = prev.closest('.team-grid');
    if (grid) {
      grid.style.removeProperty('grid-template-columns');
      grid.style.removeProperty('grid-template-rows');
      grid.classList.remove('team-grid--has-expanded');
    }
    prev.classList.remove('team-card--expanded');
    prev.style.removeProperty('--expanded-bio-height');
    if (!skipState) state.expanded = null;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

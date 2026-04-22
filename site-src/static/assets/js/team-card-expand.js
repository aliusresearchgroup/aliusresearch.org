/* Team-card click-to-expand: GRID-TRACK animation.
 *
 * Conceptual model (user's words):
 *   "The boxes are inside a grid. What changes is only the size of the
 *    boxes in the grid — the grid lines dynamically get bigger or smaller."
 *
 * Implementation: CSS can natively animate `grid-template-columns` and
 * `grid-template-rows`. We compute the clicked card's column + row index
 * and write an inline grid-template with that column + row weighted up
 * (more fr) and the other tracks weighted down. The browser smoothly
 * slides the grid lines; cards sit inside their cells unchanged.
 *
 * Nothing inside any card scales — photos, names, icon buttons all keep
 * their natural sizes. Bios just have more or less horizontal space to
 * wrap into, clipped by CSS max-height.
 *
 * Pretext: on expand, we read the final (post-transition) width of the
 * clicked card's cell and measure the bio's natural pixel height at that
 * width so `--expanded-bio-height` is exact before the animation begins.
 */
(function () {
  'use strict';

  var ANIM_MS = 1600;
  var EXPANDED_WEIGHT = 2.4;
  var SHRUNK_WEIGHT = 0.6;
  var state = { expanded: null, measure: null };

  function init() {
    if (!document.querySelector('.team-card')) return;
    document.addEventListener('click', onDocClick, true);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') collapse();
    });
    window.addEventListener('resize', function () {
      // Column count may have changed → re-run expand math if something is open
      if (state.expanded) {
        var c = state.expanded;
        collapse(true);
        expand(c);
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
      if (h) return h + 10;
    }
    // Offscreen fallback
    var clone = bioEl.cloneNode(true);
    clone.style.cssText = (
      'position:absolute; left:-9999px; top:0; ' +
      'width:' + widthPx + 'px; max-height:none; ' +
      '-webkit-line-clamp:unset; display:block;'
    );
    document.body.appendChild(clone);
    var h2 = clone.scrollHeight;
    document.body.removeChild(clone);
    return h2 + 10;
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
    var rowTracks = cs.gridTemplateRows.split(/\s+/).filter(Boolean);
    return { cols: colTracks.length || 1, rows: rowTracks.length || 1 };
  }

  function buildWeightedTemplate(count, highlightIndex) {
    var parts = [];
    for (var i = 0; i < count; i++) {
      parts.push(i === highlightIndex ?
        'minmax(0, ' + EXPANDED_WEIGHT + 'fr)' :
        'minmax(0, ' + SHRUNK_WEIGHT + 'fr)'
      );
    }
    return parts.join(' ');
  }

  function expand(card) {
    var grid = card.closest('.team-grid');
    if (!grid) return;
    var cards = Array.from(grid.querySelectorAll('.team-card'));
    var idx = cards.indexOf(card);
    if (idx < 0) return;

    var dims = getGridDimensions(grid);
    if (dims.cols <= 1) {
      // Single-column (narrow mobile) — accordion via bio max-height only
      var bioEl1 = card.querySelector('.team-card__bio');
      if (bioEl1) {
        var w1 = bioEl1.getBoundingClientRect().width - 4;
        var h1 = measureBioHeightAtWidth(bioEl1, w1);
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

    var col = idx % dims.cols;
    var row = Math.floor(idx / dims.cols);
    var totalRows = Math.ceil(cards.length / dims.cols);

    // Estimate the clicked card's final cell width so pretext can measure
    // the bio wrap at the right width.
    var gridRect = grid.getBoundingClientRect();
    var csGrid = getComputedStyle(grid);
    var gapPx = parseFloat(csGrid.columnGap) || 0;
    var padL = parseFloat(csGrid.paddingLeft) || 0;
    var padR = parseFloat(csGrid.paddingRight) || 0;
    var availableWidth = gridRect.width - padL - padR - (dims.cols - 1) * gapPx;
    var totalFr = EXPANDED_WEIGHT + (dims.cols - 1) * SHRUNK_WEIGHT;
    var targetCellWidth = availableWidth * (EXPANDED_WEIGHT / totalFr);
    // Subtract card padding (from rebuild-team-cards.py: padding: 24px 20px)
    var targetBioWidth = targetCellWidth - 40;

    // Pre-measure bio height at the target width
    var bioEl = card.querySelector('.team-card__bio');
    if (bioEl) {
      var h = measureBioHeightAtWidth(bioEl, targetBioWidth);
      card.style.setProperty('--expanded-bio-height', h + 'px');
    }

    // Collapse previous card's classes silently
    if (state.expanded && state.expanded !== card) {
      state.expanded.classList.remove('team-card--expanded');
      state.expanded.style.removeProperty('--expanded-bio-height');
    }

    // Write the weighted grid templates — this is the whole animation trigger
    grid.style.gridTemplateColumns = buildWeightedTemplate(dims.cols, col);
    grid.style.gridTemplateRows = buildWeightedTemplate(totalRows, row);
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

/* Team-card click-to-expand: real grid-track animation.
 *
 * On click, the clicked card's COLUMN widens (grid-template-columns inline
 * style is rewritten to boost that column's fr weight and shrink the others).
 * The clicked card also gets `grid-row: span 2` via its class, making it
 * twice as tall. Both changes transition on the same 2400ms cubic-bezier,
 * so the grid lines move in lockstep — all 4 sides of every card stay
 * locked to their neighbours throughout the animation.
 *
 * Inner elements (photo, name, icon row) keep their natural pixel sizes.
 * Bio is hidden in the dormant state (max-height:0 + opacity:0) and
 * revealed via max-height + opacity transition on the same 2400ms curve.
 *
 * Pretext measures the bio's natural pixel height at the clicked card's
 * post-animation width, so the max-height target is exact.
 */
(function () {
  'use strict';

  var ANIM_MS = 2400;
  var EXPANDED_FR = 2.4;
  var SHRUNK_FR = 0.6;
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
          if (w > availablePx && current) { lines++; current = words[i]; }
          else { current = candidate; }
        }
        return Math.ceil(lines * lineHeightPx);
      } catch (_e) { return null; }
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
    if (!lineHeight || !isFinite(lineHeight)) lineHeight = parseFloat(cs.fontSize) * 1.55;
    if (state.measure && text) {
      var h = state.measure(text, getComputedFont(bioEl), widthPx, lineHeight);
      if (h) return h + 4;
    }
    var clone = bioEl.cloneNode(true);
    clone.style.cssText = (
      'position:absolute; left:-9999px; top:0; width:' + widthPx + 'px; ' +
      'max-height:none; -webkit-line-clamp:unset; display:block; opacity:1;'
    );
    document.body.appendChild(clone);
    var h2 = clone.scrollHeight;
    document.body.removeChild(clone);
    return h2 + 4;
  }

  function onDocClick(e) {
    var card = e.target.closest && e.target.closest('.team-card');
    if (!card) return;
    if (e.target.closest('.team-card__icon, .team-card__links a, .team-card__links span')) return;
    e.preventDefault();
    if (card === state.expanded) collapse();
    else expand(card);
  }

  function getColumnCount(grid) {
    var cs = getComputedStyle(grid);
    return cs.gridTemplateColumns.split(/\s+/).filter(Boolean).length || 1;
  }

  function buildColTracks(cols, highlightIdx) {
    var parts = [];
    for (var i = 0; i < cols; i++) {
      parts.push(i === highlightIdx
        ? 'minmax(0, ' + EXPANDED_FR + 'fr)'
        : 'minmax(0, ' + SHRUNK_FR + 'fr)');
    }
    return parts.join(' ');
  }

  function expand(card) {
    var grid = card.closest('.team-grid');
    if (!grid) return;
    var cards = Array.from(grid.querySelectorAll('.team-card'));
    var idx = cards.indexOf(card);
    if (idx < 0) return;
    var cols = getColumnCount(grid);
    if (cols <= 1) {
      // Mobile single-column — just reveal via class
      if (state.expanded && state.expanded !== card) {
        state.expanded.classList.remove('team-card--expanded');
        state.expanded.style.removeProperty('--expanded-bio-height');
      }
      card.classList.add('team-card--expanded');
      grid.classList.add('team-grid--has-expanded');
      state.expanded = card;
      return;
    }

    var col = idx % cols;

    // Compute the clicked card's final width after column expansion
    var gridRect = grid.getBoundingClientRect();
    var csGrid = getComputedStyle(grid);
    var gapPx = parseFloat(csGrid.columnGap) || 0;
    var padL = parseFloat(csGrid.paddingLeft) || 0;
    var padR = parseFloat(csGrid.paddingRight) || 0;
    var available = gridRect.width - padL - padR - (cols - 1) * gapPx;
    var totalFr = EXPANDED_FR + (cols - 1) * SHRUNK_FR;
    var targetCardWidth = available * (EXPANDED_FR / totalFr);
    // Subtract card's horizontal padding (from CSS: 20px each side)
    var targetBioWidth = Math.max(120, targetCardWidth - 40);

    var bioEl = card.querySelector('.team-card__bio');
    if (bioEl) {
      var h = measureBioHeightAtWidth(bioEl, targetBioWidth);
      card.style.setProperty('--expanded-bio-height', h + 'px');
    }

    if (state.expanded && state.expanded !== card) {
      state.expanded.classList.remove('team-card--expanded');
      state.expanded.style.removeProperty('--expanded-bio-height');
    }

    grid.style.gridTemplateColumns = buildColTracks(cols, col);
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
      grid.classList.remove('team-grid--has-expanded');
    }
    prev.classList.remove('team-card--expanded');
    prev.style.removeProperty('--expanded-bio-height');
    if (!skipState) state.expanded = null;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else { init(); }
})();

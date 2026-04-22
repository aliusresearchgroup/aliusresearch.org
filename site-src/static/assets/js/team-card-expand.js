/* Team-card click-to-expand: accordion-pattern animation.
 *
 * Mirrors pretext_website/pages/demos/accordion.ts:
 *   - Only the bio element's max-height changes (container adapts)
 *   - Nothing inside scales — photo, name, role, icons keep their own size
 *   - Other cards in the grid shrink (bio clamps to 2 lines) so one card
 *     is visibly emphasised, accordion-style
 *   - Pretext's canvas text measurement gives the EXACT expanded height,
 *     so the CSS max-height transition animates to a known target
 *     (CSS cannot animate to height:auto)
 *
 * Fallback path: hidden-DOM-clone scrollHeight measurement if esm.sh /
 * pretext is unreachable.
 */
(function () {
  'use strict';

  var ANIM_MS = 520;
  var state = { expanded: null, measure: null };

  function init() {
    if (!document.querySelector('.team-card')) return;
    document.addEventListener('click', onDocClick, true);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') collapse();
    });

    // Dynamic pretext import (best-effort)
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

  function measureBioHeight(card) {
    var bio = card.querySelector('.team-card__bio');
    if (!bio) return 0;
    var text = (bio.textContent || '').trim();
    var cs = getComputedStyle(bio);
    var lineHeight = parseFloat(cs.lineHeight);
    if (!lineHeight || !isFinite(lineHeight)) lineHeight = parseFloat(cs.fontSize) * 1.7;
    var contentWidth = bio.getBoundingClientRect().width;

    // Primary path: pretext
    if (state.measure && text && contentWidth > 0) {
      var h = state.measure(text, getComputedFont(bio), contentWidth, lineHeight);
      if (h) return h + 4;  // small slack
    }
    // Fallback: clone-and-measure in the live DOM
    var clone = bio.cloneNode(true);
    clone.style.cssText = (
      'position:absolute; left:-9999px; top:0; ' +
      'width:' + contentWidth + 'px; ' +
      'max-height:none; ' +
      '-webkit-line-clamp:unset; display:block;'
    );
    document.body.appendChild(clone);
    var h2 = clone.scrollHeight;
    document.body.removeChild(clone);
    return h2 + 4;
  }

  function onDocClick(e) {
    var card = e.target.closest && e.target.closest('.team-card');
    if (!card) return;
    // Don't hijack clicks on icon links
    if (e.target.closest('.team-card__icon, .team-card__links a, .team-card__links span')) return;
    e.preventDefault();
    if (card === state.expanded) {
      collapse();
    } else {
      expand(card);
    }
  }

  function expand(card) {
    var grid = card.closest('.team-grid');
    if (!grid) return;

    // Pre-measure BEFORE flipping the class — so the bio's width is still the
    // uncrowded grid-cell width when we calculate wrap lines.
    var bioHeight = measureBioHeight(card);

    if (state.expanded) {
      // Collapse any previous card silently (no extra animation hop)
      state.expanded.classList.remove('team-card--expanded');
      state.expanded.style.removeProperty('--expanded-bio-height');
    }

    card.style.setProperty('--expanded-bio-height', bioHeight + 'px');
    grid.classList.add('team-grid--has-expanded');
    card.classList.add('team-card--expanded');
    state.expanded = card;
  }

  function collapse() {
    if (!state.expanded) return;
    var prev = state.expanded;
    var grid = prev.closest('.team-grid');
    prev.classList.remove('team-card--expanded');
    prev.style.removeProperty('--expanded-bio-height');
    if (grid) grid.classList.remove('team-grid--has-expanded');
    state.expanded = null;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

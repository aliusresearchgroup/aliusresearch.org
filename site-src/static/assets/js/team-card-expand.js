/* Team-card expand-on-click: uniform grid by default, the clicked card
 * smoothly grows to show its full bio while neighbours dim + scale down.
 *
 * Why pretext: CSS can't animate to `height: auto`. We need an exact target
 * height for the expanded bio so the transition is smooth. pretext's canvas
 * measureText gives line widths; combined with the computed line-height we
 * derive the natural height at the expanded card width — then set max-height
 * to that number before releasing the class that animates the growth.
 *
 * Falls back to scrollHeight if pretext fails to load.
 */
(function () {
  'use strict';

  var EXPAND_MS = 320;
  var state = { expanded: null, measure: null };

  // Wait for DOM + inject a backdrop element for click-outside detection
  function init() {
    if (!document.querySelector('.team-card')) return;
    var backdrop = document.createElement('div');
    backdrop.className = 'team-card-backdrop';
    backdrop.setAttribute('aria-hidden', 'true');
    document.body.appendChild(backdrop);
    backdrop.addEventListener('click', collapse);

    document.addEventListener('click', onDocClick, true);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') collapse();
    });

    // Best-effort pretext load (not critical — canvas fallback is fine)
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
        // Greedy word-wrap: count lines that fit in availablePx
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

  function onDocClick(e) {
    var card = e.target.closest && e.target.closest('.team-card');
    if (!card) {
      if (state.expanded) collapse();
      return;
    }
    // Ignore clicks on icon links — let them navigate
    if (e.target.closest('.team-card__icon, .team-card__links a, .team-card__links span')) return;
    if (card === state.expanded) {
      collapse();
    } else {
      e.preventDefault();
      expand(card);
    }
  }

  function measureBioHeight(card) {
    var bio = card.querySelector('.team-card__bio');
    if (!bio) return 0;
    // Build a clone at the expected expanded width and measure.
    var clone = bio.cloneNode(true);
    clone.style.cssText = (
      'position:absolute; left:-9999px; top:0; ' +
      'width:' + (card.offsetWidth - 48) + 'px; ' +  // same inner padding as expanded
      '-webkit-line-clamp:unset; display:block; ' +
      'font-size:15px; line-height:1.7;'
    );
    document.body.appendChild(clone);
    var h = clone.scrollHeight;
    document.body.removeChild(clone);
    return h;
  }

  function expand(card) {
    if (state.expanded && state.expanded !== card) collapse(true);
    var grid = card.closest('.team-grid');
    if (!grid) return;

    // Pre-measure so the transition has a concrete target height.
    var bioHeight = measureBioHeight(card);
    card.style.setProperty('--expanded-bio-height', bioHeight + 'px');

    grid.classList.add('team-grid--has-expanded');
    card.classList.add('team-card--expanded');
    document.body.classList.add('team-card-backdrop--active');
    state.expanded = card;

    // Keep the card in view after the animation settles
    setTimeout(function () {
      card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 60);
  }

  function collapse(skipScroll) {
    if (!state.expanded) {
      document.body.classList.remove('team-card-backdrop--active');
      return;
    }
    var prev = state.expanded;
    var grid = prev.closest('.team-grid');
    prev.classList.remove('team-card--expanded');
    if (grid) grid.classList.remove('team-grid--has-expanded');
    document.body.classList.remove('team-card-backdrop--active');
    state.expanded = null;
    if (!skipScroll) {
      setTimeout(function () {
        // nudge layout back to cards
        prev.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }, EXPAND_MS);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
